#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
APPDIR="$HOME/.local/share/novaos/app"
STATE="$HOME/.local/state/novaos"
RUN="$STATE/run"
LOG="$STATE/logs"
mkdir -p "$RUN" "$LOG" "$HOME/.config/novaos"
DISPLAY_NUM="${NOVAOS_DISPLAY:-:1}"
PROFILE_FILE="$HOME/.config/novaos/profile"
[[ -f "$PROFILE_FILE" ]] || printf 'full\n' > "$PROFILE_FILE"
log(){ printf '[NovaOS] %s\n' "$*"; }
error(){ log "ERRO: $*" >&2; exit 1; }
# PID + /proc start_ticks protege contra reutilização de PID.
pid_ticks(){ awk '{print $22}' "/proc/$1/stat" 2>/dev/null || true; }
record(){ local t; t="$(pid_ticks "$2")"; [[ -n "$t" ]] && printf '%s %s\n' "$2" "$t" > "$RUN/$1.pid"; }
valid(){ local id tick; [[ -f "$RUN/$1.pid" ]] || return 1; read -r id tick < "$RUN/$1.pid"; [[ "$id" =~ ^[0-9]+$ && -n "$tick" && "$(pid_ticks "$id")" == "$tick" ]]; }
stop_pid(){ if valid "$1"; then local id tick; read -r id tick < "$RUN/$1.pid"; kill -TERM "$id" 2>/dev/null || true; fi; rm -f "$RUN/$1.pid"; }
check(){
  log "Termux $(uname -m); DISPLAY=$DISPLAY_NUM; livre: $(df -h "$HOME" | awk 'END {print $4}')"
  command -v proot-distro >/dev/null && log 'proot-distro: presente' || log 'proot-distro: AUSENTE'
  command -v termux-x11 >/dev/null && log 'comando termux-x11: presente' || log 'comando termux-x11: AUSENTE'
  if [[ -S "$PREFIX/tmp/.X11-unix/X${DISPLAY_NUM#:}" ]]; then log 'Socket X11: presente (NÃO confirma que esteja responsivo)'; else log 'Socket X11: ausente'; fi
  if command -v pm >/dev/null; then pm path com.termux.x11 2>/dev/null | head -1 | sed 's/^/[NovaOS] APK: /' || true; fi
  valid guest && log 'Sessão NovaOS registrada: ativa' || log 'Sessão NovaOS: não registrada'
}
start(){
  command -v proot-distro >/dev/null || error 'Instale o projeto primeiro com bash install.sh.'
  command -v termux-x11 >/dev/null || error 'Falta o pacote termux-x11-nightly.'
  [[ -d "$APPDIR/nova-shell" ]] || error 'Arquivos da NovaShell não encontrados.'
  if valid guest; then log 'NovaOS já está ativa. Use novaos restart para reiniciar.'; return; fi
  rm -f "$RUN/guest.pid"
  local xnum="${DISPLAY_NUM#:}" socket="$PREFIX/tmp/.X11-unix/X${DISPLAY_NUM#:}"
  if [[ ! -S "$socket" ]]; then
    # Sem excluir locks/sockets antigos: o usuário pode diagnosticar sua sessão.
    if [[ -e "$PREFIX/tmp/.X${xnum}-lock" ]]; then
      error "Há lock X${xnum} sem socket. Não removi nada. Consulte 'novaos repair' e escolha outro NOVAOS_DISPLAY se necessário."
    fi
    local flags=()
    case "${NOVAOS_X11_FLAGS:-}" in
      '') ;;
      '-legacy-drawing'|'-force-bgra') flags=("$NOVAOS_X11_FLAGS");;
      '-legacy-drawing -force-bgra'|'-force-bgra -legacy-drawing') flags=(-legacy-drawing -force-bgra);;
      *) error 'NOVAOS_X11_FLAGS aceita somente -legacy-drawing e/ou -force-bgra.';;
    esac
    log "Iniciando Termux:X11 em $DISPLAY_NUM"
    termux-x11 "$DISPLAY_NUM" "${flags[@]}" >"$LOG/x11.log" 2>&1 & record x11 "$!"
    for _ in $(seq 1 24); do [[ -S "$socket" ]] && break; sleep 0.25; done
    [[ -S "$socket" ]] || error "X11 não abriu. Verifique $LOG/x11.log e o APK Termux:X11."
  else
    log 'Servidor X11 existente detectado; será reutilizado e não será encerrado pelo NovaOS.'
  fi
  if command -v am >/dev/null; then am start --user 0 -n com.termux.x11/com.termux.x11.MainActivity >/dev/null 2>&1 || true; fi
  if command -v pulseaudio >/dev/null; then
    pulseaudio --start --exit-idle-time=-1 >/dev/null 2>&1 || log 'PulseAudio não iniciou; a imagem continua utilizável sem áudio.'
    if command -v pactl >/dev/null && pactl info >/dev/null 2>&1; then
      # Restrito a loopback; carregamento idempotente quando já ativo.
      pactl list short modules 2>/dev/null | grep -q 'module-native-protocol-tcp' || \
        pactl load-module module-native-protocol-tcp listen=127.0.0.1 auth-ip-acl=127.0.0.1 >/dev/null 2>&1 || true
    fi
  fi
  if command -v python >/dev/null; then
    python "$APPDIR/scripts/host-metrics.py" "$PREFIX/tmp/novaos-metrics.json" >"$LOG/metrics.log" 2>&1 & record metrics "$!"
  fi
  local profile; profile="$(cat "$PROFILE_FILE")"; [[ "$profile" == lite || "$profile" == full ]] || profile=full
  log "Abrindo NovaShell ($profile)..."
  # Apenas essa sessão é controlada por nosso PID; outras sessões do PRoot são preservadas.
  proot-distro login novaos --shared-tmp --user nova -- \
    env DISPLAY="$DISPLAY_NUM" PULSE_SERVER=127.0.0.1 NOVAOS_PROFILE="$profile" \
    NOVAOS_METRICS=/tmp/novaos-metrics.json /bin/bash /opt/novaos/app/scripts/guest-session.sh \
    >"$LOG/session.log" 2>&1 & record guest "$!"
  sleep 1
  if ! valid guest; then
    log "A sessão terminou prematuramente. Log: $LOG/session.log"
    tail -n 25 "$LOG/session.log" || true
    error 'Falha ao abrir o desktop.'
  fi
  log 'Sessão enviada ao Termux:X11. Confira o APK Termux:X11.'
}
stop(){
  log 'Encerrando somente processos registrados desta sessão NovaOS.'
  stop_pid guest
  stop_pid metrics
  # O servidor X11 pode ser compartilhado após sua criação; mantê-lo preserva outras janelas.
  log 'Desktop encerrado. Termux:X11 mantido (pode estar sendo compartilhado).'
}
repair(){
  check
  log 'Executando verificação/reinstalação de dependências da NovaOS...'
  [[ -d "$APPDIR/scripts" ]] || error 'Projeto ausente. Execute install.sh do ZIP.'
  proot-distro login novaos --shared-tmp --bind "$APPDIR:/mnt/novaos-source" -- \
    /bin/bash /mnt/novaos-source/scripts/setup-guest.sh
  log 'Verificação de pacotes concluída. Diagnóstico X11:'
  proot-distro login novaos --shared-tmp --user nova -- env DISPLAY="$DISPLAY_NUM" \
    /bin/bash /opt/novaos/app/scripts/guest-diag.sh || true
}
case "${1:-start}" in
  start) start;;
  stop) stop;;
  restart) stop; sleep 1; start;;
  lite|full) printf '%s\n' "$1" > "$PROFILE_FILE"; log "Perfil $1 salvo."; if valid guest; then stop; sleep 1; start; fi;;
  repair) repair;;
  update) bash "$APPDIR/update.sh";;
  status) check;;
  logs)
    echo '=== Termux: sessão NovaOS ==='
    tail -n 70 "$LOG/session.log" 2>/dev/null || echo 'Sem log de sessão no Termux.'
    echo '=== Linux PRoot: NovaShell / Openbox / wallpaper ==='
    proot-distro login novaos --shared-tmp --user nova -- /bin/bash -c '
      d="$HOME/.local/state/novaos/logs"
      for name in novashell openbox wallpaper; do
        echo "--- $name.log ---"
        if [[ -f "$d/$name.log" ]]; then tail -n 80 "$d/$name.log"; else echo "(arquivo ainda inexistente)"; fi
      done
    ' || true
    ;;
  help|-h|--help) printf 'NovaOS: novaos [start|stop|restart|lite|full|repair|update|status|logs]\n';;
  *) error "Comando desconhecido: $1";;
esac
