#!/bin/bash
set -euo pipefail
[[ $(id -un) == nova ]] || { echo 'A sessão deve executar como usuário nova.' >&2; exit 1; }
export XDG_RUNTIME_DIR=/tmp/novaos-runtime-nova
install -d -m 700 "$XDG_RUNTIME_DIR"
export XDG_SESSION_TYPE=x11 XDG_CURRENT_DESKTOP=XFCE DESKTOP_SESSION=xfce
export NO_AT_BRIDGE=1 LIBGL_ALWAYS_SOFTWARE=1
export NOVAOS_MOBILE=1
unset SESSION_MANAGER DBUS_SESSION_BUS_ADDRESS
# On mobile, locked sessions cannot authenticate against Android. Do not start
# a screen locker or power daemon; Android remains responsible for these.
mkdir -p "$HOME/.config/autostart"
for service in xfce4-power-manager xfce4-screensaver light-locker; do
  if [[ ! -f "$HOME/.config/autostart/$service.desktop" ]]; then
    printf '[Desktop Entry]\nType=Application\nName=%s\nHidden=true\n' "$service" > "$HOME/.config/autostart/$service.desktop"
  fi
done
# NovaOS initialization runs from XFCE autostart after xfconf is available.
exec dbus-run-session -- startxfce4
