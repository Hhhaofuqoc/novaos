#!/usr/bin/env bash
# Genuine Debian live-build recipe. Requires a disposable Debian 13 build host.
set -euo pipefail
repo=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
edition=lite
configure_only=false
installer=live
workdir=
out=$repo/dist
usage() {
    cat <<HELP
Usage: $0 [--edition lite|plasma] [--workdir PATH] [--output PATH]
          [--configure-only] [--no-debian-installer]
Requires Debian 13, live-build, debootstrap, xorriso, squashfs-tools, and root
for the actual build. Writes only inside workdir/output, never to a disk device.
HELP
}
while (($#)); do
    case $1 in
        --edition) edition=${2:?Missing edition}; shift 2 ;;
        --workdir) workdir=${2:?Missing workdir}; shift 2 ;;
        --output) out=${2:?Missing output}; shift 2 ;;
        --configure-only) configure_only=true; shift ;;
        --no-debian-installer) installer=none; shift ;;
        --help|-h) usage; exit 0 ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done
[[ $edition == lite || $edition == plasma ]] || { echo 'Edition must be lite or plasma.' >&2; exit 2; }
workdir=${workdir:-$repo/build/iso-$edition}
[[ -n $workdir && $workdir != / ]] || { echo 'Unsafe workdir.' >&2; exit 2; }
for tool in lb dpkg-deb; do
    command -v "$tool" >/dev/null || { printf 'Missing build tool: %s\n' "$tool" >&2; exit 1; }
done
if [[ $configure_only == false && $(id -u) != 0 ]]; then
    echo 'ISO builds need root for debootstrap/chroot/mount. Use a disposable Debian 13 VM.' >&2
    exit 1
fi
mkdir -p -- "$workdir" "$out"
workdir=$(CDPATH='' cd -- "$workdir" && pwd)
out=$(CDPATH='' cd -- "$out" && pwd)
# Never replace or erase a pre-existing unrelated directory.
if [[ -n $(find "$workdir" -mindepth 1 -maxdepth 1 -print -quit) && ! -f $workdir/.novaos-build ]]; then
    echo 'Refusing a non-empty workdir not created by NovaOS.' >&2; exit 1
fi
if [[ -f $workdir/.novaos-build && $(cat "$workdir/.novaos-build") != "$edition" ]]; then
    echo 'Use separate workdirs for Lite and Plasma.' >&2; exit 1
fi
if [[ -d $workdir/chroot ]]; then
    echo 'Existing chroot: run lb clean in that workdir or choose a fresh workdir before rebuilding.' >&2; exit 1
fi
printf '%s\n' "$edition" > "$workdir/.novaos-build"
NOVAOS_DIST_DIR="$out" bash "$repo/scripts/build-deb.sh"
cd -- "$workdir"
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-0}
lb config \
    --mode debian \
    --distribution trixie \
    --architectures amd64 \
    --archive-areas 'main non-free-firmware' \
    --debootstrap-options '--include=ca-certificates' \
    --binary-images iso-hybrid \
    --bootloaders 'syslinux grub-efi' \
    --debian-installer "$installer" \
    --debian-installer-gui true \
    --apt-recommends false \
    --firmware-binary true \
    --firmware-chroot true \
    --security true \
    --updates true \
    --backports false \
    --memtest none \
    --mirror-bootstrap https://deb.debian.org/debian \
    --mirror-chroot https://deb.debian.org/debian \
    --mirror-chroot-security https://security.debian.org/debian-security \
    --mirror-binary https://deb.debian.org/debian \
    --mirror-binary-security https://security.debian.org/debian-security \
    --bootappend-live 'boot=live components username=nova hostname=novaos locales=pt_BR.UTF-8 keyboard-layouts=us timezone=Etc/UTC persistence' \
    --iso-application 'NovaOS' \
    --iso-volume "NOVAOS_${edition^^}" \
    --iso-publisher 'NovaOS Contributors'
mkdir -p config/package-lists config/packages.chroot
cat "$repo/desktop/packages-lite.txt" "$repo/desktop/packages-desktop.txt" \
    | sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' | LC_ALL=C sort -u > config/package-lists/novaos.list.chroot
if [[ $edition == plasma ]]; then
    sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' "$repo/desktop/packages-plasma.txt" >> config/package-lists/novaos.list.chroot
fi
cp -a "$repo/desktop/live-config/." config/
cp -- "$out/novaos-desktop_${NOVAOS_VERSION:-0.1.0}_all.deb" config/packages.chroot/
if [[ -f $out/novaos-music_${NOVAOS_VERSION:-0.1.0}_all.deb ]]; then
    cp -- "$out/novaos-music_${NOVAOS_VERSION:-0.1.0}_all.deb" config/packages.chroot/
fi
if [[ $edition == plasma ]]; then
    mkdir -p config/includes.chroot/etc/sddm.conf.d
    cat > config/includes.chroot/etc/sddm.conf.d/50-novaos.conf <<'SDDM'
[Theme]
Current=breeze
[Autologin]
Session=plasma.desktop
SDDM
    # Use SDDM instead of running two display managers. Xfce remains a fallback.
    sed -i '/^lightdm$/d; /^lightdm-gtk-greeter$/d' config/package-lists/novaos.list.chroot
    cat > config/hooks/live/0910-novaos-plasma.hook.chroot <<'HOOK'
#!/bin/sh
set -eu
mkdir -p /etc/X11
printf '/usr/bin/sddm\n' > /etc/X11/default-display-manager
systemctl enable sddm.service
HOOK
    chmod +x config/hooks/live/0910-novaos-plasma.hook.chroot
fi
printf 'Configured %s edition in %s\n' "$edition" "$workdir"
[[ $configure_only == false ]] || exit 0
# pipefail keeps a failed build from being presented as a successful ISO.
lb build 2>&1 | tee build.log
[[ -s live-image-amd64.hybrid.iso ]] || { echo 'live-build did not create an ISO.' >&2; exit 1; }
iso="$out/novaos-${NOVAOS_VERSION:-0.1.0}-${edition}-amd64.iso"
cp -- live-image-amd64.hybrid.iso "$iso"
(cd "$out" && sha256sum "${iso##*/}" > "${iso##*/}.sha256")
cp -- build.log "$out/novaos-${NOVAOS_VERSION:-0.1.0}-${edition}-build.log"
printf 'Built ISO: %s\nBoot testing is still required; see docs/DESKTOP.md.\n' "$iso"
