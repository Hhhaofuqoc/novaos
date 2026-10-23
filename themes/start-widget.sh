#!/bin/bash
# Optional, bounded-refresh desktop widget. Run once from an XFCE session.
set -euo pipefail
if [[ ${NOVAOS_MOBILE:-0} == 1 || -f /etc/novaos/mobile ]]; then
    echo 'NovaMonitor is available on Mobile; the desktop Conky widget is disabled.' >&2
    exit 0
fi
command -v conky >/dev/null || { echo 'Install conky-std to use this optional widget.' >&2; exit 1; }
exec conky -c "${NOVAOS_ASSETS:-/usr/share/novaos}/themes/conky.conf"
