#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd -P)"
SOURCE="$HOME/.local/share/novaos/source-git"
REMOTE="https://github.com/Hhhaofuqoc/novaos.git"
say(){ printf '[NovaOS update] %s\n' "$*"; }
if [[ -d "$ROOT/.git" ]]; then
  SOURCE="$ROOT"
elif [[ -d "$HOME/novaos-src/.git" ]]; then
  SOURCE="$HOME/novaos-src"
elif [[ -d "$HOME/novaos-git/.git" ]]; then
  SOURCE="$HOME/novaos-git"
elif [[ ! -d "$SOURCE/.git" ]]; then
  if [[ -e "$SOURCE" ]]; then
    say "O caminho $SOURCE ja existe e nao e Git. Nenhum arquivo foi apagado."
    exit 1
  fi
  if ! command -v git >/dev/null 2>&1; then pkg install -y git; fi
  say 'Baixando codigo oficial da NovaOS do GitHub.'
  git clone --filter=blob:none "$REMOTE" "$SOURCE"
fi
say "Atualizando $SOURCE ..."
git -C "$SOURCE" pull --ff-only
say 'Reaplicando somente os arquivos e dependencias gerenciados pela NovaOS.'
exec bash "$SOURCE/install.sh"
