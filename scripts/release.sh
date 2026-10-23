#!/usr/bin/env bash
# Produce reviewable local artifacts; this script does not publish to any service.
set -euo pipefail
if (($#)); then
    if [[ $# == 1 && ( $1 == --help || $1 == -h ) ]]; then
        printf 'Usage: %s (no positional arguments)\nSet NOVAOS_VERSION / NOVAOS_DIST_DIR to configure the local build.\n' "$0"
        exit 0
    fi
    echo 'Unexpected argument. Use --help.' >&2
    exit 2
fi
repo=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
version=${NOVAOS_VERSION:-0.1.0}
out=${NOVAOS_DIST_DIR:-$repo/dist}
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+([.+~][a-zA-Z0-9.]+)?$ ]] || { echo 'Invalid version.' >&2; exit 2; }
mkdir -p -- "$out"
out=$(CDPATH='' cd -- "$out" && pwd)
[[ $out != "$repo" ]] || { echo 'Output must not be the source root.' >&2; exit 2; }
export NOVAOS_DIST_DIR=$out
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-0}
# The source manifest is embedded in both source and Mobile bundles.
python3 - "$repo" "$out" <<'PYMANIFEST'
import hashlib, pathlib, sys
root, out = map(pathlib.Path, sys.argv[1:])
excluded = {'.git', 'dist', 'build', '.venv', 'test-results', '.pytest_cache', '.mypy_cache', '.cache', '__pycache__'}
lines = []
for path in sorted(root.rglob('*')):
    if not path.is_file() or path.is_symlink() or path == root / 'SHA256SUMS':
        continue
    relative = path.relative_to(root)
    if any(part in excluded for part in relative.parts) or path.suffix in ('.pyc', '.pyo'):
        continue
    if path.is_relative_to(out):
        continue
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    lines.append(f'{digest}  {relative.as_posix()}\n')
(root / 'SHA256SUMS').write_text(''.join(lines))
print(f'Checksummed {len(lines)} source files')
PYMANIFEST
bash "$repo/scripts/build-deb.sh"
# Stable ordering/timestamps make identical input trees produce identical archives.
exclude_out=()
case "$out/" in
    "$repo/"*) exclude_out=(--exclude="./${out#"$repo/"}") ;;
esac
tar_args=(--sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner --mode='u+rwX,go+rX,go-w' --format=gnu)
tar "${tar_args[@]}" "${exclude_out[@]}" --exclude='./.git' --exclude='./dist' --exclude='./build' \
    --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='./.venv' --exclude='./test-results' --exclude='.pytest_cache' --exclude='.mypy_cache' --exclude='.cache' --exclude='*.pyo' \
    --transform="s,^\.,novaos-$version," -C "$repo" -cf - . | gzip -n > "$out/novaos-${version}-source.tar.gz"
tar "${tar_args[@]}" --exclude=__pycache__ --exclude='*.pyc' -C "$repo" -cf - themes wallpapers | gzip -n > "$out/novaos-${version}-themes.tar.gz"
# The Mobile bundle includes the complete verified source needed by install-termux.sh.
cp -- "$out/novaos-${version}-source.tar.gz" "$out/novaos-${version}-mobile.tar.gz"
if [[ -f $repo/music/generated/manifest.json ]]; then
    tar "${tar_args[@]}" -C "$repo" -cf - music/generated music/LICENSE music/cover.svg | gzip -n > "$out/novaos-${version}-music.tar.gz"
fi
download_base=${NOVAOS_DOWNLOAD_BASE_URL:-https://raw.githubusercontent.com/Hhhaofuqoc/novaos/mobile-lite-downloads-v${version}-fix2}
python3 "$repo/scripts/build-bootstrap.py" --bundle "$out/novaos-${version}-mobile.tar.gz" \
    --base-url "$download_base" --version "$version" --output "$out/install-novaos.sh"
python3 - "$out" "$version" <<'PY'
import hashlib, json, pathlib, sys
out, version = pathlib.Path(sys.argv[1]), sys.argv[2]
# Only this version's artifacts; stale outputs must not silently enter a release.
files = sorted(p for p in out.iterdir() if p.is_file() and not p.name.endswith('.sha256') and (p.name.startswith(f'novaos-{version}-') or p.name.endswith(f'_{version}_all.deb') or p.name == 'install-novaos.sh'))
entries = []
for path in files:
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    entries.append({'name': path.name, 'bytes': path.stat().st_size, 'sha256': digest})
    if path.name.endswith('.tar.gz'):
        (out / (path.name + '.sha256')).write_text(f'{digest}  {path.name}\n')
manifest = {'project': 'NovaOS', 'version': version, 'status': 'alpha', 'artifacts': entries,
            'validation': 'See docs/VALIDATION.md; artifact creation does not establish Android or ISO boot validation.'}
(out / 'release-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
entries.append({'name': 'release-manifest.json', 'sha256': hashlib.sha256((out / 'release-manifest.json').read_bytes()).hexdigest()})
(out / 'SHA256SUMS').write_text(''.join(f"{e['sha256']}  {e['name']}\n" for e in entries))
print(f'Created {len(entries)-1} local artifacts in {out}')
PY
