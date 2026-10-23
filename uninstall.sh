#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
ROOT="$HOME/.local/share/novaos/app"
echo 'Desinstalará SOMENTE arquivos gerenciados pela NovaOS.'
echo 'Contêiner novaos e configurações pessoais serão PRESERVADOS.'
read -r -p 'Digite DESINSTALAR para continuar: ' ans
[[ "$ans" == 'DESINSTALAR' ]] || exit 1
if command -v novaos >/dev/null 2>&1; then novaos stop || true; fi
if proot-distro list -q 2>/dev/null | grep -Fxq novaos; then
  proot-distro login novaos -- /bin/bash -c 'if [ -f /opt/novaos/app/.novaos-owned ]; then rm -rf /opt/novaos/app; fi; rm -f /usr/local/bin/nova-info /usr/local/bin/nova-settings'
fi
rm -f "$PREFIX/bin/novaos"
if [[ -f "$ROOT/.novaos-owned" || -f "$ROOT/install.sh" ]]; then rm -rf "$ROOT"; fi
echo 'Código removido, dados e contêiner preservados.'
