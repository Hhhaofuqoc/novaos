"""Métricas honestas: ausente = None, nunca números inventados."""
import json
import os
import time
from pathlib import Path

METRICS = Path('/tmp/novaos-metrics.json')

def host():
    try:
        value = json.loads(METRICS.read_text())
        if time.time() - float(value['timestamp']) > 8: return {}
        return value
    except (OSError, ValueError, KeyError, TypeError): return {}

def ram_android():
    # Em PRoot /proc/meminfo normalmente se refere à RAM real do Android.
    try:
        data = {}
        for line in Path('/proc/meminfo').read_text().splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                data[k] = int(v.strip().split()[0])*1024
        total = data.get('MemTotal'); available = data.get('MemAvailable')
        return (total-available, total) if total and available is not None else None
    except (OSError, ValueError, IndexError): return None

def storage():
    try:
        s = os.statvfs(str(Path.home()))
        return (s.f_blocks-s.f_bfree)*s.f_frsize, s.f_blocks*s.f_frsize, s.f_bavail*s.f_frsize
    except OSError: return None

def human_rate(b):
    if b is None: return 'Indisponível'
    return f'{b/1048576:.1f} MB/s' if b >= 1048576 else f'{b/1024:.0f} KB/s'
