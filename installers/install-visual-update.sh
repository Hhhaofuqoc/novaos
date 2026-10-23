#!/usr/bin/env bash
# Install only the fetch/optional Plasma additions into an existing NovaOS guest.
set -euo pipefail
mode=${1:---fetch-only}
case $mode in --fetch-only|--plasma) ;; *) echo 'Modo inválido.' >&2; exit 2;; esac
[[ $(id -u) == 0 && -f /etc/novaos-mobile-owner ]] || {
  echo 'Execute pelo atualizador do NovaOS no Termux.' >&2; exit 1;
}
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export DEBIAN_FRONTEND=noninteractive
saved_policy=''
if [[ -e /usr/sbin/policy-rc.d ]]; then
  saved_policy=$(mktemp)
  cp -a /usr/sbin/policy-rc.d "$saved_policy"
fi
restore_policy() {
  if [[ -n $saved_policy ]]; then
    cp -a "$saved_policy" /usr/sbin/policy-rc.d
    rm -f -- "$saved_policy"
  else rm -f /usr/sbin/policy-rc.d; fi
}
trap restore_policy EXIT
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod 755 /usr/sbin/policy-rc.d
packages=(fastfetch)
if [[ $mode == --plasma ]]; then
  mapfile -t plasma_packages < <(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$repo/mobile/packages-plasma.txt")
  packages+=("${plasma_packages[@]}")
fi
apt-get update
apt-get install -y --no-install-recommends "${packages[@]}"
install -d /usr/share/novaos/fetch /usr/share/novaos/themes/plasma
install -m 644 "$repo/themes/fetch/"*.jsonc /usr/share/novaos/fetch/
install -m 644 "$repo/themes/plasma/NovaOS.colors" /usr/share/novaos/themes/plasma/
install -m 755 "$repo/themes/apply-plasma.sh" /usr/share/novaos/themes/apply-plasma.sh
install -m 755 "$repo/applications/novafetch" /usr/bin/novafetch
install -m 644 "$repo/applications/novaos/__main__.py" "$repo/applications/novaos/system.py" /usr/lib/python3/dist-packages/novaos/
install -m 755 "$repo/mobile/guest-session.sh" /usr/local/libexec/novaos-mobile-session
install -m 644 "$repo/themes/icons/NovaOS/index.theme" /usr/share/icons/NovaOS/index.theme
if [[ $mode == --plasma ]]; then
  for component in welcome browser music notes; do
    icon="novaos-$component"
    [[ $component != welcome ]] || icon=novaos
    desktop_file="/usr/share/applications/novaos-$component.desktop"
    [[ ! -f $desktop_file ]] || sed -i "s|^Icon=.*|Icon=/usr/share/icons/NovaOS/scalable/apps/$icon.svg|" "$desktop_file"
  done
  for component in terminal files; do
    executable=konsole
    [[ $component != files ]] || executable=dolphin
    cat > "/usr/share/applications/novaos-plasma-$component.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=NovaOS $component
Exec=$executable
Icon=/usr/share/icons/NovaOS/scalable/apps/novaos-$component.svg
Terminal=false
Categories=System;
ENTRY
  done
fi
if [[ -f /etc/xdg/autostart/novaos-session.desktop ]]; then
  sed -i 's/^OnlyShowIn=.*/OnlyShowIn=XFCE;KDE;/' /etc/xdg/autostart/novaos-session.desktop
fi
# Fastfetch's normal command picks up this per-user config; all old files are backed up.
for account in nova root; do
  home_dir=$(getent passwd "$account" | cut -d: -f6)
  [[ -n $home_dir && -d $home_dir ]] || continue
  destination="$home_dir/.config/fastfetch"
  backup="$home_dir/.config/novaos/backups/fetch-$(date -u +%Y%m%dT%H%M%S)-$$"
  mkdir -p "$destination" "$backup"
  for previous in config.jsonc config.json; do
    [[ ! -f $destination/$previous ]] || cp -a "$destination/$previous" "$backup/"
  done
  install -m 644 /usr/share/novaos/fetch/compact.jsonc "$destination/config.jsonc"
  if [[ $mode == --plasma ]]; then
    konsole_dir="$home_dir/.local/share/konsole"
    mkdir -p "$konsole_dir"
    [[ ! -f $home_dir/.config/konsolerc ]] || cp -a "$home_dir/.config/konsolerc" "$backup/"
    for file in NovaOS.profile NovaOS.colorscheme; do
      [[ ! -f $konsole_dir/$file ]] || cp -a "$konsole_dir/$file" "$backup/"
      install -m 644 "$repo/themes/plasma/$file" "$konsole_dir/$file"
      chown "$account:$(id -gn "$account")" "$konsole_dir/$file"
    done
    kwriteconfig6 --file "$home_dir/.config/konsolerc" --group 'Desktop Entry' --key DefaultProfile NovaOS.profile
    chown "$account:$(id -gn "$account")" "$home_dir/.config/konsolerc" "$konsole_dir"
  fi
  chown -R "$account:$(id -gn "$account")" "$destination" "$backup"
done
apt-get clean
printf 'NovaFetch instalado. Execute: novafetch\n'
if [[ $mode == --plasma ]]; then
  command -v startplasma-x11 >/dev/null || { echo 'startplasma-x11 não encontrado.' >&2; exit 1; }
  printf 'Plasma X11 instalado; selecione a sessão no launcher Termux.\n'
fi
