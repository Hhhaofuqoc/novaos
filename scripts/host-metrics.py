#!/usr/bin/env python3
"""Mede APENAS dados que o Android permite ler. Sem CPU/Rede fictícios."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

DEST = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/novaos-metrics.json')
DEST.parent.mkdir(parents=True, exist_ok=True)

def cpu():
    try:
        line = Path('/proc/stat').read_text().splitlines()[0].split()
        if line[0] != 'cpu': return None
        fields = list(map(int, line[1:]))
        return sum(fields), fields[3] + (fields[4] if len(fields) > 4 else 0)
    except (OSError, ValueError, IndexError): return None

def net():
    try:
        sums = [0, 0]
        for line in Path('/proc/net/dev').read_text().splitlines()[2:]:
            dev, values = line.split(':', 1)
            dev = dev.strip()
            if dev == 'lo' or dev.startswith(('veth', 'dummy')): continue
            f = values.split(); sums[0] += int(f[0]); sums[1] += int(f[8])
        return tuple(sums)
    except (OSError, ValueError, IndexError): return None

def battery():
    p = Path('/sys/class/power_supply')
    try:
        for item in p.iterdir():
            if (item/'type').read_text().strip().lower() != 'battery': continue
            v = int((item/'capacity').read_text().strip())
            if 0 <= v <= 100: return v
    except (OSError, ValueError): pass
    return None

old_cpu, old_net, last = cpu(), net(), time.monotonic()
while True:
    time.sleep(2.0)
    c, n, now = cpu(), net(), time.monotonic()
    out = {'timestamp': time.time(), 'cpu_percent': None,
           'download_bps': None, 'upload_bps': None, 'battery_percent': battery()}
    if c and old_cpu:
        dt = c[0]-old_cpu[0]; idle = c[1]-old_cpu[1]
        if dt > 0 and 0 <= idle <= dt:
            out['cpu_percent'] = max(0., min(100., (dt-idle)*100.0/dt))
    if n and old_net and now > last:
        diff = [n[i]-old_net[i] for i in range(2)]
        if all(0 <= x < 2**32 for x in diff):
            out['download_bps'] = round(diff[0]/(now-last))
            out['upload_bps'] = round(diff[1]/(now-last))
    old_cpu, old_net, last = c, n, now
    tmp = DEST.with_suffix('.tmp')
    try:
        tmp.write_text(json.dumps(out), encoding='utf8')
        os.replace(tmp, DEST)
    except OSError: pass
