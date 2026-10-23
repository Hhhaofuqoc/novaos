#!/usr/bin/env bash
# Noninteractive QEMU test: boot ISO, collect serial log and a REAL framebuffer screenshot.
# This tests whether QEMU starts and provides boot evidence; GUI readiness must be
# inspected in the screenshot, it is NOT inferred just from a running PID.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
ISO="$ROOT/dist/NovaOS-v1.0-Full-amd64.iso"
OUT="$ROOT/dist/vm-smoke"
mkdir -p "$OUT"
[[ -s "$ISO" ]] || { echo 'No ISO to test' >&2; exit 1; }
command -v qemu-system-x86_64 >/dev/null || { echo 'QEMU missing' >&2; exit 1; }
command -v socat >/dev/null || { echo 'socat missing' >&2; exit 1; }
SOCK="$OUT/qemu-monitor.sock"
rm -f "$SOCK"
ACCEL=tcg
if [[ -r /dev/kvm && -w /dev/kvm ]]; then ACCEL=kvm; fi
qemu-system-x86_64 \
  -machine q35 -accel "$ACCEL" -cpu max -smp 2 -m 3072 \
  -cdrom "$ISO" -boot d -no-reboot \
  -display none -vnc 127.0.0.1:17 \
  -monitor "unix:$SOCK,server,nowait" \
  -serial "file:$OUT/serial.log" \
  >"$OUT/qemu.log" 2>&1 &
PID=$!
cleanup(){ kill "$PID" 2>/dev/null || true; wait "$PID" 2>/dev/null || true; rm -f "$SOCK"; }
trap cleanup EXIT
for n in $(seq 1 25); do [[ -S "$SOCK" ]] && break; sleep 1; done
[[ -S "$SOCK" ]] || { echo 'QEMU failed to create monitor socket'; cat "$OUT/qemu.log"; exit 1; }
# Software-emulated VMs can take a while to boot. Give the desktop time.
sleep "${NOVAOS_SMOKE_SECONDS:-125}"
kill -0 "$PID" 2>/dev/null || { echo 'QEMU terminated before screenshot' >&2; cat "$OUT/qemu.log"; exit 1; }
printf 'screendump %s\n' "$OUT/screenshot.ppm" | socat - "UNIX-CONNECT:$SOCK" >"$OUT/monitor.log" 2>&1
[[ -s "$OUT/screenshot.ppm" ]] || { echo 'No framebuffer screenshot from QEMU' >&2; exit 1; }
{
  echo 'QEMU boot smoke launched successfully.'
  echo "Virtualization mode: $ACCEL"
  echo 'Evidence: real QEMU framebuffer screenshot.ppm + serial.log.'
  echo 'This smoke test does not, on its own, prove NovaShell reached the desktop.'
} | tee "$OUT/RESULT.txt"
