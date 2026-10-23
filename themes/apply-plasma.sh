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
if [[ ! -f $state/plasma-config-v2 ]]; then
  backup="$state/backups/plasma-$(date -u +%Y%m%dT%H%M%S)-$$"
  mkdir -p "$backup"
  for file in kdeglobals kwinrc plasma-org.kde.plasma.desktop-appletsrc konsolerc; do
    [[ ! -f $config/$file ]] || cp -a "$config/$file" "$backup/"
  done
  kwriteconfig6 --file konsolerc --group 'Desktop Entry' --key DefaultProfile NovaOS.profile
  printf '%s\n' "$backup" > "$state/plasma-config-v2"
fi
kwriteconfig6 --file kdeglobals --group KDE --key widgetStyle Breeze
kwriteconfig6 --file kdeglobals --group Icons --key Theme NovaOS
kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key library org.kde.breeze
kwriteconfig6 --file kwinrc --group Compositing --key Enabled "$([[ $profile == lite ]] && echo false || echo true)"
kwriteconfig6 --file kwinrc --group Plugins --key blurEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key wobblywindowsEnabled false
kwriteconfig6 --file ksmserverrc --group General --key loginMode emptySession
kwriteconfig6 --file kwinrc --group Desktops --key Number 4
kwriteconfig6 --file kwinrc --group Desktops --key Rows 1
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
# Breeze's default theme follows the actual NovaOS color scheme. breeze-dark
# has fixed gray colors and would override the requested midnight panels.
plasma-apply-desktoptheme default >/dev/null
kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure >/dev/null 2>&1 || true
wallpaper="$assets/wallpapers/novaos-night-room.png"
[[ -f $wallpaper ]] || { echo 'Wallpaper NovaOS ausente.' >&2; exit 1; }
script=$(python3 - "$wallpaper" "$state/plasma-layout-v2" <<'PY'
import json, pathlib, sys
image = pathlib.Path(sys.argv[1]).as_uri()
print('var screens = desktops(); for (var i=0;i<screens.length;i++) { var d=screens[i]; d.wallpaperPlugin="org.kde.image"; d.currentConfigGroup=["Wallpaper","org.kde.image","General"]; d.writeConfig("Image",'+json.dumps(image)+'); }')
if not pathlib.Path(sys.argv[2]).exists():
    print('''
var old = panels(); for (var j=0;j<old.length;j++) old[j].remove();
var top = new Panel; top.location="top"; top.height=30; top.floating=false;
var kickoff=top.addWidget("org.kde.plasma.kickoff"); kickoff.currentConfigGroup=["General"]; kickoff.writeConfig("icon","/usr/share/icons/NovaOS/scalable/apps/novaos.svg");
kickoff.writeConfig("menuLabel","NovaOS"); kickoff.writeConfig("favoritesDisplay",0); kickoff.writeConfig("appNameFormat",0);
kickoff.writeConfig("favorites",["novaos-browser.desktop","novaos-plasma-terminal.desktop","novaos-plasma-files.desktop","novaos-editor.desktop","novaos-music.desktop","novaos-monitor.desktop","novaos-settings.desktop","novaos-store.desktop","novaos-notes.desktop"]);
kickoff.writeConfig("systemFavorites",["logout"]); kickoff.writeConfig("primaryActions",1);
var pager=top.addWidget("org.kde.plasma.pager"); pager.currentConfigGroup=["General"]; pager.writeConfig("displayedText",0);
top.addWidget("org.kde.plasma.panelspacer");
top.addWidget("org.kde.plasma.systemtray");
top.addWidget("org.kde.plasma.digitalclock");
var dock = new Panel; dock.location="bottom"; dock.height=56;
dock.alignment="center"; dock.lengthMode="fit"; dock.minimumLength=480; dock.maximumLength=720; dock.length=620; dock.floating=true;
var dockmenu=dock.addWidget("org.kde.plasma.kickoff"); dockmenu.currentConfigGroup=["General"]; dockmenu.writeConfig("icon","/usr/share/icons/NovaOS/scalable/apps/novaos.svg");
var tasks=dock.addWidget("org.kde.plasma.icontasks"); tasks.currentConfigGroup=["General"];
tasks.writeConfig("launchers",["file:///usr/share/applications/novaos-plasma-files.desktop","file:///usr/share/applications/novaos-plasma-terminal.desktop","file:///usr/share/applications/novaos-browser.desktop","file:///usr/share/applications/novaos-editor.desktop","file:///usr/share/applications/novaos-music.desktop","applications:systemsettings.desktop"]);
''')
PY
)
gdbus call --session --dest org.kde.plasmashell --object-path /PlasmaShell --method org.kde.PlasmaShell.evaluateScript "$script" >/dev/null
touch "$state/plasma-layout-v2"
if [[ ! -f $state/plasma-favorites-v2 ]]; then
  # The daemon registers its bus name before its resource plugin is ready.
  # Wait briefly instead of losing the first favorite on a clean session.
  for ((attempt=0; attempt<10; attempt++)); do
    interfaces=$(gdbus introspect --session --dest org.kde.ActivityManager \
      --object-path /ActivityManager/Resources/Linking 2>/dev/null || true)
    [[ $interfaces != *LinkResourceToActivity* ]] || break
    sleep 0.3
  done
  favorites_ok=true
  for entry in browser plasma-terminal plasma-files editor music monitor settings store notes; do
    if ! gdbus call --session --dest org.kde.ActivityManager --object-path /ActivityManager/Resources/Linking \
      --method org.kde.ActivityManager.ResourcesLinking.LinkResourceToActivity \
      org.kde.plasma.favorites.applications "applications:novaos-$entry.desktop" :global >/dev/null; then
      favorites_ok=false
    fi
  done
  # Use the supported Activities API; keep any pre-existing personal favorites.
  [[ $favorites_ok != true ]] || touch "$state/plasma-favorites-v2"
fi
printf '%s %s\n' "$profile" "$theme" > "$state/plasma-appearance"
