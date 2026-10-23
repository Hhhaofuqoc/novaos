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
packages=(fastfetch python3-gi-cairo)
if [[ $mode == --plasma ]]; then
  # Debian slim filters translation catalogs. Keep Portuguese without restoring
  # every language or changing the image's other space-saving filters.
  cat > /etc/dpkg/dpkg.cfg.d/zz-novaos-languages <<'LANGUAGES'
path-include /usr/share/locale/pt
path-include /usr/share/locale/pt/*
path-include /usr/share/locale/pt_BR
path-include /usr/share/locale/pt_BR/*
LANGUAGES
  mapfile -t plasma_packages < <(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$repo/mobile/packages-plasma.txt")
  packages+=("${plasma_packages[@]}")
fi
apt-get update
apt-get install -y --no-install-recommends "${packages[@]}"
if [[ $mode == --plasma ]]; then
  localedef -i pt_BR -f UTF-8 pt_BR.UTF-8
  if [[ ! -f /usr/share/locale/pt_BR/LC_MESSAGES/plasma_applet_org.kde.plasma.kickoff.mo ]]; then
    apt-get install -y --no-install-recommends --reinstall plasma-desktop-data plasma-workspace-data
  fi
fi
install -d /usr/share/novaos/fetch /usr/share/novaos/themes/plasma
install -d /usr/share/novaos/wallpapers
install -m 644 "$repo/wallpapers/novaos-night-room.png" /usr/share/novaos/wallpapers/
install -m 644 "$repo/themes/fetch/"*.jsonc /usr/share/novaos/fetch/
install -m 644 "$repo/themes/plasma/NovaOS.colors" /usr/share/novaos/themes/plasma/
install -m 755 "$repo/themes/apply-plasma.sh" /usr/share/novaos/themes/apply-plasma.sh
install -m 755 "$repo/applications/novafetch" /usr/bin/novafetch
install -m 644 "$repo/applications/novaos/__main__.py" "$repo/applications/novaos/system.py" /usr/lib/python3/dist-packages/novaos/
install -m 644 "$repo/applications/novaos/desktop_widgets.py" "$repo/applications/novaos/music.py" /usr/lib/python3/dist-packages/novaos/
install -m 755 "$repo/mobile/guest-session.sh" /usr/local/libexec/novaos-mobile-session
install -m 644 "$repo/themes/icons/NovaOS/index.theme" /usr/share/icons/NovaOS/index.theme
install -m 644 "$repo/themes/icons/NovaOS/scalable/apps/novaos.svg" /usr/share/icons/NovaOS/scalable/apps/novaos.svg
if [[ $mode == --plasma ]]; then
  install -m 644 "$repo/themes/plasma/novaos-widgets.desktop" /etc/xdg/autostart/novaos-widgets.desktop
  for component in welcome browser music notes editor monitor settings store updater; do
    icon="novaos-$component"
    [[ $component != welcome ]] || icon=novaos
    desktop_file="/usr/share/applications/novaos-$component.desktop"
    [[ ! -f $desktop_file ]] || sed -i "s|^Icon=.*|Icon=/usr/share/icons/NovaOS/scalable/apps/$icon.svg|" "$desktop_file"
  done
  for component in terminal files; do
    executable=konsole
    title=NovaTerminal
    [[ $component != files ]] || executable=dolphin
    [[ $component != files ]] || title=NovaFiles
    cat > "/usr/share/applications/novaos-plasma-$component.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=$title
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
  # Parent directories created by an emulated-root installer must remain writable
  # by the account (Activities and GTK also use these paths).
  for relative in .config .config/novaos .config/novaos/backups .local .local/share; do
    mkdir -p "$home_dir/$relative"
    chown "$account:$(id -gn "$account")" "$home_dir/$relative"
  done
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
