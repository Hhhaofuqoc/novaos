#!/usr/bin/env python3
"""Boot the actual read-only ISO in QEMU and inspect the live KDE guest via QGA."""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time


class JsonSocket:
    def __init__(self, path, qmp=False):
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.settimeout(15)
        self.socket.connect(str(path))
        self.stream = self.socket.makefile('rwb', buffering=0)
        if qmp:
            self.receive()
            self.call('qmp_capabilities')
        else:
            # QGA persists across client reconnects. Flush partial/stale replies
            # using its documented synchronization marker before issuing RPCs.
            identifier=time.monotonic_ns() % (2**52)
            request={'execute':'guest-sync-delimited','arguments':{'id':identifier}}
            self.stream.write(b'\xff'+json.dumps(request).encode()+b'\n')
            while self.receive().get('return') != identifier:
                pass

    def receive(self):
        while True:
            line = self.stream.readline()
            if not line:
                raise ConnectionError('QEMU socket closed')
            # guest-sync-delimited prefixes the matching response with 0xff.
            result = json.loads(line.rsplit(b'\xff',1)[-1])
            if 'event' not in result:
                return result

    def call(self, command, arguments=None):
        request = {'execute': command}
        if arguments:
            request['arguments'] = arguments
        self.stream.write(json.dumps(request).encode()+b'\n')
        result = self.receive()
        if 'error' in result:
            raise RuntimeError(str(result['error']))
        return result.get('return')

    def close(self):
        self.stream.close()
        self.socket.close()


PROBE = r'''
import json, os, pathlib, subprocess
home=pathlib.Path('/home/nova')
names={}
for path in pathlib.Path('/proc').iterdir():
    if not path.name.isdigit(): continue
    try: names[int(path.name)]=(path/'comm').read_text().strip()
    except OSError: pass
shell=next((pid for pid,name in names.items() if name=='plasmashell'),None)
result={'live':pathlib.Path('/run/live/medium').exists(),
        'kernel':os.uname().release,'architecture':os.uname().machine,
        'plasmashell':bool(shell),'kwin_x11':'kwin_x11' in names.values(),
        'theme':(home/'.config/novaos/plasma-appearance').exists(),
        'wallpaper':pathlib.Path('/usr/share/novaos/wallpapers/novaos-night-room.png').exists()}
if shell and result['theme']:
    # Consume only the named session selectors; do not dump environment/cookies.
    pairs=pathlib.Path(f'/proc/{shell}/environ').read_bytes().split(bytes([0]))
    environment=dict(p.decode(errors='replace').split('=',1) for p in pairs if b'=' in p)
    allowed=('DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR','XDG_SESSION_TYPE','XDG_CURRENT_DESKTOP','LANG','LANGUAGE')
    prefix=['runuser','-u','nova','--','env','HOME=/home/nova','USER=nova','LOGNAME=nova']
    prefix += [key+'='+environment[key] for key in allowed if key in environment]
    wm=subprocess.run(prefix+['wmctrl','-m'],capture_output=True,text=True,timeout=20)
    desktops=subprocess.run(prefix+['wmctrl','-d'],capture_output=True,text=True,timeout=20)
    result['window_manager']=wm.stdout.strip()
    result['desktops']=len(desktops.stdout.splitlines())
    result['windows']=subprocess.run(prefix+['wmctrl','-l'],capture_output=True,text=True,timeout=20).stdout
    result['widgets']='NovaOS Desktop Widgets' in result['windows']
    result['ready']=result['live'] and result['kwin_x11'] and result['wallpaper'] and result['widgets'] and 'KWin' in wm.stdout and result['desktops']==4
    if result['ready'] and not (home/'.cache/novaos-iso-boot-probe').exists():
        for args in [['konsole','--separate','-e','bash','-c','novafetch --wide; exec bash'],
                     ['dolphin'], ['novaos','music','--background','--ambient','--toggle']]:
            subprocess.Popen(prefix+args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        (home/'.cache').mkdir(exist_ok=True)
        (home/'.cache/novaos-iso-boot-probe').touch()
    result['windows']=subprocess.run(prefix+['wmctrl','-l'],capture_output=True,text=True,timeout=20).stdout
    result['apps_ready']='Konsole' in result['windows'] and ('Dolphin' in result['windows'] or 'dolphin' in result['windows'])
    playback=pathlib.Path(environment.get('XDG_RUNTIME_DIR','/run/user/1000'))/'novaos/playback.json'
    if playback.exists(): result['music']=json.loads(playback.read_text())
print(json.dumps(result))
'''


def execute_guest(agent):
    process = agent.call('guest-exec', {'path': '/usr/bin/python3', 'arg': ['-c', PROBE], 'capture-output': True})
    deadline = time.monotonic()+65
    while time.monotonic() < deadline:
        result = agent.call('guest-exec-status', {'pid': process['pid']})
        if result.get('exited'):
            output = base64.b64decode(result.get('out-data', '')).decode(errors='replace')
            if result.get('exitcode'):
                error = base64.b64decode(result.get('err-data', '')).decode(errors='replace')
                raise RuntimeError(error[-1500:])
            return json.loads(output)
        time.sleep(.4)
    raise TimeoutError('Guest probe timed out')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iso', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--firmware', choices=['bios', 'uefi'], default='bios')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    if not args.iso.is_file():
        parser.error('Actual ISO file required')
    target = args.output.resolve(); target.mkdir(parents=True, exist_ok=True)
    qmp_path, agent_path = target/'qmp.sock', target/'qga.sock'
    if qmp_path.exists() or agent_path.exists():
        parser.error('Use a fresh output directory')
    accel = 'kvm' if os.access('/dev/kvm', os.R_OK|os.W_OK) else 'tcg,thread=multi'
    command = ['qemu-system-x86_64', '-machine', 'q35', '-accel', accel,
               '-cpu', 'host' if accel=='kvm' else 'max', '-m', '4096', '-smp', '2',
               '-cdrom', str(args.iso.resolve()), '-boot', 'd', '-display', 'none',
               '-vga', 'virtio', '-serial', 'file:'+str(target/'serial.log'),
               '-qmp', f'unix:{qmp_path},server=on,wait=off',
               '-chardev', f'socket,path={agent_path},server=on,wait=off,id=qga0',
               '-device', 'virtio-serial', '-device', 'virtserialport,chardev=qga0,name=org.qemu.guest_agent.0',
               '-audiodev', 'none,id=audio0', '-device', 'ich9-intel-hda', '-device', 'hda-duplex,audiodev=audio0',
               '-nic', 'user,model=virtio-net-pci', '-no-reboot']
    if args.firmware=='uefi':
        code=Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
        variables=Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
        if not code.exists() or not variables.exists():
            parser.error('OVMF 4M firmware required')
        shutil.copy2(variables,target/'OVMF_VARS.fd')
        command += ['-drive',f'if=pflash,format=raw,readonly=on,file={code}',
                    '-drive',f'if=pflash,format=raw,file={target / "OVMF_VARS.fd"}']
    report={'passed':False,'firmware':args.firmware,'acceleration':accel,'memory_mib':4096,
            'scope':'Real ISO boot in virtual hardware; not physical-PC validation',
            'physical_audio_tested':False,'physical_disk_attached':False}
    log=(target/'qemu.log').open('w')
    proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    started=time.monotonic();qmp=None
    try:
        deadline=started+args.timeout
        while time.monotonic()<deadline:
            if proc.poll() is not None:
                raise RuntimeError('QEMU exited: '+(target/'qemu.log').read_text()[-1000:])
            if qmp is None and qmp_path.exists():
                qmp=JsonSocket(qmp_path,qmp=True)
            try:
                agent=JsonSocket(agent_path)
                try:
                    agent.call('guest-ping')
                    guest=execute_guest(agent)
                finally:
                    agent.close()
                report['guest']=guest
                if guest.get('ready') and guest.get('apps_ready'):
                    report['passed']=True
                    break
            except (OSError,TimeoutError,RuntimeError,ValueError,ConnectionError) as error:
                report['last_probe_error']=str(error)[-1500:]
            time.sleep(6)
        report['elapsed_seconds']=round(time.monotonic()-started,2)
        if qmp:
            qmp.call('screendump',{'filename':str(target/'screen.ppm')})
        if not report['passed']:
            raise RuntimeError('ISO did not reach a themed KDE Live session before timeout')
        print(json.dumps(report,indent=2))
        return 0
    finally:
        (target/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        if qmp:
            try: qmp.call('quit')
            except (OSError,RuntimeError,ConnectionError): pass
            qmp.close()
        if proc.poll() is None:
            proc.terminate()
        try: proc.wait(timeout=15)
        except subprocess.TimeoutExpired: proc.kill();proc.wait()
        log.close()


if __name__=='__main__':
    raise SystemExit(main())
