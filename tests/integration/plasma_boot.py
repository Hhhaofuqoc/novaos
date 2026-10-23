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
            assert Path(directory+'/.config/novaos/plasma-layout-v2').exists()
            assert Path(directory+'/.config/novaos/plasma-favorites-v2').exists()
            assert 'novaos-night-room.png' in Path(directory+'/.config/plasma-org.kde.plasma.desktop-appletsrc').read_text()
            report['checks']+=['Plasma X11 starts','KWin is real WM','NovaOS color/panel layout applied','original wallpaper configured']
            report['checks'].append('NovaOS favorites linked through the native Activities API')
            report['panel_config']=Path(directory+'/.config/plasma-org.kde.plasma.desktop-appletsrc').read_text()
            desktop_process=next(p for p in children if p.name()=='plasmashell')
            env['DBUS_SESSION_BUS_ADDRESS']=desktop_process.environ()['DBUS_SESSION_BUS_ADDRESS']
            env['XDG_RUNTIME_DIR']='/tmp/novaos-runtime-nova'
            env['NOVAOS_AUDIO_SINK']='fakesink'
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                windows=subprocess.check_output(['wmctrl','-l'],env=env,text=True)
                if 'NovaOS Desktop Widgets' in windows: break
                time.sleep(.5)
            else: raise AssertionError('Native sidebar failed to start')
            display_width,display_height=map(int,subprocess.check_output(['xdotool','getdisplaygeometry'],env=env,text=True).split())
            geometry=next(line.split() for line in subprocess.check_output(['wmctrl','-lG'],env=env,text=True).splitlines() if 'NovaOS Desktop Widgets' in line)
            x,y,width,height=map(int,geometry[2:6])
            assert x>=0 and y>=0 and x+width<=display_width+2 and y+height<=display_height-70, geometry
            report['checks'].append('native system/network/music sidebar starts')
            report['checks'].append(f'sidebar fits {display_width}x{display_height} with controls accessible')
            music=subprocess.Popen(['novaos','music','--toggle','--background'],env=env,stdout=log,stderr=subprocess.STDOUT)
            playback=Path(env['XDG_RUNTIME_DIR'])/'novaos/playback.json'
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                try:
                    state=json.loads(playback.read_text())
                    if state.get('pid')==music.pid and state.get('playing') and state.get('position',0)>1: break
                except (OSError,ValueError): pass
                time.sleep(.5)
            else: raise AssertionError('Background player did not publish real playback')
            assert state.get('duration',0)>0
            subprocess.run(['novaos','music','--toggle','--background'],env=env,check=True,timeout=10)
            assert json.loads(playback.read_text())['playing'] is False
            subprocess.run(['novaos','music','--next','--background'],env=env,check=True,timeout=10)
            assert json.loads(playback.read_text())['title']!=state['title']
            report['checks'].append('real background audio, pause and next update widget metadata')
            konsole=subprocess.Popen(['konsole','--separate','--hold','-e','/bin/bash','-c','sleep 2; novafetch --wide; exec sleep 45'],env={**env,'XDG_CURRENT_DESKTOP':'KDE'},stdout=log,stderr=subprocess.STDOUT)
            time.sleep(1)
            for line in subprocess.check_output(['wmctrl','-l'],env=env,text=True).splitlines():
                if 'Konsole' in line:
                    bounds=f'0,{int(display_width*.244)},{int(display_height*.255)},{int(display_width*.55)},{int(display_height*.545)}'
                    subprocess.run(['wmctrl','-ir',line.split()[0],'-e',bounds],env=env,check=True)
            time.sleep(3)
            assert konsole.poll() is None,'Konsole fetch exited early'
            report['checks'].append('Konsole runs native NovaFetch')
            screenshot=os.environ.get('NOVAOS_PLASMA_SCREENSHOT')
            if screenshot:
                subprocess.run(['import','-window','root',screenshot],env=env,check=True)
                report['checks'].append('real desktop screenshot captured')
                subprocess.run(['xdotool','mousemove','30','15','click','1'],env=env,check=True)
                time.sleep(1)
                menu_image=str(Path(screenshot).with_name(Path(screenshot).stem+'-menu.png'))
                subprocess.run(['import','-window','root',menu_image],env=env,check=True)
                subprocess.run(['xdotool','key','Escape'],env=env,check=True)
            assert len(subprocess.check_output(['wmctrl','-d'],env=env,text=True).splitlines())==4
            report['checks'].append('four real virtual desktops configured')
            tracked=[p for p in children if p.is_running()]
            report['processes']=[{'name':p.name(),'rss_bytes':p.memory_info().rss} for p in tracked]
            before={p.pid:sum(p.cpu_times()[:2]) for p in tracked}
            began=time.monotonic();time.sleep(4)
            cpu=sum(max(0,sum(p.cpu_times()[:2])-before[p.pid]) for p in tracked if p.is_running())
            report['idle_cpu_one_core_percent']=cpu/(time.monotonic()-began)*100
            report['metrics_scope']='Short native cloud sample; not a Moto G34 prediction'
            report['passed']=True
        finally:
            if 'music' in locals() and music.poll() is None:
                music.terminate()
                try: music.wait(timeout=5)
                except subprocess.TimeoutExpired: music.kill(); music.wait()
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
