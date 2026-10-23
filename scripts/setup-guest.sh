#!/bin/bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
SRC=/mnt/novaos-source
DEST=/opt/novaos/app
say(){ echo "[NovaOS guest] $*"; }
[ -f "$SRC/nova-shell/main.py" ] || { echo 'Projeto não encontrado no bind /mnt/novaos-source' >&2; exit 1; }
command -v apt-get >/dev/null || { echo 'Contêiner existente não é baseado em Debian/Ubuntu (APT ausente). Nada foi modificado.' >&2; exit 1; }
. /etc/os-release
case "$ID" in debian|ubuntu) ;; *) say "Distribuição $ID; apt presente; compatibilidade não garantida";; esac
say "Base Linux existente: ${PRETTY_NAME:-$ID} (será preservada)"
apt-get update -qq
# Pacotes modestos, sem XFCE, KDE, GNOME Shell, systemd como serviço ou x86.
apt-get install -y --no-install-recommends \
  openbox python3 python3-gi python3-cairo python3-psutil \
  gir1.2-gtk-3.0 dbus-x11 wmctrl xdotool x11-utils x11-xserver-utils \
  feh pcmanfm lxterminal geany mpv gpicview \
  libglib2.0-bin gvfs gvfs-backends xdg-utils pulseaudio-utils playerctl \
  procps iproute2 adwaita-icon-theme hicolor-icon-theme \
  fonts-dejavu-core fonts-noto-core librsvg2-common xterm
# Fastfetch é leve, mas pode não existir em bases Debian/Ubuntu mais antigas.
# Instalar somente quando o próprio APT oferecer o pacote; ausência não derruba a NovaOS.
if apt-cache show fastfetch >/dev/null 2>&1; then
  apt-get install -y --no-install-recommends fastfetch || say 'Fastfetch não pôde ser instalado; os demais componentes continuarão.'
else
  say 'Fastfetch indisponível nesta base; nova-info/nova-fetch permanecem disponíveis.'
fi
if ! id nova >/dev/null 2>&1; then
  say 'Criando usuário nova sem alterar usuários existentes.'
  useradd -m -s /bin/bash nova
fi
mkdir -p /opt/novaos /var/backups/novaos
if [ -d "$DEST" ] && [ -f "$DEST/.novaos-owned" ]; then
  # Arquivos antigos da aplicação, não dados pessoais. Cópia de segurança com timestamp.
  t="$(date +%Y%m%d-%H%M%S)"
  cp -a "$DEST" "/var/backups/novaos/app-$t"
elif [ -e "$DEST" ]; then
  echo "Diretório $DEST já existe, mas não pertence a este instalador. Nenhum arquivo alterado." >&2
  exit 1
fi
mkdir -p "$DEST"
cp -a "$SRC/." "$DEST/"
touch "$DEST/.novaos-owned"
chmod 755 "$DEST/scripts/guest-session.sh" "$DEST/scripts/guest-diag.sh"
install -m 755 "$DEST/scripts/nova-info" /usr/local/bin/nova-info
install -m 755 "$DEST/scripts/nova-settings" /usr/local/bin/nova-settings
install -m 755 "$DEST/scripts/nova-logo" /usr/local/bin/nova-logo
install -m 755 "$DEST/scripts/nova-fetch" /usr/local/bin/nova-fetch
# Acesso read-only ao projeto, configurações pessoais ficam em ~nova/.config/novaos.
chmod -R a+rX "$DEST"
mkdir -p /home/nova/.config/novaos /home/nova/.local/share/applications
chown -R nova:nova /home/nova/.config/novaos
# Configurações nativas dos fetchers; backups antes de qualquer alteração existente.
python3 "$DEST/scripts/enable-branding.py" /home/nova
# A identidade também vale para o shell administrativo root dentro do contêiner.
python3 "$DEST/scripts/enable-branding.py" /root
# Não sobrescrever arquivos existentes nem rc.xml/GTK do usuário.
if [ ! -e /home/nova/.local/share/applications/nova-center.desktop ]; then
  install -m 644 "$DEST/config/nova-center.desktop" /home/nova/.local/share/applications/nova-center.desktop
  chown nova:nova /home/nova/.local/share/applications/nova-center.desktop
fi
say 'Pacotes, NovaShell e atalho de configurações preparados.'
# NÃO limpar cache global de outras instalações.
