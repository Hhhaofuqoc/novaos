#!/usr/bin/env bash
# Install NovaOS-owned system files. No network, package operations or HOME writes.
set -euo pipefail
repo=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
destdir=
with_music=true
usage() {
    cat <<HELP
Usage: $0 [--destdir DIRECTORY] [--without-music]
Install NovaOS applications and assets under /usr. Use --destdir for packaging.
Without --destdir this requires root inside Debian; it never edits user homes.
This script does not install APT dependencies. See desktop/packages-lite.txt.
HELP
}
while (($#)); do
    case "$1" in
        --destdir) destdir=${2:?Missing destination directory}; shift 2 ;;
        --without-music) with_music=false; shift ;;
        --help|-h) usage; exit 0 ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done
if [[ -z $destdir ]]; then
    [[ $(id -u) == 0 ]] || { echo 'Use --destdir for staging, or run as root inside Debian.' >&2; exit 1; }
    destdir=/
fi
mkdir -p -- "$destdir"
destdir=$(CDPATH='' cd -- "$destdir" && pwd)
[[ -f $repo/applications/novaos/__main__.py ]] || { echo 'Incomplete source: applications/novaos/__main__.py is missing.' >&2; exit 1; }
# Exact modes do not depend on the checkout umask. Symlinks in source are ignored.
install_file() {
    local src=$1 rel=$2 mode=${3:-0644}
    install -d -m 0755 -- "$destdir/$(dirname -- "$rel")"
    install -m "$mode" -- "$src" "$destdir/$rel"
}
copy_tree() {
    local src=$1 rel=$2 path mode
    [[ -d $src ]] || return 0
    while IFS= read -r -d '' path; do
        mode=0644
        [[ $path != *.sh ]] || mode=0755
        install_file "$path" "$rel/${path#"$src/"}" "$mode"
    done < <(find "$src" -type f ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' -print0)
}
# Do not remove old code or resources recursively: this is safe to rerun on update.
copy_tree "$repo/applications/novaos" usr/lib/python3/dist-packages/novaos
copy_tree "$repo/themes" usr/share/novaos/themes
copy_tree "$repo/wallpapers" usr/share/novaos/wallpapers
copy_tree "$repo/themes/NovaOS-Dark" usr/share/themes/NovaOS-Dark
copy_tree "$repo/themes/NovaOS-Light" usr/share/themes/NovaOS-Light
copy_tree "$repo/themes/icons/NovaOS" usr/share/icons/NovaOS
for asset in cover.svg LICENSE; do
    [[ ! -f $repo/music/$asset ]] || install_file "$repo/music/$asset" "usr/share/novaos/music/$asset"
done
if [[ $with_music == true ]]; then
    copy_tree "$repo/music/generated" usr/share/novaos/music/generated
fi
copy_tree "$repo/docs" usr/share/doc/novaos-desktop
[[ ! -f $repo/LICENSE ]] || install_file "$repo/LICENSE" usr/share/doc/novaos-desktop/copyright
if [[ -f $repo/installers/apt-helper ]]; then
    install_file "$repo/installers/apt-helper" usr/lib/novaos/apt-helper 0755
fi
install -d -m 0755 -- "$destdir/usr/bin" "$destdir/usr/share/applications" "$destdir/etc/xdg/autostart"
cat > "$destdir/usr/bin/novaos" <<'LAUNCHER'
#!/bin/sh
exec /usr/bin/python3 -m novaos "$@"
LAUNCHER
chmod 0755 "$destdir/usr/bin/novaos"
wrapper() {
    local name=$1 command=$2
    printf '#!/bin/sh\nexec %s "$@"\n' "$command" > "$destdir/usr/bin/$name"
    chmod 0755 "$destdir/usr/bin/$name"
}
for command in music notes settings monitor welcome profile theme diagnostics store updater; do
    wrapper "novaos-$command" "novaos $command"
done
wrapper novaos-files thunar
wrapper novaos-terminal xfce4-terminal
wrapper novaos-editor mousepad
wrapper novaos-browser firefox-esr
entry() {
    local id=$1 name=$2 comment=$3 exec_line=$4 icon=$5 categories=$6
    cat > "$destdir/usr/share/applications/$id.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Version=1.0
Name=$name
Comment=$comment
Exec=$exec_line
Icon=$icon
Terminal=false
StartupNotify=true
Categories=$categories
ENTRY
    chmod 0644 "$destdir/usr/share/applications/$id.desktop"
}
entry novaos-welcome NovaWelcome 'Your universe. Your system.' 'novaos welcome' novaos 'System;'
entry novaos-settings NovaSettings 'Aparência e desempenho do NovaOS' 'novaos settings' novaos-settings 'Settings;DesktopSettings;'
entry novaos-monitor NovaMonitor 'CPU, memória, armazenamento e processos reais' 'novaos monitor' novaos-monitor 'System;Monitor;'
entry novaos-music NovaMusic 'Música instrumental original e biblioteca local' 'novaos music' novaos-music 'AudioVideo;Audio;Player;'
entry novaos-notes NovaNotes 'Notas locais persistentes' 'novaos notes' novaos-notes 'Utility;TextEditor;'
entry novaos-files NovaFiles 'Arquivos e pastas com Thunar' 'novaos-files %U' novaos-files 'System;FileTools;FileManager;'
entry novaos-terminal NovaTerminal 'Terminal Linux real com XFCE Terminal' 'novaos-terminal' novaos-terminal 'System;TerminalEmulator;'
entry novaos-editor NovaEditor 'Editor de texto e código com Mousepad' 'novaos-editor %F' novaos-editor 'Utility;TextEditor;'
entry novaos-browser 'Navegador Firefox ESR' 'Navegar na Web' 'novaos-browser %U' novaos-browser 'Network;WebBrowser;'
entry novaos-store NovaStore 'Instalar pacotes dos repositórios APT configurados' 'novaos store' novaos-store 'System;PackageManager;'
entry novaos-updater NovaUpdater 'Revisar e instalar atualizações Debian' 'novaos updater' novaos-updater 'System;PackageManager;'
cat > "$destdir/etc/xdg/autostart/novaos-session.desktop" <<'AUTOSTART'
[Desktop Entry]
Type=Application
Name=NovaOS session configuration
Comment=Apply the saved NovaOS profile and first-run desktop layout
Exec=novaos session-init
TryExec=novaos
OnlyShowIn=XFCE;
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
AUTOSTART
chmod 0644 "$destdir/etc/xdg/autostart/novaos-session.desktop"
# No default user config is copied over existing preferences or personal data.
printf 'Installed NovaOS-owned files into %s\n' "$destdir"
