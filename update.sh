#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd -P)"
if [[ -d "$ROOT/.git" ]]; then
  echo '[NovaOS] Origem Git local detectada. Buscando apenas atualização fast-forward.'
  git -C "$ROOT" pull --ff-only || { echo 'Não foi possível atualizar via Git; código local preservado.'; exit 1; }
else
  echo '[NovaOS] Pacote ZIP/local: reaplicando esta versão. Para código novo, extraia um ZIP mais recente e execute install.sh.'
fi
exec bash "$ROOT/install.sh"
