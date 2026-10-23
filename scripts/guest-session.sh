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
  wallpaper="$(/usr/bin/python3 - "$APP/assets/wallpapers/nova-night.webp" <<'PY'
import json
import sys
from pathlib import Path
fallback = sys.argv[1]
try:
    config = json.loads((Path.home() / '.config/novaos/settings.json').read_text(encoding='utf-8'))
    selected = config.get('wallpaper') if isinstance(config, dict) else None
    print(selected if isinstance(selected, str) and Path(selected).is_file() else fallback)
except (OSError, ValueError, TypeError):
    print(fallback)
PY
)"
  [ -f "$wallpaper" ] && feh --no-fehbg --bg-fill "$wallpaper" >>"$STATE/wallpaper.log" 2>&1 || true
fi
echo "[NovaOS] Iniciando NovaShell em DISPLAY=${DISPLAY:-indefinido}" >>"$STATE/novashell.log"
/usr/bin/python3 -u "$APP/nova-shell/main.py" >>"$STATE/novashell.log" 2>&1 &
shell_pid=$!
children+=("$shell_pid")
if wait "$shell_pid"; then
  echo "[NovaOS] NovaShell encerrou normalmente." >>"$STATE/novashell.log"
else
  rc=$?
  echo "[NovaOS] NovaShell encerrou com erro (codigo $rc)." | tee -a "$STATE/novashell.log"
  if command -v xterm >/dev/null 2>&1; then
    xterm -T 'NovaOS - erro da NovaShell' -geometry 100x30 -fa 'DejaVu Sans Mono' -fs 10 -e /bin/bash -c '
      echo "Falha ao abrir a NovaShell. Logs de diagnostico:"
      echo
      tail -n 80 "$HOME/.local/state/novaos/logs/novashell.log"
      echo
      echo "Copie esta mensagem e envie ao ChatGPT."
      printf "Pressione Enter para fechar... "
      read -r _
    ' || true
  fi
  exit "$rc"
fi
