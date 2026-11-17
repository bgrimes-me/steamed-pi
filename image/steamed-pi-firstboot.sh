#!/bin/bash
# Runs once, as root, on the first boot of a Steamed Pi image. Waits for the first user account (created by Ubuntu's setup
# wizard) and for the network, runs the installer for that user, then reboots into Gaming Mode.
# Log: /var/log/steamed-pi-firstboot.log      Marker: /var/lib/steamed-pi/firstboot-done
set -u
MARK=/var/lib/steamed-pi/firstboot-done; REPO=/opt/steamed-pi
exec >>/var/log/steamed-pi-firstboot.log 2>&1
[ -f "$MARK" ] && exit 0
echo "== $(date) first boot setup starting"
first_user() { getent passwd | awk -F: '$3>=1000 && $3<60000 && $7!~/nologin|false/ && $6!="" {print $1}' | while read -r u; do [ -d "$(getent passwd "$u" | cut -d: -f6)" ] && { echo "$u"; break; }; done; }
U=""; for _ in $(seq 1 2880); do U=$(first_user); [ -n "$U" ] && break; sleep 30; done      # up to 24 h for someone to finish the setup wizard
[ -n "$U" ] || { echo "no user account appeared; giving up (run $REPO/install.sh yourself)"; exit 1; }
echo "user: $U"; nm-online -q -t 900 || echo "network not confirmed; trying anyway"
sleep 60       # let the desktop settle after the wizard
STEAMED_PI_USER=$U "$REPO/install.sh" --yes
rc=$?
echo "installer exit code: $rc"
if [ $rc = 0 ]; then mkdir -p "$(dirname "$MARK")"; touch "$MARK"; echo "rebooting into Gaming Mode"; systemctl reboot
else echo "installer reported problems. Fix the cause and run: STEAMED_PI_USER=$U $REPO/install.sh"; fi
