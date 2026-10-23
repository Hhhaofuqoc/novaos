#!/usr/bin/env python3
"""Enable native NovaOS branding in common fetch tools without destroying user settings.

Run as root during guest setup. Original configs are backed up on modification.
Does NOT rewrite /etc/os-release and does NOT fake any system metrics.
"""
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

APP = Path(os.environ.get('NOVAOS_BRAND_APP', '/opt/novaos/app'))
FASTFETCH_LOGO = '/opt/novaos/app/assets/logos/nova-fastfetch.txt'
NEOFETCH_LOGO = '/opt/novaos/app/assets/logos/nova-neofetch.txt'
BRAND_START = '# >>> NovaOS branding (managed) >>>'
BRAND_END = '# <<< NovaOS branding (managed) <<<' 


def write(path: Path, value: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding='utf-8') if path.exists() else None
    if old == value:
        return False
    if old is not None:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup = path.with_name(path.name + '.backup-' + stamp)
        ix = 0
        while backup.exists():
            ix += 1
            backup = path.with_name(path.name + '.backup-' + stamp + f'-{ix}')
        shutil.copy2(path, backup)
    temp = path.with_name(path.name + '.novaos-tmp')
    try:
        temp.write_text(value, encoding='utf-8')
        os.chmod(temp, old and (path.stat().st_mode & 0o777) or 0o644)
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()
    return True


def masked_jsonc(source: str):
    """Mask comments, keeping strings and all offsets intact."""
    chars = list(source)
    i = 0
    quoted = False
    while i < len(chars):
        c = chars[i]
        if quoted:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c == '/' and i + 1 < len(chars) and chars[i + 1] in ('/', '*'):
            if chars[i + 1] == '/':
                j = source.find('\n', i)
                j = len(chars) if j < 0 else j
            else:
                j = source.find('*/', i + 2)
                if j < 0:
                    raise ValueError('Unterminated JSONC comment')
                j += 2
            for k in range(i, j):
                if chars[k] not in ('\n', '\r'):
                    chars[k] = ' '
            i = j
            continue
        i += 1
    return ''.join(chars)


def update_fastfetch(source: str):
    """Replace just the top-level `logo` JSONC value, or insert one without losing modules."""
    palette = {
        'type': 'file', 'source': FASTFETCH_LOGO,
        'color': {'1': '#af55fb', '2': '#6978ff', '3': '#5bd5eb'},
        'padding': {'right': 3}
    }
    insert = json.dumps(palette, ensure_ascii=False)
    masked = masked_jsonc(source)
    start = masked.find('{')
    if start == -1:
        raise ValueError('Existing fastfetch config has no JSON object')
    depth = 0
    quoted = False
    i = start
    end_root = -1
    found = None
    while i < len(masked):
        char = masked[i]
        if char == '"':
            j = i + 1
            while j < len(masked):
                if masked[j] == '\\':
                    j += 2
                elif masked[j] == '"':
                    break
                else:
                    j += 1
            if j >= len(masked):
                raise ValueError('Invalid fastfetch JSONC string')
            if depth == 1 and json.loads(masked[i:j + 1]) == 'logo':
                k = j + 1
                while k < len(masked) and masked[k].isspace():
                    k += 1
                if k < len(masked) and masked[k] == ':':
                    val_start = k + 1
                    k = val_start
                    inner_depth = 0
                    in_quote = False
                    while k < len(masked):
                        tok = masked[k]
                        if in_quote:
                            if tok == '\\':
                                k += 2
                                continue
                            if tok == '"':
                                in_quote = False
                        elif tok == '"':
                            in_quote = True
                        elif tok in '[{':
                            inner_depth += 1
                        elif tok in ']}':
                            if inner_depth == 0:
                                break
                            inner_depth -= 1
                        elif tok == ',' and inner_depth == 0:
                            break
                        k += 1
                    found = (val_start, k)
                    break
            i = j + 1
            continue
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                end_root = i
                break
        i += 1
    if found is not None:
        a, b = found
        return source[:a] + ' ' + insert + source[b:]
    if end_root < 0:
        raise ValueError('Existing fastfetch JSONC has unbalanced braces')
    # Insert first property; preserve other root members, comments, custom modules and formatting.
    has_properties = bool(masked[start + 1:end_root].strip())
    return source[:start + 1] + '\n  "logo": ' + insert + (',' if has_properties else '') + source[start + 1:]


def strip_managed(text):
    if BRAND_START in text and BRAND_END in text:
        before, rest = text.split(BRAND_START, 1)
        _, after = rest.split(BRAND_END, 1)
        return (before.rstrip('\n') + '\n' + after.lstrip('\n')).strip('\n') + '\n'
    return text


def apply(home: Path):
    ff_path = home / '.config/fastfetch/config.jsonc'
    ff_before = ff_path.read_text(encoding='utf-8') if ff_path.exists() else None
    if ff_before is None:
        write(ff_path, (APP/'config/fetch/fastfetch.jsonc').read_text(encoding='utf-8'))
    else:
        write(ff_path, update_fastfetch(ff_before))
    neo_path = home / '.config/neofetch/config.conf'
    neo_old = neo_path.read_text(encoding='utf-8') if neo_path.exists() else ''
    body = (APP/'config/fetch/neofetch.conf').read_text(encoding='utf-8')
    neo_new = strip_managed(neo_old).rstrip('\n') + '\n\n' + BRAND_START + '\n' + body + BRAND_END + '\n'
    write(neo_path, neo_new)
    # screenfetch doesn't have a default config; Bash invokes native -a option.
    # Import via a small managed block in .bashrc, retaining everything else.
    rc = home / '.bashrc'
    old = rc.read_text(encoding='utf-8') if rc.exists() else ''
    snippet = 'if [ -f /opt/novaos/app/config/fetch/bash-branding.sh ]; then\n  . /opt/novaos/app/config/fetch/bash-branding.sh\nfi\n'
    new = strip_managed(old).rstrip('\n') + '\n\n' + BRAND_START + '\n' + snippet + BRAND_END + '\n'
    write(rc, new)
    # Optional `fetch` client that reads ~/.config/fetch/logo.txt natively.
    fetch_logo = home / '.config/fetch/logo.txt'
    if not fetch_logo.exists():
        write(fetch_logo, (APP/'assets/logos/nova-ascii.txt').read_text(encoding='utf-8'))
    if os.geteuid() == 0:
        uid, gid = home.stat().st_uid, home.stat().st_gid
        for name in (ff_path, neo_path, rc, fetch_logo):
            os.chown(name, uid, gid)
            for backup in name.parent.glob(name.name + '.backup-*'):
                os.chown(backup, uid, gid)
            folder = name.parent
            while folder != home and home in folder.parents:
                os.chown(folder, uid, gid)
                folder = folder.parent
    return 'Branding configurado para Fastfetch, Neofetch, Screenfetch, pfetch (Bash) e fetch (se instalado).'


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Uso: enable-branding.py /home/nova')
    print(apply(Path(sys.argv[1]).expanduser().resolve()))
