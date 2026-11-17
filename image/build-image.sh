#!/bin/bash
# EXPERIMENTAL and UNTESTED on real hardware: stage Steamed Pi inside an Ubuntu Desktop image for the Raspberry Pi,
# so the installer runs by itself on first boot. Run it as root, on Linux, from a checkout of this repository.
#
#   sudo image/build-image.sh --base ubuntu-desktop-raspi.img.xz --out steamed-pi.img
#
# It copies the repository to /opt/steamed-pi inside the image and enables image/steamed-pi-firstboot.service.
# It does NOT put Valve's Steam client (or any other third-party software) in the image: those are downloaded on the
# first boot, which therefore needs a network connection.
set -euo pipefail
BASE=""; OUT=""
while [ $# -gt 0 ]; do case $1 in --base) BASE=$2; shift;; --out) OUT=$2; shift;; *) echo "usage: $0 --base IMAGE[.xz] --out IMAGE"; exit 2;; esac; shift; done
[ -n "$BASE" ] && [ -n "$OUT" ] || { echo "usage: $0 --base IMAGE[.xz] --out IMAGE"; exit 2; }
[ "$(id -u)" = 0 ] || { echo "run as root (it mounts disk images)"; exit 1; }
HERE=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)
W=$(mktemp -d); LOOP=""; cleanup() { set +e; mountpoint -q "$W/root" && umount "$W/root"; [ -n "$LOOP" ] && losetup -d "$LOOP"; rm -rf "$W"; }; trap cleanup EXIT

echo "== copying the base image"; case $BASE in *.xz) xz -dc "$BASE" > "$OUT";; *) cp --sparse=always "$BASE" "$OUT";; esac
LOOP=$(losetup --find --show --partscan "$OUT"); mkdir -p "$W/root"
ROOTPART=$(lsblk -lnpo NAME,FSTYPE "$LOOP" | awk '$2=="ext4"{print $1}' | tail -1); [ -n "$ROOTPART" ] || { echo "no ext4 root partition found in the image"; exit 1; }
mount "$ROOTPART" "$W/root"; echo "root partition: $ROOTPART"
echo "== staging Steamed Pi"
mkdir -p "$W/root/opt/steamed-pi"; tar -C "$HERE" --exclude=.git --exclude=build -cf - . | tar -C "$W/root/opt/steamed-pi" -xf -
chmod +x "$W/root/opt/steamed-pi/image/steamed-pi-firstboot.sh" "$W/root/opt/steamed-pi/install.sh"
install -m 644 "$HERE/image/steamed-pi-firstboot.service" "$W/root/etc/systemd/system/steamed-pi-firstboot.service"
mkdir -p "$W/root/etc/systemd/system/multi-user.target.wants"; ln -sf ../steamed-pi-firstboot.service "$W/root/etc/systemd/system/multi-user.target.wants/steamed-pi-firstboot.service"
sync; echo "== done: $OUT"; echo "Flash it with Raspberry Pi Imager (Use custom), boot, finish Ubuntu's setup, and wait: the installer runs by itself and reboots into Gaming Mode."
