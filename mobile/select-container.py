#!/usr/bin/env python3
"""Select a free or NovaOS-owned PRoot container without changing any rootfs."""
from pathlib import Path
import re
import subprocess
import sys
from novaos_mobile import load_container_alias


def select(metadata):
    # v5.10.2 explicitly provides bare names on stdout with list --quiet.
    inventory = subprocess.run(['proot-distro', 'list', '--quiet'],
                               capture_output=True, text=True, check=True)
    names = set(inventory.stdout.splitlines())
    if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name) for name in names):
        raise RuntimeError('Resposta inesperada ao listar ambientes PRoot; nenhum ambiente foi alterado')
    preferred = load_container_alias(metadata, default=None)
    candidates = ([preferred] if preferred else []) + ['novaos', 'novaos-lite'] + [f'novaos-lite-{i}' for i in range(2, 100)]
    for name in dict.fromkeys(candidates):
        if name not in names:
            return name
        owned = subprocess.run(['proot-distro', 'login', name, '--', '/usr/bin/test',
                                '-f', '/etc/novaos-mobile-owner'], capture_output=True)
        if owned.returncode == 0:
            return name
        print(f'Ambiente {name} preservado; escolhendo outro nome para esta instalação.', file=sys.stderr)
    raise RuntimeError('Não foi encontrado um nome livre para o ambiente NovaOS')


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('Uso: select-container.py CAMINHO-DO-installed.json')
        print(select(Path(sys.argv[1])))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'NovaOS: {error}', file=sys.stderr)
        raise SystemExit(1)
