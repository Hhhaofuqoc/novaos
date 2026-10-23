#!/usr/bin/env bash
# Run genuine X11/GTK integration against an isolated HOME and staged installation.
set -euo pipefail
repo=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
report=${1:-"$repo/dist/validation"}
mkdir -p "$report"
report=$(CDPATH='' cd -- "$report" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/novaos-gui.XXXXXXXX")
cleanup() { rm -rf -- "$work"; }
trap cleanup EXIT
python=${NOVAOS_TEST_PYTHON:-/usr/bin/python3}
# Optional unpacked Debian packages, useful when root is unavailable.
if [[ -n ${NOVAOS_TEST_RUNTIME:-} ]]; then
    export PATH="$NOVAOS_TEST_RUNTIME/usr/bin:$PATH"
    export LD_LIBRARY_PATH="$NOVAOS_TEST_RUNTIME/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    export GI_TYPELIB_PATH="$NOVAOS_TEST_RUNTIME/usr/lib/x86_64-linux-gnu/girepository-1.0${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"
    export PYTHONPATH="$NOVAOS_TEST_RUNTIME/usr/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}"
fi
for program in Xvfb xauth wmctrl xdotool xprop xdpyinfo xfwm4 xfdesktop xfsettingsd xfce4-panel dbus-run-session; do
    command -v "$program" >/dev/null || { printf 'Missing integration dependency: %s\n' "$program" >&2; exit 1; }
done
"$python" -c 'import gi, psutil; gi.require_version("Gtk", "3.0"); gi.require_version("Gst", "1.0"); from gi.repository import Gtk, Gst'
export HOME="$work/home"
export XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share" XDG_CACHE_HOME="$HOME/.cache"
export XDG_RUNTIME_DIR="$work/runtime"
mkdir -m 700 -p "$HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_RUNTIME_DIR"
mkdir -p "$XDG_DATA_HOME/novaos"
printf 'preserve user data through installation and update\n' > "$XDG_DATA_HOME/novaos/persistence-sentinel"
bash "$repo/installers/install-system.sh" --destdir "$work/stage" > "$report/install.log"
bash "$repo/installers/install-system.sh" --destdir "$work/stage" >> "$report/install.log"
test "$(cat "$XDG_DATA_HOME/novaos/persistence-sentinel")" = 'preserve user data through installation and update'
export PATH="$work/stage/usr/bin:$PATH"
export PYTHONPATH="$work/stage/usr/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}"
export XDG_DATA_DIRS="$work/stage/usr/share:/usr/local/share:/usr/share"
# GTK's theme lookup uses ~/.themes; XDG_DATA_DIRS alone is not sufficient.
ln -s "$work/stage/usr/share/themes" "$HOME/.themes"
export NOVAOS_ASSETS="$work/stage/usr/share/novaos"
export NO_AT_BRIDGE=1
export XDG_CURRENT_DESKTOP=XFCE
export NOVAOS_AUDIO_SINK=fakesink
export GSETTINGS_BACKEND=keyfile
export XAUTHORITY="$work/xauthority"
export NOVAOS_TEST_WORK="$work"
export NOVAOS_TEST_REPORT="$report"
# Avoid inherited display/bus from a user's normal desktop.
unset DISPLAY DBUS_SESSION_BUS_ADDRESS SESSION_MANAGER
exec_status=0
dbus-run-session -- "$python" "$repo/tests/integration/gui.py" || exec_status=$?
exit "$exec_status"
