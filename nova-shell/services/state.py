"""Persistência atômica das preferências pessoais da NovaOS."""
import json
import os
from pathlib import Path

PATH = Path.home() / '.config' / 'novaos' / 'settings.json'
DEFAULT = {'accent': 'violet', 'show_sidebar': True, 'show_dock': True,
           'wallpaper': '/opt/novaos/app/assets/wallpapers/nova-night.webp',
           'favorites': [], 'pinned': []}

def load():
    try:
        obj = json.loads(PATH.read_text(encoding='utf-8'))
        return {**DEFAULT, **obj} if isinstance(obj, dict) else dict(DEFAULT)
    except (OSError, ValueError, TypeError):
        return dict(DEFAULT)

def save(data):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(tmp, PATH)
