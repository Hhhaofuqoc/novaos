#!/usr/bin/env bash
# Publicação inicial idempotente da NovaOS pelo GitHub CLI no Termux.
# Nunca usa force push, não sobrescreve históricos remotos e não toca no PRoot.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$ROOT"
say(){ printf '\033[1;35m[NovaOS GitHub]\033[0m %s\n' "$*"; }
fail(){ say "ERRO: $*" >&2; exit 1; }
[[ -f "$ROOT/install.sh" && -f "$ROOT/scripts/guest-session.sh" ]] || fail 'Diretório NovaOS incompleto.'
[[ -n "${PREFIX:-}" && "$PREFIX" == *com.termux/files/usr* ]] || fail 'Execute no Termux original, fora do PRoot.'
if ! command -v gh >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
  say 'Instalando Git e GitHub CLI do repositório oficial Termux...'
  pkg install -y git gh || fail 'Não foi possível instalar git/gh. Confira internet e os repositórios do Termux.'
fi
if ! gh auth status -h github.com >/dev/null 2>&1; then
  say 'Autenticação oficial do GitHub necessária (será aberta uma página ou exibido um código).'
  gh auth login --hostname github.com --git-protocol https --web || fail 'Login do GitHub não concluído.'
fi
gh auth setup-git >/dev/null || fail 'Não foi possível configurar autenticação do Git.'
LOGIN="$(gh api user --jq .login)" || fail 'Não foi possível consultar o usuário GitHub.'
[[ "$LOGIN" == Hhhaofuqoc ]] || fail "GitHub CLI autenticado como '$LOGIN', mas a conta GitHub vinculada a este projeto é 'Hhhaofuqoc'. Entre na conta correta e tente novamente."
REPO="$LOGIN/NovaOS"
TARGET="https://github.com/$REPO.git"
if [[ ! -d .git ]]; then
  say 'Inicializando repositório Git local sem modificar arquivos de sistema.'
  git init -b main
fi
BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || true)"
[[ "$BRANCH" == main ]] || fail "Branch local '$BRANCH' não é main; publicação cancelada para preservar o histórico existente."
if ! git config --get user.name >/dev/null; then git config user.name "$LOGIN"; fi
if ! git config --get user.email >/dev/null; then
  ACCOUNT_ID="$(gh api user --jq .id)"
  git config user.email "${ACCOUNT_ID}+${LOGIN}@users.noreply.github.com"
fi
# Adiciona exclusivamente caminhos conhecidos da distribuição; não publica arquivos aleatórios do usuário.
git add -- .gitignore README.md install.sh update.sh start.sh stop.sh repair.sh uninstall.sh publish-github.sh assets config nova-shell scripts themes tests
if ! git diff --cached --quiet; then
  git commit -m 'NovaOS v1.0: NovaShell, branding e scripts Termux'
fi
if git remote get-url origin >/dev/null 2>&1; then
  remote="$(git remote get-url origin)"
  case "$remote" in
    "$TARGET"|"https://github.com/$REPO"|"git@github.com:$REPO.git") ;;
    *) fail "Remote origin já aponta para outro lugar: $remote. Nada foi alterado.";;
  esac
fi
if gh repo view "$REPO" >/dev/null 2>&1; then
  say "Repositório $REPO já existe: tentando enviar commits sem sobrescrever histórico remoto."
  if ! git remote get-url origin >/dev/null 2>&1; then git remote add origin "$TARGET"; fi
  git push -u origin main || fail 'Push recusado; histórico remoto não foi sobrescrito. Resolva o conflito manualmente.'
else
  say "Criando https://github.com/$REPO (público) e enviando os arquivos..."
  gh repo create "$REPO" --public --description 'NovaOS: desktop Openbox + NovaShell GTK3 para Termux:X11/PRoot no Android' --source "$ROOT" --remote origin --push || fail 'Falha na criação/publicação. Consulte gh auth status e tente novamente.'
fi
say "Publicado: https://github.com/$REPO"
say 'Para ativar atualizações por Git no comando novaos update, execute bash install.sh a partir DESTA pasta após publicar.'
