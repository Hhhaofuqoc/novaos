#!/bin/bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
find "$ROOT" -type f \( -name '*.sh' -o -name 'nova-info' -o -name 'nova-settings' \) -print0 | while IFS= read -r -d '' file; do bash -n "$file"; done
python3 -m compileall -q "$ROOT/nova-shell" "$ROOT/scripts/host-metrics.py"
python3 "$ROOT/scripts/generate-icons.py"
python3 -m unittest discover -s "$ROOT/tests" -v
printf 'Testes estáticos finalizados. Não equivalem a execução em Android.\n'
