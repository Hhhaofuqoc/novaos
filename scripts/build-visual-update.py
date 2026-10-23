#!/usr/bin/env python3
"""Build a small checksummed update for installed NovaOS Mobile environments."""
import argparse
import gzip
import hashlib
import io
from pathlib import Path
import shlex
import tarfile

ROOT=Path(__file__).resolve().parents[1]
FILES=['applications/novafetch','applications/novaos/__main__.py','applications/novaos/system.py',
       'themes/fetch/compact.jsonc','themes/fetch/wide.jsonc','themes/plasma/NovaOS.colors',
       'themes/plasma/NovaOS.profile','themes/plasma/NovaOS.colorscheme',
       'themes/apply-plasma.sh','themes/icons/NovaOS/index.theme',
       'installers/install-visual-update.sh','mobile/novaos_mobile.py',
       'mobile/guest-session.sh','mobile/packages-plasma.txt']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    parser.add_argument('--base-url',default='https://raw.githubusercontent.com/Hhhaofuqoc/novaos/novaos-visual-v1')
    args=parser.parse_args()
    if not args.base_url.startswith('https://') or any(c.isspace() for c in args.base_url):
        parser.error('HTTPS base URL required')
    args.output.mkdir(parents=True,exist_ok=True)
    archive=args.output/'novaos-visual-update.tar.gz'
    contents={name:(ROOT/name).read_bytes() for name in FILES}
    contents['SHA256SUMS']=''.join(f'{hashlib.sha256(body).hexdigest()}  {name}\n' for name,body in contents.items()).encode()
    with archive.open('wb') as output, gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0) as compressed:
        with tarfile.open(fileobj=compressed,mode='w') as tar:
            for name,body in sorted(contents.items()):
                item=tarfile.TarInfo('novaos-visual-update/'+name)
                item.size=len(body)
                item.mode=0o644
                tar.addfile(item,io.BytesIO(body))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    Path(str(archive)+'.sha256').write_text(f'{digest}  {archive.name}\n')
    script=(ROOT/'mobile/visual-update.sh.in').read_text()
    script=script.replace('@@ARCHIVE_URL@@',shlex.quote(args.base_url.rstrip('/')+'/'+archive.name))
    script=script.replace('@@ARCHIVE_SHA256@@',shlex.quote(digest))
    bootstrap=args.output/'install-novaos-visual.sh'
    bootstrap.write_text(script)
    bootstrap.chmod(0o755)
    Path(str(bootstrap)+'.sha256').write_text(f'{hashlib.sha256(bootstrap.read_bytes()).hexdigest()}  {bootstrap.name}\n')
    print(f'{archive.name}: {archive.stat().st_size} bytes')

if __name__=='__main__': main()
