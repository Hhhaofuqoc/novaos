#!/bin/bash
set -Eeuo pipefail
APP=/opt/novaos/app
STATE="$HOME/.local/state/novaos/logs"
mkdir -p "$STATE" "$HOME/.config/novaos"
export XDG_CURRENT_DESKTOP=NovaShell XDG_SESSION_DESKTOP=NovaShell
export GTK_THEME=Adwaita:dark
export XDG_DATA_DIRS="${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
export NO_AT_BRIDGE=1
command -v openbox >/dev/null || { echo 'Openbox ausente. Use novaos repair.' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Python3 ausente.' >&2; exit 1; }
children=()
cleanup(){
  trap - EXIT INT TERM
  for (( i=${#children[@]}-1; i>=0; i-- )); do kill -TERM "${children[$i]}" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] && command -v dbus-launch >/dev/null; then
  eval "$(dbus-launch --sh-syntax)"
  children+=("$(printf '%s' "$DBUS_SESSION_BUS_PID")")
fi
# Somente programas da sessão atual. Nenhum xfce4, systemd ou KDE.
openbox --config-file "$APP/config/openbox/rc.xml" >"$STATE/openbox.log" 2>&1 & children+=("$!")
sleep .35
if ! kill -0 "${children[${#children[@]}-1]}" 2>/dev/null; then echo 'Openbox encerrou. Leia openbox.log.' >&2; exit 1; fi
xsetroot -solid '#090d1b' >/dev/null 2>&1 || true
if command -v feh >/dev/null; then
  wallpaper="$(python3 -c "import json,os; p=os.path.expanduser("~/.config/novaos/settings.json"); print(json.load(open(p)).get("wallpaper", "$APP/assets/wallpapers/nova-night.webp"))" 2>/dev/null || echo "$APP/assets/wallpapers/nova-night.webp")"
  [ -f "$wallpaper" ] && feh --no-fehbg --bg-fill "$wallpaper" >>"$STATE/wallpaper.log" 2>&1 || true
fi
python3 "$APP/nova-shell/main.py" >>"$STATE/novashell.log" 2>&1 & children+=("$!")
wait "${children[${#children[@]}-1]}"
