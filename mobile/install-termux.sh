#!/data/data/com.termux/files/usr/bin/bash
# Run using: bash mobile/install-termux.sh, from the reviewed source archive.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
DEVELOPMENT=0
[[ ${1:-} == --development ]] && DEVELOPMENT=1
if [[ $# -gt 1 || ( $# -eq 1 && $DEVELOPMENT -ne 1 ) ]]; then
  echo 'Uso: bash mobile/install-termux.sh [--development]' >&2; exit 2
fi
: "${PREFIX:?Execute este instalador no Termux, fora do Debian.}"
[[ -x $PREFIX/bin/pkg && $PREFIX == /data/*/com.termux/files/usr ]] || {
  echo 'Termux oficial necessário; execute fora de PRoot.' >&2; exit 1;
}
[[ $(id -u) -ne 0 ]] || { echo 'Não execute como root Android.' >&2; exit 1; }
case $(uname -m) in aarch64|x86_64) ;; *) echo 'Esta versão suporta aarch64 (ARM64) e x86_64; ARM de 32 bits ainda não validado.' >&2; exit 1;; esac
HOME_REAL=$(cd "$HOME" && pwd -P)
case "$ROOT" in "$HOME_REAL"/*) ;; *) echo 'Extraia o projeto dentro de $HOME no Termux, não em /sdcard.' >&2; exit 1;; esac
# Installation may temporarily hold rootfs, package downloads, and unpacked files.
FREE_KIB=$(df -Pk "$PREFIX" | awk 'END {print $4}')
(( FREE_KIB >= 6 * 1024 * 1024 )) || {
  echo 'São necessários pelo menos 6 GiB livres para instalar. Libere espaço e tente novamente.' >&2; exit 1;
}
if [[ -f $ROOT/SHA256SUMS ]]; then
  (cd "$ROOT" && sha256sum --check --strict SHA256SUMS)
elif (( DEVELOPMENT )); then
  echo 'Modo desenvolvimento: sem manifesto de release; você está executando fontes locais revisadas.'
else
  echo 'SHA256SUMS ausente. Use o arquivo de release íntegro ou --development para fontes locais revisadas.' >&2
  exit 1
fi
printf 'NovaOS Mobile Lite: Debian + XFCE em PRoot. Livre: %s GiB.\n' "$((FREE_KIB / 1024 / 1024))"
printf 'A instalação usa rede e preserva os arquivos existentes do NovaOS.\n'
pkg update
pkg install -y x11-repo
pkg install -y proot-distro pulseaudio termux-x11-nightly xorg-xauth python util-linux
bash "$ROOT/mobile/check-proot.sh"
STATE="$HOME/.local/state/novaos-mobile"
mkdir -p "$STATE"
chmod 700 "$STATE"
exec 9> "$STATE/install.lock"
flock -n 9 || { echo 'Outra instalação NovaOS está em execução.' >&2; exit 1; }
if command -v novaos-mobile >/dev/null && novaos-mobile status --quiet; then
  echo 'Encerre a sessão primeiro: novaos-mobile stop' >&2; exit 1
fi
CONTAINER=$(python "$ROOT/mobile/select-container.py" "$STATE/installed.json")
printf 'Ambiente selecionado para NovaOS Mobile Lite: %s\n' "$CONTAINER"
if ! proot-distro login "$CONTAINER" -- /usr/bin/test -f /etc/novaos-mobile-owner 2>/dev/null; then
  IMAGE=$(grep -v '^#' "$ROOT/mobile/debian-image.txt" | tr -d '\n')
  proot-distro install --name "$CONTAINER" "$IMAGE"
  proot-distro login "$CONTAINER" -- /usr/bin/touch /etc/novaos-mobile-owner
fi
# Paths are passed as argv to PRoot; no remote script is evaluated.
proot-distro login "$CONTAINER" --bind "$ROOT:/opt/novaos-source" -- /bin/bash /opt/novaos-source/mobile/configure-guest.sh
install -d "$HOME/.local/lib/novaos-mobile" "$PREFIX/bin" "$HOME/.shortcuts"
install -m 644 "$ROOT/mobile/novaos_mobile.py" "$HOME/.local/lib/novaos-mobile/novaos_mobile.py"
# printf %q protects spaces in Termux's private home path.
printf '#!%s/bin/bash\nexec %q %q "$@"\n' "$PREFIX" "$PREFIX/bin/python" "$HOME/.local/lib/novaos-mobile/novaos_mobile.py" > "$PREFIX/bin/novaos-mobile"
chmod 755 "$PREFIX/bin/novaos-mobile"
printf '#!%s/bin/bash\nexec novaos-mobile start\n' "$PREFIX" > "$HOME/.shortcuts/NovaOS"
chmod 700 "$HOME/.shortcuts/NovaOS"
printf '{"edition":"mobile-lite","version":"0.1.0-alpha","container":"%s"}\n' "$CONTAINER" > "$STATE/installed.json"
chmod 600 "$STATE/installed.json"
printf '\nInstalação concluída. Instale também o APK oficial Termux:X11 e execute:\n  novaos-mobile start\n  novaos-mobile stop\nGuia: docs/MOBILE.md. APK NovaOS próprio não é necessário.\n'
