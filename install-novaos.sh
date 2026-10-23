#!/usr/bin/env bash
# Generated from reviewed sources. The release bundle hash is pinned at build time.
set -euo pipefail
umask 077
version=0.1.0
archive_url=https://raw.githubusercontent.com/Hhhaofuqoc/novaos/mobile-lite-downloads-v0.1.0-fix2/novaos-0.1.0-mobile.tar.gz
archive_sha256=16f07a1312c551a9c07600a28b36b2026fd0da047842b5533de732b4b777687e
download_only=false
case ${1:-} in
  --download-only) download_only=true ;;
  '') ;;
  *) echo 'Uso: bash install-novaos.sh [--download-only]' >&2; exit 2 ;;
esac
(( $# <= 1 )) || { echo 'Argumentos inesperados.' >&2; exit 2; }
if [[ $download_only == false ]]; then
  [[ -n ${PREFIX:-} && -x $PREFIX/bin/pkg ]] || {
    echo 'Execute no Termux. Use --download-only para somente baixar os fontes em outro Linux.' >&2
    exit 1
  }
fi
for program in curl sha256sum tar mktemp; do
  command -v "$program" >/dev/null || { echo "Comando necessário: $program" >&2; exit 1; }
done
cache_root="$HOME/.cache"
mkdir -p -- "$cache_root"
download_dir=$(mktemp -d "$cache_root/novaos-download.XXXXXXXX")
source_dir=''
keep_sources=false
cleanup() {
  rm -rf -- "$download_dir"
  if [[ -n $source_dir && $keep_sources == false ]]; then rm -rf -- "$source_dir"; fi
}
trap cleanup EXIT
bundle="$download_dir/novaos-mobile.tar.gz"
printf 'Baixando NovaOS Mobile Lite %s…\n' "$version"
curl --fail --show-error --location --proto '=https' --proto-redir '=https' \
  --tlsv1.2 --retry 3 --connect-timeout 30 --output "$bundle" "$archive_url"
printf '%s  %s\n' "$archive_sha256" "$bundle" | sha256sum --check --strict -
# Only extract after the exact release bundle has passed SHA-256 validation.
source_dir=$(mktemp -d "$HOME/novaos-$version.XXXXXXXX")
tar --no-same-owner --no-same-permissions -xzf "$bundle" -C "$source_dir"
project="$source_dir/novaos-$version"
[[ -f $project/SHA256SUMS && -f $project/mobile/install-termux.sh ]] || {
  echo 'Pacote incompleto; a instalação não foi executada.' >&2; exit 1;
}
(cd "$project" && sha256sum --check --strict SHA256SUMS)
keep_sources=true
printf '\nFontes verificadas: %s\n' "$project"
if [[ $download_only == true ]]; then exit 0; fi
bash "$project/mobile/install-termux.sh"
printf '\nPara abrir, instale o APK oficial Termux:X11 e execute: novaos-mobile start\n'
