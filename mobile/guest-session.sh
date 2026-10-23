#!/bin/bash
set -euo pipefail
[[ $(id -un) == nova ]] || { echo 'A sessão deve executar como usuário nova.' >&2; exit 1; }
export XDG_RUNTIME_DIR=/tmp/novaos-runtime-nova
install -d -m 700 "$XDG_RUNTIME_DIR"
desktop=${1:-xfce}
export XDG_SESSION_TYPE=x11
export NO_AT_BRIDGE=1 LIBGL_ALWAYS_SOFTWARE=1
export NOVAOS_MOBILE=1
unset SESSION_MANAGER DBUS_SESSION_BUS_ADDRESS
# On mobile, locked sessions cannot authenticate against Android. Do not start
# a screen locker or power daemon; Android remains responsible for these.
mkdir -p "$HOME/.config/autostart"
for service in xfce4-power-manager xfce4-screensaver light-locker; do
  if [[ ! -f "$HOME/.config/autostart/$service.desktop" ]]; then
    printf '[Desktop Entry]\nType=Application\nName=%s\nHidden=true\n' "$service" > "$HOME/.config/autostart/$service.desktop"
  fi
done
case "$desktop" in
  xfce)
    export XDG_CURRENT_DESKTOP=XFCE DESKTOP_SESSION=xfce
    exec dbus-run-session -- startxfce4 ;;
  plasma)
    command -v startplasma-x11 >/dev/null || {
      echo 'Plasma ainda não instalado. Aplique a atualização Plasma do NovaOS.' >&2; exit 1;
    }
    export XDG_CURRENT_DESKTOP=KDE DESKTOP_SESSION=plasma KDE_SESSION_VERSION=6
    export QT_QUICK_BACKEND=software QT_X11_NO_MITSHM=1
    # PRoot has no systemd --user manager. Plasma still supports direct startup.
    command -v kwriteconfig6 >/dev/null && kwriteconfig6 --file startkderc --group General --key systemdBoot false
    kwriteconfig6 --file kscreenlockerrc --group Daemon --key Autolock false
    kwriteconfig6 --file kscreenlockerrc --group Daemon --key LockOnResume false
    initial_profile=$(novaos profile)
    composition=false
    case "$initial_profile" in balanced|ultra) composition=true;; esac
    kwriteconfig6 --file kwinrc --group Compositing --key Enabled "$composition"
    exec dbus-run-session -- startplasma-x11 ;;
  *) echo 'Desktop inválido: escolha xfce ou plasma.' >&2; exit 2 ;;
esac
