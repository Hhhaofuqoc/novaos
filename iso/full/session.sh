#!/bin/bash
# NovaOS Full — real X11 user session, no Termux or PRoot involved.
set -u
export XDG_CURRENT_DESKTOP=NovaShell
export XDG_SESSION_DESKTOP=novaos
export DESKTOP_SESSION=novaos
export GTK_THEME=Adwaita:dark
export NO_AT_BRIDGE=1
APP=/opt/novaos/app
LOGS="$HOME/.local/state/novaos/logs"
mkdir -p "$LOGS" "$HOME/.config/novaos"
log(){ printf '[NovaOS VM] %s\n' "$*" | tee -a "$LOGS/session.log"; }
if ! command -v xdpyinfo >/dev/null || ! xdpyinfo -display "${DISPLAY:-:0}" >/dev/null 2>&1; then
  log "ERROR: No accessible graphical X11 display (${DISPLAY:-unset})."
  exit 1
fi
if wmctrl -m >/dev/null 2>&1; then
  log 'Existing window manager detected; not starting another Openbox.'
else
  openbox --config-file "$APP/config/openbox/rc.xml" >"$LOGS/openbox.log" 2>&1 &
  WM_PID=$!
  sleep 1
  if ! kill -0 "$WM_PID" 2>/dev/null; then
    log 'Openbox exited unexpectedly. See openbox.log.'
    xterm -T 'NovaOS Openbox error' -e sh -c 'tail -80 "$HOME/.local/state/novaos/logs/openbox.log"; read -r _' || true
    exit 1
  fi
fi
DEFAULT_WALLPAPER="$APP/assets/wallpapers/nova-night.webp"
WALLPAPER="$(/usr/bin/python3 - "$DEFAULT_WALLPAPER" <<'PY'
import json
import sys
from pathlib import Path
try:
    config=json.loads((Path.home()/'.config/novaos/settings.json').read_text(encoding='utf8'))
    chosen=config.get('wallpaper') if isinstance(config,dict) else None
    print(chosen if isinstance(chosen,str) and Path(chosen).is_file() else sys.argv[1])
except (OSError,ValueError,TypeError):
    print(sys.argv[1])
PY
)"
feh --no-fehbg --bg-fill "$WALLPAPER" >>"$LOGS/wallpaper.log" 2>&1 || log 'Wallpaper unavailable.'
if command -v lxpolkit >/dev/null 2>&1; then lxpolkit >>"$LOGS/polkit.log" 2>&1 & fi
if command -v nm-applet >/dev/null 2>&1; then nm-applet >>"$LOGS/network-applet.log" 2>&1 & fi
if command -v spice-vdagent >/dev/null 2>&1; then spice-vdagent >>"$LOGS/spice-vdagent.log" 2>&1 & fi
# Real Python-GI from Debian, not Termux Python.
log 'Starting NovaShell GTK3.'
/usr/bin/python3 -u "$APP/nova-shell/main.py" >>"$LOGS/novashell.log" 2>&1
rc=$?
log "NovaShell exited with code $rc."
# If the desktop crashes, display the actual traceback rather than just wallpaper.
exec xterm -T 'NovaOS diagnostic' -geometry 102x30 -e /bin/bash -c '
  echo "NovaShell failed. See log below:"; echo;
  tail -n 100 "$HOME/.local/state/novaos/logs/novashell.log";
  echo; echo "Logs: ~/.local/state/novaos/logs/";
  read -rp "Enter to close... " _
'
