#!/usr/bin/env bash
# Temporary authenticated noVNC access to NovaOS Full on an ephemeral GitHub runner.
set -Eeuo pipefail
MINUTES="${1:-60}"
case "$MINUTES" in 30|60|90) ;; *) echo 'Invalid session duration.' >&2; exit 2;; esac
: "${NOVAOS_REMOTE_PASSWORD:?Create repository secret NOVAOS_REMOTE_PASSWORD (16+ characters).}"
if (( ${#NOVAOS_REMOTE_PASSWORD} < 16 )); then
  echo 'NOVAOS_REMOTE_PASSWORD must have at least 16 characters.' >&2
  exit 2
fi
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
ISO="$ROOT/dist/NovaOS-v1.0-Full-amd64.iso"
[[ -s "$ISO" ]] || { echo 'ISO missing. Wait for successful ISO workflow.' >&2; exit 1; }
WORK="${RUNNER_TEMP:-/tmp}/novaos-remote"
mkdir -p "$WORK"
chmod 700 "$WORK"
QEMU_PID='' WS_PID='' TUNNEL_PID=''
cleanup() {
  trap - EXIT INT TERM
  echo '[NovaOS Remote] Shutting down this temporary VM and tunnel.'
  for pid in "$TUNNEL_PID" "$WS_PID" "$QEMU_PID"; do
    if [[ "$pid" =~ ^[0-9]+$ ]]; then kill -TERM "$pid" 2>/dev/null || true; fi
  done
  for pid in "$TUNNEL_PID" "$WS_PID" "$QEMU_PID"; do
    if [[ "$pid" =~ ^[0-9]+$ ]]; then wait "$pid" 2>/dev/null || true; fi
  done
}
trap cleanup EXIT INT TERM
for cmd in qemu-system-x86_64 websockify cloudflared nginx curl; do
  command -v "$cmd" >/dev/null || { echo "Missing dependency: $cmd" >&2; exit 1; }
done
[[ -f /usr/share/novnc/vnc.html ]] || { echo 'noVNC assets missing.' >&2; exit 1; }
QEMU_ACCEL=(-machine q35,accel=tcg -cpu max)
if [[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]; then
  QEMU_ACCEL=(-machine q35,accel=kvm -cpu host)
  echo '[NovaOS Remote] Using KVM acceleration.'
else
  echo '[NovaOS Remote] KVM unavailable; software emulation may be slow.'
fi
qemu-system-x86_64 "${QEMU_ACCEL[@]}" \
  -name NovaOS-Full -smp 2 -m 3072 \
  -boot order=d -cdrom "$ISO" -no-reboot \
  -vga std -display none -vnc 127.0.0.1:6 \
  -nic user,model=virtio-net-pci \
  -serial "file:$WORK/qemu-serial.log" \
  >"$WORK/qemu.log" 2>&1 &
QEMU_PID=$!
sleep 3
kill -0 "$QEMU_PID" 2>/dev/null || { echo 'QEMU exited:' >&2; tail -n 50 "$WORK/qemu.log" >&2; exit 1; }

# noVNC and VNC are not exposed on public network interfaces.
websockify --web /usr/share/novnc 127.0.0.1:6080 127.0.0.1:5906 \
  >"$WORK/websockify.log" 2>&1 &
WS_PID=$!
sleep 2
kill -0 "$WS_PID" 2>/dev/null || { echo 'websockify exited:' >&2; tail -n 40 "$WORK/websockify.log" >&2; exit 1; }

# The HTTPS tunnel can only access the local nginx Basic Auth gateway.
# Never print or write the user-selected password into workflow logs.
printf '%s\n' "$NOVAOS_REMOTE_PASSWORD" | sudo htpasswd -i -B -c /etc/nginx/.novaos-remote.htpasswd nova >/dev/null
sudo chown root:www-data /etc/nginx/.novaos-remote.htpasswd
sudo chmod 0640 /etc/nginx/.novaos-remote.htpasswd
sudo tee /etc/nginx/conf.d/novaos-remote.conf >/dev/null <<'NGINX'
server {
    listen 127.0.0.1:8787;
    server_name localhost;
    auth_basic "NovaOS Full remote desktop";
    auth_basic_user_file /etc/nginx/.novaos-remote.htpasswd;
    access_log off;
    location / {
        proxy_pass http://127.0.0.1:6080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_buffering off;
    }
}
NGINX
sudo nginx -t
sudo systemctl restart nginx
STATUS="$(curl --silent --output /dev/null --write-out '%{http_code}' http://127.0.0.1:8787/vnc.html)"
[[ "$STATUS" == 401 ]] || { echo "Auth gateway failure: HTTP $STATUS, expected HTTP 401. Tunnel will not start." >&2; exit 1; }

cloudflared tunnel --url http://127.0.0.1:8787 >"$WORK/tunnel.log" 2>&1 &
TUNNEL_PID=$!
URL=''
for _ in $(seq 1 40); do
  URL="$(grep -Eo 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$WORK/tunnel.log" 2>/dev/null | head -n 1 || true)"
  [[ -n "$URL" ]] && break
  kill -0 "$TUNNEL_PID" 2>/dev/null || break
  sleep 2
done
if [[ -z "$URL" ]]; then
  echo 'Cloudflare tunnel failed.' >&2
  tail -n 45 "$WORK/tunnel.log" >&2
  exit 1
fi
PAGE="$URL/vnc.html?autoconnect=true&resize=scale&path=websockify"
echo '====== NOVAOS FULL REMOTE DESKTOP ======'
echo "URL: $PAGE"
echo 'Username: nova'
echo 'Password: the NOVAOS_REMOTE_PASSWORD repository secret you set'
echo "Session length: $MINUTES minutes (ends earlier if the job is cancelled)"
echo '======================================='
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo '## NovaOS Full — acesso remoto'
    echo ''
    echo "**[Abrir NovaOS no navegador]($PAGE)**"
    echo ''
    echo 'Usuário: nova; senha: o segredo NOVAOS_REMOTE_PASSWORD (não aparece nos logs).'
    echo ''
    echo "Sessão temporária de $MINUTES minutos; ao finalizar, a VM é descartada."
    echo 'Autenticação Nginx é obrigatória antes do noVNC e do WebSocket.'
  } >> "$GITHUB_STEP_SUMMARY"
fi

SECONDS_LEFT=$((MINUTES * 60))
while (( SECONDS_LEFT > 0 )); do
  sleep 10
  SECONDS_LEFT=$((SECONDS_LEFT - 10))
  if ! kill -0 "$QEMU_PID" 2>/dev/null; then
    echo '[NovaOS Remote] QEMU exited unexpectedly:' >&2
    tail -n 60 "$WORK/qemu.log" >&2
    exit 1
  fi
  if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
    echo '[NovaOS Remote] Tunnel exited unexpectedly:' >&2
    tail -n 45 "$WORK/tunnel.log" >&2
    exit 1
  fi
done
echo '[NovaOS Remote] Session complete.'
