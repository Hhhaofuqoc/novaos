#!/bin/bash
set +e
echo '=== NovaOS Diagnóstico PRoot ==='
echo "Usuário: $(id -un) | Kernel reportado: $(uname -r)"
echo "DISPLAY=${DISPLAY:-indefinido} | XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-indefinido}"
for p in openbox python3 feh wmctrl xdpyinfo; do command -v "$p" || echo "AUSENTE: $p"; done
python3 - <<'PY'
try:
    import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk
    print('GTK 3 via gi: OK (importação)')
except Exception as e: print('GTK 3: ERRO:',e)
PY
xdpyinfo 2>&1 | head -n 7
echo '=== Últimos logs ==='
for l in "$HOME"/.local/state/novaos/logs/*.log; do [ -f "$l" ] && { echo "-- $l --"; tail -n 12 "$l"; }; done
