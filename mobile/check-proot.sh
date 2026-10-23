#!/usr/bin/env bash
# PRoot-Distro 5.10.2 writes its help to stderr, even on success.
set -euo pipefail
if ! proot_help=$(proot-distro install --help 2>&1); then
  printf 'Não foi possível consultar o PRoot-Distro:\n%s\n' "$proot_help" >&2
  exit 1
fi
if [[ $proot_help != *--name* ]]; then
  printf '%s\n' 'Esta instalação precisa da CLI OCI do PRoot-Distro, com a opção --name.' \
    'Atualize o pacote no Termux: pkg upgrade proot-distro' >&2
  exit 1
fi
