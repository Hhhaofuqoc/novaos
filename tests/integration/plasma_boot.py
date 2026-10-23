#!/usr/bin/python3
"""Real Plasma X11 guest boot under Xvfb. Run as nova; no Android claims."""
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import tempfile
import time
import psutil

target=Path(os.environ.get('NOVAOS_PLASMA_REPORT','/tmp/novaos-plasma-report.json'))
report={'scope':'Native Debian x86_64 Plasma X11/Xvfb; not Android or PRoot','passed':False,'checks':[]}
with tempfile.TemporaryDirectory(prefix='novaos-plasma-') as directory:
    env={**os.environ,'HOME':directory,'XDG_CONFIG_HOME':directory+'/.config',
         'XDG_DATA_HOME':directory+'/.local/share','XDG_CACHE_HOME':directory+'/.cache'}
    profile=Path('/home/nova/.local/share/konsole/NovaOS.profile')
    assert profile.exists(),'Installed Konsole NovaOS profile missing'
    shutil.copytree(profile.parent,Path(directory)/'.local/share/konsole')
    Path(directory+'/.config').mkdir(parents=True,exist_ok=True)
    shutil.copyfile('/home/nova/.config/konsolerc',directory+'/.config/konsolerc')
    with open(directory+'/session.log','w') as log:
        proc=subprocess.Popen(['/usr/local/libexec/novaos-mobile-session','plasma'],env=env,
                              stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        children=[]
        try:
            deadline=time.monotonic()+70
            while time.monotonic()<deadline:
                if proc.poll() is not None: raise AssertionError('Plasma exited early')
                children=psutil.Process(proc.pid).children(recursive=True)
                names=[p.name() for p in children]
                if 'plasmashell' in names and Path(directory+'/.config/novaos/plasma-appearance').exists(): break
                time.sleep(1)
            else: raise AssertionError('Plasma/theme startup timed out')
            wm=subprocess.check_output(['wmctrl','-m'],env=env,text=True)
            assert 'KWin' in wm,wm
            assert Path(directory+'/.config/novaos/plasma-layout-v1').exists()
            assert 'novaos-desktop.png' in Path(directory+'/.config/plasma-org.kde.plasma.desktop-appletsrc').read_text()
            report['checks']+=['Plasma X11 starts','KWin is real WM','NovaOS color/panel layout applied','original wallpaper configured']
            report['panel_config']=Path(directory+'/.config/plasma-org.kde.plasma.desktop-appletsrc').read_text()
            konsole=subprocess.Popen(['konsole','--separate','--hold','-e','/bin/bash','-c','sleep 2; novafetch --wide; exec sleep 45'],env={**env,'XDG_CURRENT_DESKTOP':'KDE'},stdout=log,stderr=subprocess.STDOUT)
            time.sleep(1)
            for line in subprocess.check_output(['wmctrl','-l'],env=env,text=True).splitlines():
                if 'Konsole' in line:
                    subprocess.run(['wmctrl','-ir',line.split()[0],'-e','0,140,100,1250,660'],env=env,check=True)
            time.sleep(3)
            assert konsole.poll() is None,'Konsole fetch exited early'
            report['checks'].append('Konsole runs native NovaFetch')
            screenshot=os.environ.get('NOVAOS_PLASMA_SCREENSHOT')
            if screenshot:
                subprocess.run(['import','-window','root',screenshot],env=env,check=True)
                report['checks'].append('real desktop screenshot captured')
            tracked=[p for p in children if p.is_running()]
            report['processes']=[{'name':p.name(),'rss_bytes':p.memory_info().rss} for p in tracked]
            before={p.pid:sum(p.cpu_times()[:2]) for p in tracked}
            began=time.monotonic();time.sleep(4)
            cpu=sum(max(0,sum(p.cpu_times()[:2])-before[p.pid]) for p in tracked if p.is_running())
            report['idle_cpu_one_core_percent']=cpu/(time.monotonic()-began)*100
            report['metrics_scope']='Short native cloud sample; not a Moto G34 prediction'
            report['passed']=True
        finally:
            try: children=psutil.Process(proc.pid).children(recursive=True)
            except psutil.NoSuchProcess: children=[]
            for p in reversed(children):
                try:p.terminate()
                except psutil.Error:pass
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            _,remaining=psutil.wait_procs(children,timeout=2)
            for p in remaining:
                try:p.kill()
                except psutil.Error:pass
            report['log_tail']=Path(directory+'/session.log').read_text(errors='replace')[-9000:]
            target.write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report,indent=2))
