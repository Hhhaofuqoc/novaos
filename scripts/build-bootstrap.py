#!/usr/bin/env python3
"""Generate the external downloader after the bundle, avoiding checksum cycles."""
import argparse
import hashlib
from pathlib import Path
import re
import shlex
from urllib.parse import urlsplit


def render(bundle, base_url, version, output):
    url = urlsplit(base_url)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.query or url.fragment or any(c.isspace() for c in base_url)):
        raise ValueError('The download base URL must be HTTPS, without credentials, whitespace, query or fragment')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:[.+~][a-zA-Z0-9.]+)?', version):
        raise ValueError('Invalid version')
    template = Path(__file__).resolve().parents[1]/'mobile/bootstrap-termux.sh.in'
    text = template.read_text()
    with Path(bundle).open('rb') as stream:
        archive_digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    for token, value in {'VERSION': version,
                         'ARCHIVE_URL': base_url.rstrip('/')+f'/novaos-{version}-mobile.tar.gz',
                         'ARCHIVE_SHA256': archive_digest}.items():
        text = text.replace(f'@@{token}@@', shlex.quote(value))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text)
    output.chmod(0o755)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    Path(str(output)+'.sha256').write_text(f'{digest}  {output.name}\n')
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--version', default='0.1.0')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        digest = render(args.bundle, args.base_url, args.version, args.output)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f'Generated {args.output.name}: {digest}')


if __name__ == '__main__':
    main()
