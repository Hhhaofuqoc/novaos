#!/bin/bash
# Configure real XFCE components. Never reset a user's layout on a routine login.
set -euo pipefail
profile=${1:-lite}
theme=${2:-dark}
reset=${3:-}
case "$profile" in lite|balanced|ultra) ;; *) echo 'Profile must be lite, balanced or ultra.' >&2; exit 2;; esac
case "$theme" in dark) gtk_theme=NovaOS-Dark;; light) gtk_theme=NovaOS-Light;; *) echo 'Theme must be dark or light.' >&2; exit 2;; esac
if [[ -n "$reset" && "$reset" != --reset-layout ]]; then
    echo 'Usage: apply-xfce.sh [lite|balanced|ultra] [dark|light] [--reset-layout]' >&2
    exit 2
fi
command -v xfconf-query >/dev/null || { echo 'XFCE xfconf-query is required.' >&2; exit 1; }
[[ -n ${DISPLAY:-} && -n ${DBUS_SESSION_BUS_ADDRESS:-} ]] || { echo 'Run inside your XFCE X11/D-Bus session.' >&2; exit 1; }
assets=${NOVAOS_ASSETS:-/usr/share/novaos}
config=${XDG_CONFIG_HOME:-$HOME/.config}
state="$config/novaos"
mkdir -p "$state"
chmod 700 "$state"
# mkdir acts as a process-safe lock without requiring flock on Android.
lock="$state/theme.lock"
if ! mkdir "$lock" 2>/dev/null; then
    echo "Theme application is already running, or a stale lock exists: $lock" >&2
    exit 1
fi
trap 'rmdir "$lock"' EXIT
set_value() {
    local channel=$1 key=$2 type=$3 value=$4
    if xfconf-query -c "$channel" -p "$key" >/dev/null 2>&1; then
        xfconf-query -c "$channel" -p "$key" -s "$value"
    else
        xfconf-query -c "$channel" -p "$key" -n -t "$type" -s "$value"
    fi
}
set_array() {
    local channel=$1 key=$2 type=$3
    shift 3
    if xfconf-query -c "$channel" -p "$key" >/dev/null 2>&1; then
        xfconf-query -c "$channel" -p "$key" -r -R
    fi
    local args=(-c "$channel" -p "$key" -n -a)
    for value in "$@"; do args+=(-t "$type" -s "$value"); done
    xfconf-query "${args[@]}"
}
plugin() { set_value xfce4-panel "/plugins/plugin-$1" string "$2"; }
launcher() {
    local id=$1 title=$2 icon=$3 command=$4
    local dest="$config/xfce4/panel/launcher-$id"
    mkdir -p "$dest"
    cat > "$dest/novaos.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$title
Exec=$command
Icon=$icon
Terminal=false
StartupNotify=true
EOF
    plugin "$id" launcher
    set_array xfce4-panel "/plugins/plugin-$id/items" string novaos.desktop
}
set_value xsettings /Net/ThemeName string "$gtk_theme"
set_value xsettings /Net/IconThemeName string NovaOS
set_value xsettings /Gtk/FontName string 'DejaVu Sans 10'
set_value xsettings /Gtk/CursorThemeName string Adwaita
set_value xsettings /Gtk/CursorThemeSize int 28
set_value xfwm4 /general/theme string "$gtk_theme"
set_value xfwm4 /general/title_font string 'DejaVu Sans Bold 10'
set_value xfwm4 /general/button_layout string 'O|HMC'
# XFWM has compositing/shadows but does not implement blur. Ultra does not invent it.
composite=true
animation=true
[[ "$profile" != lite ]] || { composite=false; animation=false; }
set_value xfwm4 /general/use_compositing bool "$composite"
set_value xfwm4 /general/show_frame_shadow bool "$composite"
set_value xfwm4 /general/show_popup_shadow bool "$composite"
set_value xsettings /Gtk/EnableAnimations bool "$animation"
set_value xfwm4 /general/workspace_count int 2
# First run applies the layout; further profile/theme changes preserve rearrangements.
if [[ ! -f "$state/layout-v1" || "$reset" == --reset-layout ]]; then
    backup="$state/backups/xfce-$(date -u +%Y%m%dT%H%M%S)-$$"
    mkdir -p "$backup"
    if [[ -d "$config/xfce4" ]]; then cp -a "$config/xfce4" "$backup/"; fi
    xfconf-query -c xfce4-panel -lv > "$backup/panel-properties.txt" 2>/dev/null || true
    # The panel is restarted after all properties are coherent.
    timeout --kill-after=1s 3s xfce4-panel --quit >/dev/null 2>&1 || true
    for property in /panels /plugins; do
        if xfconf-query -c xfce4-panel -p "$property" >/dev/null 2>&1; then
            xfconf-query -c xfce4-panel -p "$property" -r -R
        fi
    done
    set_value xfce4-panel /configver int 2
    set_array xfce4-panel /panels int 1 2
    set_value xfce4-panel /panels/panel-1/position string 'p=6;x=0;y=0'
    set_value xfce4-panel /panels/panel-1/position-locked bool true
    set_value xfce4-panel /panels/panel-1/size uint 42
    set_value xfce4-panel /panels/panel-1/length uint 98
    set_value xfce4-panel /panels/panel-1/length-adjust bool false
    set_value xfce4-panel /panels/panel-1/span-monitors bool false
    set_value xfce4-panel /panels/panel-1/enter-opacity uint 100
    set_value xfce4-panel /panels/panel-1/leave-opacity uint 100
    set_array xfce4-panel /panels/panel-1/plugin-ids int 1 2 3 4 5 6 7 8 9
    plugin 1 applicationsmenu
    set_value xfce4-panel /plugins/plugin-1/button-title string NovaOS
    set_value xfce4-panel /plugins/plugin-1/button-icon string novaos
    set_value xfce4-panel /plugins/plugin-1/show-button-title bool true
    plugin 2 tasklist
    set_value xfce4-panel /plugins/plugin-2/flat-buttons bool true
    set_value xfce4-panel /plugins/plugin-2/show-handle bool false
    set_value xfce4-panel /plugins/plugin-2/grouping uint 1
    plugin 3 separator
    set_value xfce4-panel /plugins/plugin-3/expand bool true
    set_value xfce4-panel /plugins/plugin-3/style uint 0
    plugin 4 clock
    set_value xfce4-panel /plugins/plugin-4/digital-format string '%a %d %b   %H:%M'
    set_value xfce4-panel /plugins/plugin-4/tooltip-format string '%A, %d %B %Y'
    plugin 5 systray
    set_value xfce4-panel /plugins/plugin-5/icon-size int 22
    plugin 6 pulseaudio
    plugin 7 notification-plugin
    launcher 8 'NovaSettings' novaos-settings 'novaos settings'
    plugin 9 pager
    set_value xfce4-panel /panels/panel-2/position string 'p=10;x=0;y=0'
    set_value xfce4-panel /panels/panel-2/position-locked bool true
    set_value xfce4-panel /panels/panel-2/size uint 54
    set_value xfce4-panel /panels/panel-2/length uint 1
    set_value xfce4-panel /panels/panel-2/length-adjust bool true
    set_value xfce4-panel /panels/panel-2/autohide-behavior uint 1
    set_value xfce4-panel /panels/panel-2/enter-opacity uint 100
    set_value xfce4-panel /panels/panel-2/leave-opacity uint 100
    set_array xfce4-panel /panels/panel-2/plugin-ids int 10 11 12 13 14 15 16 17
    launcher 10 'Aplicativos' novaos 'xfce4-appfinder'
    launcher 11 'NovaTerminal' novaos-terminal 'xfce4-terminal'
    launcher 12 'NovaFiles' novaos-files 'thunar'
    launcher 13 'Navegador' novaos-browser 'firefox-esr'
    launcher 14 'NovaMusic' novaos-music 'novaos music'
    launcher 15 'NovaNotes' novaos-notes 'novaos notes'
    launcher 16 'NovaSettings' novaos-settings 'novaos settings'
    launcher 17 'NovaMonitor' novaos-monitor 'novaos monitor'
    set_value xfce4-desktop /desktop-icons/style int 0
    printf '%s\n' "$backup" > "$state/layout-v1"
    xfce4-panel >/dev/null 2>&1 &
fi
# Choose portrait art only for a portrait framebuffer; Android is often landscape.
wallpaper="$assets/wallpapers/novaos-desktop.png"
resolution=$(xrandr --current 2>/dev/null | awk '/\*/ {print $1; exit}') || true
if [[ "$resolution" =~ ^([0-9]+)x([0-9]+)$ ]] && (( BASH_REMATCH[2] > BASH_REMATCH[1] )); then
    wallpaper="$assets/wallpapers/novaos-mobile.png"
fi
if [[ ! -f "$wallpaper" ]]; then wallpaper="${wallpaper%.png}.svg"; fi
[[ -f "$wallpaper" ]] || { echo "Missing wallpaper: $wallpaper" >&2; exit 1; }
# Existing outputs use names such as monitorVirtual-1, never assume monitor0 only.
mapfile -t outputs < <(xfconf-query -c xfce4-desktop -l 2>/dev/null | sed -n 's#\(/backdrop/screen[0-9]*/monitor[^/]*/workspace[0-9]*\)/.*#\1#p' | sort -u)
# A fresh XFCE profile does not persist backdrop defaults until they change.
# Discover current XRandR connector names, instead of guessing monitor0 only.
mapfile -t connectors < <(xrandr --query 2>/dev/null | awk '$2 == "connected" {print $1}')
for connector in "${connectors[@]}"; do
    # XFCE strips slash separators from monitor identifiers in xfconf paths.
    connector=${connector//\//_}
    for workspace in 0 1; do
        outputs+=("/backdrop/screen0/monitor${connector}/workspace${workspace}")
    done
done
if [[ ${#outputs[@]} -eq 0 ]]; then
    outputs=(/backdrop/screen0/monitor0/workspace0 /backdrop/screen0/monitor0/workspace1)
fi
set_value xfce4-desktop /backdrop/single-workspace-mode bool true
set_value xfce4-desktop /backdrop/single-workspace-number int 0
for output in "${outputs[@]}"; do
    set_value xfce4-desktop "$output/last-image" string "$wallpaper"
    set_value xfce4-desktop "$output/image-style" int 5
    set_value xfce4-desktop "$output/color-style" int 0
    set_value xfce4-desktop "$output/backdrop-cycle-enable" bool false
 done
# Ensure a running xfdesktop rereads properties created after its first frame.
if command -v xfdesktop >/dev/null; then
    timeout --kill-after=1s 3s xfdesktop --reload >/dev/null 2>&1 || true
fi
printf '%s %s\n' "$profile" "$theme" > "$state/appearance"
