#!/usr/bin/env bash
# Package only local files; never installs packages or downloads code.
set -euo pipefail
if (($#)); then
    if [[ $# == 1 && ( $1 == --help || $1 == -h ) ]]; then
        printf 'Usage: %s (no positional arguments)\nSet NOVAOS_VERSION / NOVAOS_DIST_DIR to configure the local build.\n' "$0"
        exit 0
    fi
    echo 'Unexpected argument. Use --help.' >&2
    exit 2
fi
repo=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
version=${NOVAOS_VERSION:-0.1.0}
out=${NOVAOS_DIST_DIR:-$repo/dist}
if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+([.+~][a-zA-Z0-9.]+)?$ ]]; then
    printf 'Invalid Debian package version: %s\n' "$version" >&2
    exit 2
fi
for tool in dpkg-deb install find; do
    command -v "$tool" >/dev/null || { printf 'Missing dependency: %s\n' "$tool" >&2; exit 1; }
done
[[ -f $repo/installers/install-system.sh ]] || { echo 'Missing installer.' >&2; exit 1; }
mkdir -p -- "$out"
stage=$(mktemp -d "${TMPDIR:-/tmp}/novaos-deb.XXXXXXXX")
trap 'rm -rf -- "$stage"' EXIT
core=$stage/core
music=$stage/music
mkdir -p -- "$core/DEBIAN"
bash "$repo/installers/install-system.sh" --destdir "$core"
# Split original recordings from the small application/theme package.
if [[ -d $core/usr/share/novaos/music/generated ]] && find "$core/usr/share/novaos/music/generated" -type f -print -quit | read -r _; then
    mkdir -p -- "$music/usr/share/novaos/music" "$music/DEBIAN"
    mv -- "$core/usr/share/novaos/music/generated" "$music/usr/share/novaos/music/generated"
fi
cat > "$core/DEBIAN/control" <<CONTROL
Package: novaos-desktop
Version: $version
Section: x11
Priority: optional
Architecture: all
Maintainer: NovaOS Contributors <maintainers@novaos.invalid>
Depends: python3 (>= 3.11), python3-gi, python3-psutil, python3-gi-cairo, fastfetch, gir1.2-gtk-3.0, gir1.2-gstreamer-1.0, gir1.2-gst-plugins-base-1.0, gstreamer1.0-plugins-base, gstreamer1.0-plugins-good, gstreamer1.0-pulseaudio, librsvg2-common, dbus-x11, xdg-utils
Recommends: novaos-music, xfce4-session, xfce4-panel, xfdesktop4, xfwm4, xfce4-settings, xfconf, xfce4-terminal, thunar, mousepad, firefox-esr, xfce4-taskmanager, xfce4-appfinder, xfce4-notifyd, xfce4-pulseaudio-plugin, fonts-dejavu-core, adwaita-icon-theme, pulseaudio-utils
Description: NovaOS native applications and Synthwave Linux Experience
 Your universe. Your system. Native GTK applications, XFCE theme,
 original wallpapers and session integration for Debian 13.
 This alpha package does not replace the Linux kernel or Android.
CONTROL
# Declare configuration files so dpkg preserves local administrator modifications.
if [[ -d $core/etc ]]; then
    (cd "$core" && find etc -type f -printf '/%p\n' | LC_ALL=C sort) > "$core/DEBIAN/conffiles"
fi
find "$core" -type d -exec chmod 0755 {} +
find "$core" -type f ! -perm /111 -exec chmod 0644 {} +
find "$core" -type f -perm /111 -exec chmod 0755 {} +
find "$core" -type f -name '*.pyc' -delete
find "$core" -type d -name __pycache__ -empty -delete
# root ownership in archives without requiring root to build.
dpkg-deb --root-owner-group --build "$core" "$out/novaos-desktop_${version}_all.deb"
if [[ -d $music/usr ]]; then
    if [[ -f $repo/music/LICENSE ]]; then
        install -Dm0644 "$repo/music/LICENSE" "$music/usr/share/doc/novaos-music/copyright"
    fi
    cat > "$music/DEBIAN/control" <<CONTROL
Package: novaos-music
Version: $version
Section: sound
Priority: optional
Architecture: all
Maintainer: NovaOS Contributors <maintainers@novaos.invalid>
Suggests: novaos-desktop
Description: Original locally synthesized NovaOS ambient collection
 Twelve original instrumental tracks, metadata and checksums generated
 by the open source NovaOS music synthesizer. No streaming is required.
CONTROL
    find "$music" -type d -exec chmod 0755 {} +
    find "$music" -type f -exec chmod 0644 {} +
    dpkg-deb --root-owner-group --build "$music" "$out/novaos-music_${version}_all.deb"
else
    printf 'Music recordings absent: package the album after running music/generate.py.\n' >&2
fi
