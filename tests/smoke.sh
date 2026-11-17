#!/bin/bash
# Smoke tests: everything that can be checked without a Raspberry Pi, root, or a reboot.   Run:  tests/smoke.sh
# What it does NOT cover: the real install on a Pi (packages, Steam download, GDM, reboot). See docs/INSTALL.md.
set -u
cd "$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)" || exit 1
FAIL=0; pass() { printf '  ok    %s\n' "$*"; }; fail() { printf '  FAIL  %s\n' "$*"; FAIL=1; }
SCRATCH=$(mktemp -d); trap 'rm -rf "$SCRATCH"' EXIT

echo "1. shell syntax"
while IFS= read -r f; do bash -n "$f" 2>/dev/null && : || fail "bash -n $f"; done < <(find . -name '*.sh' -o -name '*.in' -path './src/*' -prune -o -name '*.sh' -print | sort -u)
for f in install.sh uninstall.sh installer/lib.sh installer/modules/*.sh src/bin/steamed-pi-console-session src/bin/steamed-pi-console-start src/bin/steam src/bin/steamed-pi-first-login tools/compat/run.sh; do bash -n "$f" || fail "bash -n $f"; done; pass "all shell scripts parse"

echo "2. python syntax"
PYBAD=0
for f in $(grep -lE '^#!/usr/bin/(env )?python3' -r src installer tools 2>/dev/null) $(find . -name '*.py'); do python3 -I -c "import sys; compile(open(sys.argv[1]).read(), sys.argv[1], 'exec')" "$f" 2>/dev/null || { fail "python $f"; PYBAD=1; }; done
[ $PYBAD = 0 ] && pass "all python files compile"

echo "3. shellcheck (if installed)"
if command -v shellcheck >/dev/null; then shellcheck -S error install.sh uninstall.sh installer/lib.sh installer/modules/*.sh >/dev/null 2>&1 && pass "shellcheck: no errors" || fail "shellcheck reported errors (run it to see)"; else echo "  skip  shellcheck not installed"; fi

echo "4. nothing personal or machine-specific in the repository"
# A user's name, a hostname or an address must never be baked in. Allowed: the placeholders and the 'someuser' used by tests.
BAD=$(grep -rInE '/home/[A-Za-z][A-Za-z0-9_-]*/' . --exclude-dir=.git --exclude=smoke.sh | grep -vE '/home/(someuser|\*)/' | head -5)
[ -z "$BAD" ] && pass "no hardcoded home folders" || { fail "hardcoded home folder:"; echo "$BAD"; }
BAD=$(grep -rInE '\b[a-z0-9-]+\.local\b' . --exclude-dir=.git --exclude=smoke.sh | grep -vE '\$\(hostname\)\.local|hostname\)\.local|S\.host\+|\.local/(bin|lib|share|state)|\.local\b[^.]' | head -5)
[ -z "$BAD" ] && pass "no hardcoded hostnames" || { fail "hardcoded hostname:"; echo "$BAD"; }
BAD=$(grep -rInE '\b(192\.168|10\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01]))\.[0-9]+\.[0-9]+\b' . --exclude-dir=.git --exclude=smoke.sh | grep -vE '/(8|12|16) |/(8|12|16)$' | head -5)
[ -z "$BAD" ] && pass "no hardcoded IP addresses" || { fail "IP address:"; echo "$BAD"; }
BAD=$(grep -rInEi '@(gmail|outlook|hotmail|yahoo|icloud)\.|api[_-]?key|password *= *["'"'"'][^"'"'"']+["'"'"']' . --exclude-dir=.git --exclude=smoke.sh | head -5)
[ -z "$BAD" ] && pass "no emails or credentials" || { fail "possible secret:"; echo "$BAD"; }

echo "4b. one naming scheme (no leftovers of the old retro-* names)"
BAD=$(grep -rInE '(^|[^A-Za-z0-9_])(retro-[a-z]|retro_(common|palette|settings|vdf)|RETRO_|controller-home\b)' . --exclude-dir=.git --exclude=smoke.sh --exclude=migrate-from-retro.sh | grep -vE 'steamed-pi-controller-home' | head -5)
[ -z "$BAD" ] && pass "all names follow the steamed-pi-* scheme" || { fail "old name found:"; echo "$BAD"; }

echo "5. installer renders for any user (scratch home, no sudo)"
mkdir -p "$SCRATCH/home"
if STEAMED_PI_HOME="$SCRATCH/home" LOG_FILE="$SCRATCH/i.log" ./install.sh --only deploy --yes >"$SCRATCH/out.txt" 2>&1; then pass "deploy step ran"; else fail "deploy step failed"; tail -5 "$SCRATCH/out.txt"; fi
LEFT=$(grep -rl '@HOME@\|@USER@' "$SCRATCH/home" 2>/dev/null | head -3); [ -z "$LEFT" ] && pass "all placeholders filled in" || fail "unfilled placeholder in: $LEFT"
grep -q "Exec=$SCRATCH/home/.local/bin/steamed-pi-session-switch" "$SCRATCH/home/.local/share/applications/steamed-pi-gaming-mode.desktop" && pass "launchers point at that user's home" || fail "launcher path wrong"
[ -x "$SCRATCH/home/.local/bin/steamed-pi-setting" ] && pass "commands are executable" || fail "commands not executable"
HOME="$SCRATCH/home" STEAMED_PI_SETTINGS_DRY=1 "$SCRATCH/home/.local/bin/steamed-pi-setting" list >/dev/null 2>&1 && pass "deployed steamed-pi-setting runs" || fail "deployed steamed-pi-setting failed"

echo "6. full dry run of every step"
if LOG_FILE="$SCRATCH/dry.log" ./install.sh --dry-run --yes >"$SCRATCH/dry.txt" 2>&1; then pass "dry run completed"; else fail "dry run failed"; tail -8 "$SCRATCH/dry.txt"; fi
grep -q '^ERROR' "$SCRATCH/dry.txt" && fail "dry run printed an error"

echo "6b. the REAL installer, every step, in scratch mode (root steps are skipped, but all the code paths run under 'set -u')"
S2="$SCRATCH/real"; mkdir -p "$S2"
STEAMED_PI_HOME="$S2" LOG_FILE="$S2/i.log" ./install.sh --yes --skip preflight,steam,emulation >"$SCRATCH/real.txt" 2>&1; RC=$?
[ $RC = 0 ] && pass "installer exited 0" || { fail "installer exit code $RC"; tail -8 "$SCRATCH/real.txt"; }
for marker in "Installing Steamed Pi files" "Setting up the console session" "Boot splash and login screen" "Enabling Steamed Pi" "==> Done"; do
  grep -q "$marker" "$SCRATCH/real.txt" && pass "reached: $marker" || fail "never reached: $marker"; done
[ -L "$S2/.config/systemd/user/default.target.wants/steamed-pi-dashboard.service" ] && pass "dashboard service enabled" || fail "dashboard service not enabled"
grep -qE 'unbound variable|command not found' "$SCRATCH/real.txt" && { fail "shell errors in the installer output:"; grep -E 'unbound variable|command not found' "$SCRATCH/real.txt" | head -3; }

echo "6c. hostname helper validation"
H=system/steamed-pi-set-hostname
[ "$($H --check Steamed-Pi 2>&1)" = "steamed-pi" ] && pass "names are lower-cased" || fail "normalization"
for bad in "-x" "x-" "a b" "a_b" "a;b" '$(id)' ""; do $H --check "$bad" >/dev/null 2>&1 && fail "accepted bad name: [$bad]"; done; pass "bad names rejected"
$H steamed-pi >/dev/null 2>&1 && fail "helper ran without root" || pass "helper refuses to run without root"
grep -q 'steamed-pi-set-hostname' system/sudoers.in && pass "sudo rule limited to the helper" || fail "sudo rule missing"

echo "6d. documentation matches the installer"
for opt in $(grep -oE -- '--[a-z-]+\)' install.sh | tr -d ')' | sort -u); do
  case $opt in --help|--yes) continue;; esac
  grep -q -- "$opt" docs/INSTALL.md || fail "option $opt is not documented in docs/INSTALL.md"
done; pass "every installer option is in docs/INSTALL.md"
HELP=$(./install.sh --help); for opt in $(grep -oE -- '--[a-z-]+\)' install.sh | tr -d ')' | sort -u); do [ "$opt" = --help ] && continue; echo "$HELP" | grep -q -- "$opt" || fail "--help does not mention $opt"; done; pass "--help lists every option"
for step in preflight packages steam deploy system boot-look session emulation finish; do ls installer/modules/*-"$step".sh >/dev/null 2>&1 || fail "step $step has no module"; grep -q "$step" docs/INSTALL.md || fail "step $step missing from docs/INSTALL.md"; done; pass "every step has a module and is documented"
for f in README.md docs/*.md; do for l in $(grep -oE '\]\((docs/)?[A-Za-z_/.-]+\.md[^)]*\)' "$f" | sed -E 's/.*\(([^)#]+).*/\1/'); do d=$(dirname "$f"); [ -e "$d/$l" ] || [ -e "$l" ] || fail "broken link in $f: $l"; done; done; pass "document links resolve"

echo "7. sudo rules are valid for an arbitrary user"
sed 's|@USER@|someuser|g' system/sudoers.in > "$SCRATCH/sudoers"; visudo -cf "$SCRATCH/sudoers" >/dev/null 2>&1 && pass "sudoers file validates" || fail "sudoers file invalid"

echo; [ $FAIL = 0 ] && echo "ALL CHECKS PASSED" || { echo "SOME CHECKS FAILED"; exit 1; }
