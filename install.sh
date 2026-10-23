#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
APPDIR="$HOME/.local/share/novaos/app"
LOGDIR="$HOME/.local/state/novaos/logs"
mkdir -p "$LOGDIR"
exec > >(tee -a "$LOGDIR/install.log") 2>&1
say(){ printf '\033[1;35m[NovaOS]\033[0m %s\n' "$*"; }
fail(){ say "ERRO: $*"; exit 1; }
trap 'say "Instalação interrompida na linha $LINENO. Consulte $LOGDIR/install.log"' ERR
[[ -n "${PREFIX:-}" && -d "$PREFIX" && "$PREFIX" == *com.termux/files/usr* ]] || fail 'Execute no Termux original, não dentro do PRoot.'
[[ "$(uname -m)" == aarch64 ]] || fail "Requer aarch64, encontrado $(uname -m)."
free_kb="$(df -Pk "$HOME" | awk 'END {print $4}')"
[[ "$free_kb" =~ ^[0-9]+$ ]] || fail 'Não foi possível medir o armazenamento livre.'
if ((free_kb < 9 * 1024 * 1024)); then fail 'Menos de 9 GiB livres: instalação recusada (previsão de até 5 GiB + reserva de 4 GiB).'; fi
say "Livre: $((free_kb / 1024)) MiB. Previsão típica: 2–5 GiB; limite não garantido."
command -v pkg >/dev/null || fail 'Gerenciador pkg não encontrado.'
say 'Instalando dependências do Termux, sem remover pacotes existentes...'
pkg install -y proot-distro python pulseaudio >/dev/null
if ! command -v termux-x11 >/dev/null 2>&1; then
  pkg install -y x11-repo >/dev/null
  pkg install -y termux-x11-nightly >/dev/null
fi
if ! (command -v termux-x11 >/dev/null && command -v proot-distro >/dev/null); then fail 'Termux:X11 ou PRoot indisponível.'; fi
if command -v pm >/dev/null && ! pm path com.termux.x11 2>/dev/null | grep -q package:; then
  say 'AVISO: APK Termux:X11 não detectado. Instale o aplicativo oficial, além do pacote Termux.'
fi
mkdir -p "$APPDIR"
if [[ "$ROOT" != "$APPDIR" ]]; then
  say 'Copiando projeto local para a instalação gerenciada (sem modificar o diretório original).'
  cp -a "$ROOT/." "$APPDIR/"
fi
if proot-distro list --quiet 2>/dev/null | grep -Fxq novaos; then
  say 'Contêiner novaos existente detectado: será preservado.'
elif proot-distro list 2>/dev/null | grep -Eq '^[[:space:]]*\*[[:space:]]+novaos([[:space:]]|$)'; then
  say 'Contêiner novaos existente (formato antigo): preservado.'
else
  say 'Criando um novo contêiner Debian ARM64 com o nome novaos.'
  if proot-distro install --help 2>&1 | grep -q -- '--name'; then
    proot-distro install --name novaos debian
  elif proot-distro install --help 2>&1 | grep -q -- '--override-alias'; then
    proot-distro install --override-alias novaos debian
  else
    fail 'Versão incompatível do PRoot-Distro: instale/atualize a versão oficial antes de criar o contêiner.'
  fi
fi
say 'Verificando sistema existente e aplicando somente a configuração da NovaOS...'
proot-distro login novaos --shared-tmp --bind "$APPDIR:/mnt/novaos-source" -- /bin/bash /mnt/novaos-source/scripts/setup-guest.sh
say 'Criando o comando novaos no Termux.'
cat > "$PREFIX/bin/novaos" <<'WRAPPER'
#!/data/data/com.termux/files/usr/bin/bash
exec bash "$HOME/.local/share/novaos/app/scripts/host-control.sh" "$@"
WRAPPER
chmod 755 "$PREFIX/bin/novaos"
remaining_kb="$(df -Pk "$HOME" | awk 'END {print $4}')"
if ((remaining_kb < 4 * 1024 * 1024)); then
  say 'ALERTA: restaram menos de 4 GiB. Evite instalar módulos adicionais; nenhuma limpeza de dados foi feita.'
fi
say 'Arquivos instalados. Para iniciar: novaos'
say 'Caso apareça tela preta: novaos repair; depois teste NOVAOS_X11_FLAGS=-legacy-drawing novaos'
