#!/usr/bin/env bash
# Build a real Debian 13 amd64 bootable Live ISO using Debian live-build.
# Run as root on Debian 13 (CI uses a privileged Debian container).
set -Eeuo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd -- "$HERE/../.." && pwd -P)"
[[ "$(id -u)" == 0 ]] || { echo 'Run ISO build as root (inside builder container).' >&2; exit 1; }
[[ "$(dpkg --print-architecture)" == amd64 ]] || { echo 'NovaOS Full ISO builder requires an amd64 environment.' >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates live-build debootstrap xorriso squashfs-tools \
  syslinux-common isolinux grub-pc-bin grub-efi-amd64-bin \
  mtools dosfstools git tar curl gpg file
BUILD="$ROOT/.build/novaos-full-amd64"
OUT="$ROOT/dist"
mkdir -p "$BUILD" "$OUT"
cd "$BUILD"
# Always run from a clean CI workspace; do not touch the user's Android container.
lb config \
  --mode debian \
  --distribution trixie \
  --architectures amd64 \
  --binary-images iso-hybrid \
  --bootloaders 'syslinux grub-efi' \
  --debian-installer none \
  --archive-areas 'main contrib non-free-firmware' \
  --apt-recommends false \
  --apt-indices false \
  --compression xz \
  --bootappend-live 'boot=live components username=nova hostname=novaos locales=pt_BR.UTF-8 keyboard-layouts=br' \
  --iso-application 'NovaOS Full 1.0' \
  --iso-publisher 'NovaOS'
mkdir -p config/includes.chroot/opt/novaos/app
install -Dm644 "$HERE/packages.list" config/package-lists/novaos-full.list.chroot
install -Dm755 "$HERE/session.sh" config/includes.chroot/usr/local/bin/novaos-vm-session
for component in assets config nova-shell scripts themes; do
  cp -a "$ROOT/$component" "config/includes.chroot/opt/novaos/app/"
done
install -Dm644 "$HERE/novaos.desktop" config/includes.chroot/usr/share/xsessions/novaos.desktop
install -Dm644 "$HERE/lightdm.conf" config/includes.chroot/etc/lightdm/lightdm.conf.d/50-novaos.conf
install -Dm644 "$HERE/novaos-info.desktop" config/includes.chroot/usr/share/applications/novaos-info.desktop
install -Dm755 "$HERE/0200-novaos.hook.chroot" config/hooks/normal/0200-novaos.hook.chroot
# Provide the VM with an honest, non-Android release information utility.
install -Dm755 "$HERE/nova-vm-info" config/includes.chroot/usr/local/bin/nova-info
# Use live-build to produce a real ISO filesystem, kernel, initrd and bootloaders.
lb build 2>&1 | tee "$ROOT/novaos-iso-build.log"
ISO="$(find "$BUILD" -maxdepth 1 -type f -name '*.hybrid.iso' -print -quit)"
[[ -n "$ISO" && -s "$ISO" ]] || { echo 'ERROR: live-build did not produce a hybrid ISO' >&2; exit 1; }
cp -f "$ISO" "$OUT/NovaOS-v1.0-Full-amd64.iso"
( cd "$OUT" && sha256sum NovaOS-v1.0-Full-amd64.iso | tee SHA256SUMS.txt )
file "$OUT/NovaOS-v1.0-Full-amd64.iso"
ls -lh "$OUT/NovaOS-v1.0-Full-amd64.iso"
echo "NOVAOS_ISO=$OUT/NovaOS-v1.0-Full-amd64.iso"
