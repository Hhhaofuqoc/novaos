#!/usr/bin/env bash
# Real Plasma 6 color scheme, panel layout, wallpaper and effect budget.
set -euo pipefail
profile=${1:-lite}
theme=${2:-dark}
case $profile in lite|balanced|ultra) ;; *) echo 'Perfil inválido.' >&2; exit 2;; esac
case $theme in dark|light) ;; *) echo 'Tema inválido.' >&2; exit 2;; esac
assets=${NOVAOS_ASSETS:-/usr/share/novaos}
config=${XDG_CONFIG_HOME:-$HOME/.config}
data=${XDG_DATA_HOME:-$HOME/.local/share}
state="$config/novaos"
mkdir -p "$state" "$data/color-schemes"
install -m 644 "$assets/themes/plasma/NovaOS.colors" "$data/color-schemes/NovaOS.colors"
command -v kwriteconfig6 >/dev/null || { echo 'Plasma 6 não instalado.' >&2; exit 1; }
if [[ ! -f $state/plasma-config-v1 ]]; then
  backup="$state/backups/plasma-$(date -u +%Y%m%dT%H%M%S)-$$"
  mkdir -p "$backup"
  for file in kdeglobals kwinrc plasma-org.kde.plasma.desktop-appletsrc; do
    [[ ! -f $config/$file ]] || cp -a "$config/$file" "$backup/"
  done
  printf '%s\n' "$backup" > "$state/plasma-config-v1"
fi
kwriteconfig6 --file kdeglobals --group KDE --key widgetStyle Breeze
kwriteconfig6 --file kdeglobals --group Icons --key Theme NovaOS
kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key library org.kde.breeze
kwriteconfig6 --file kwinrc --group Compositing --key Enabled "$([[ $profile == lite ]] && echo false || echo true)"
kwriteconfig6 --file kwinrc --group Plugins --key blurEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key wobblywindowsEnabled false
kwriteconfig6 --file ksmserverrc --group General --key loginMode emptySession
# Ensure GTK apps use the same dark/light identity under Plasma.
python3 - "$config" "$theme" <<'PY'
import configparser, pathlib, sys
directory, theme = pathlib.Path(sys.argv[1]), sys.argv[2]
path = directory/'gtk-3.0/settings.ini'
parser = configparser.ConfigParser(interpolation=None)
parser.read(path)
if not parser.has_section('Settings'): parser.add_section('Settings')
parser.set('Settings','gtk-theme-name','NovaOS-Dark' if theme == 'dark' else 'NovaOS-Light')
parser.set('Settings','gtk-icon-theme-name','NovaOS')
path.parent.mkdir(parents=True,exist_ok=True)
with path.open('w') as stream: parser.write(stream)
PY
[[ -n ${DISPLAY:-} && -n ${DBUS_SESSION_BUS_ADDRESS:-} ]] || exit 0
scheme=NovaOS
[[ $theme == dark ]] || scheme=BreezeLight
plasma-apply-colorscheme "$scheme" >/dev/null
kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure >/dev/null 2>&1 || true
wallpaper="$assets/wallpapers/novaos-desktop.png"
[[ -f $wallpaper ]] || { echo 'Wallpaper NovaOS ausente.' >&2; exit 1; }
script=$(python3 - "$wallpaper" "$state/plasma-layout-v1" <<'PY'
import json, pathlib, sys
image = pathlib.Path(sys.argv[1]).as_uri()
print('var screens = desktops(); for (var i=0;i<screens.length;i++) { var d=screens[i]; d.wallpaperPlugin="org.kde.image"; d.currentConfigGroup=["Wallpaper","org.kde.image","General"]; d.writeConfig("Image",'+json.dumps(image)+'); }')
if not pathlib.Path(sys.argv[2]).exists():
    print('''
var old = panels(); for (var j=0;j<old.length;j++) old[j].remove();
var top = new Panel; top.location="top"; top.height=38; top.floating=true;
var kickoff=top.addWidget("org.kde.plasma.kickoff"); kickoff.currentConfigGroup=["General"]; kickoff.writeConfig("icon","/usr/share/icons/NovaOS/scalable/apps/novaos.svg");
top.addWidget("org.kde.plasma.pager");
top.addWidget("org.kde.plasma.panelspacer");
top.addWidget("org.kde.plasma.digitalclock");
top.addWidget("org.kde.plasma.systemtray");
var dock = new Panel; dock.location="bottom"; dock.height=56;
dock.alignment="center"; dock.lengthMode="fit"; dock.minimumLength=480; dock.maximumLength=720; dock.length=620; dock.floating=true;
var tasks=dock.addWidget("org.kde.plasma.icontasks"); tasks.currentConfigGroup=["General"];
tasks.writeConfig("launchers",["file:///usr/share/applications/novaos-welcome.desktop","file:///usr/share/applications/novaos-plasma-terminal.desktop","file:///usr/share/applications/novaos-plasma-files.desktop","file:///usr/share/applications/novaos-browser.desktop","file:///usr/share/applications/novaos-music.desktop","file:///usr/share/applications/novaos-notes.desktop","applications:systemsettings.desktop"]);
''')
PY
)
gdbus call --session --dest org.kde.plasmashell --object-path /PlasmaShell --method org.kde.PlasmaShell.evaluateScript "$script" >/dev/null
touch "$state/plasma-layout-v1"
printf '%s %s\n' "$profile" "$theme" > "$state/plasma-appearance"
