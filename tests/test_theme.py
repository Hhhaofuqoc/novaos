"""Offline integration tests of the XFCE configurator with a stateful xfconf double.

These verify installer/configuration behavior, not actual XFCE rendering.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'themes' / 'apply-xfce.sh'

XFCONF_STUB = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args=sys.argv[1:]
p=Path(os.environ['XFCONF_STORE'])
data=json.loads(p.read_text()) if p.exists() else {}
c=args[args.index('-c')+1]
channel=data.setdefault(c,{})
if '-l' in args or '-lv' in args:
    for key in channel: print(key)
    sys.exit(0)
key=args[args.index('-p')+1]
if '-r' in args:
    for k in list(channel):
        if k==key or ('-R' in args and k.startswith(key+'/')): del channel[k]
elif '-s' in args:
    values=[args[i+1] for i,a in enumerate(args) if a=='-s']
    channel[key]=values if '-a' in args else values[-1]
else:
    if key not in channel: sys.exit(1)
    print(channel[key]); sys.exit(0)
p.write_text(json.dumps(data))
'''


class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.home=Path(self.temp.name)
        self.bin=self.home/'bin'; self.bin.mkdir()
        for name,contents in {
            'xfconf-query':XFCONF_STUB,
            'xfce4-panel':'#!/bin/sh\nexit 0\n',
            'xfdesktop':'#!/bin/sh\nexit 0\n',
            'xrandr':'#!/bin/sh\nprintf "  1920x1080 60.0*+\\n"\n',
        }.items():
            path=self.bin/name;path.write_text(contents);path.chmod(0o755)
        self.env={**os.environ,'HOME':str(self.home),'XDG_CONFIG_HOME':str(self.home/'.config'),
                  'PATH':str(self.bin)+os.pathsep+os.environ['PATH'],
                  'DISPLAY':':77','DBUS_SESSION_BUS_ADDRESS':'unix:path=/tmp/test-novaos',
                  'NOVAOS_ASSETS':str(ROOT),'XFCONF_STORE':str(self.home/'xfconf.json')}
        self.store=Path(self.env['XFCONF_STORE'])
        self.store.write_text(json.dumps({'xfce4-desktop':{
            '/backdrop/screen0/monitorVirtual-1/workspace0/last-image':'old.png'
        }}))

    def tearDown(self):self.temp.cleanup()

    def run_theme(self,*args,check=True,env=None):
        return subprocess.run(['bash',str(SCRIPT),*args],env=env or self.env,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=check)

    def test_first_run_sets_real_plugins_launchers_and_backup(self):
        original=self.home/'.config/xfce4/panel/custom.rc'
        original.parent.mkdir(parents=True); original.write_text('keep me')
        self.run_theme('lite','dark')
        data=json.loads(self.store.read_text())
        self.assertEqual(data['xfwm4']['/general/use_compositing'],'false')
        self.assertEqual(data['xfce4-panel']['/plugins/plugin-6'],'pulseaudio')
        self.assertEqual(data['xfce4-panel']['/plugins/plugin-7'],'notification-plugin')
        self.assertEqual(data['xfce4-panel']['/plugins/plugin-2'],'tasklist')
        marker=self.home/'.config/novaos/layout-v1'
        backup=Path(marker.read_text().strip())
        self.assertEqual((backup/'xfce4/panel/custom.rc').read_text(),'keep me')
        launcher=self.home/'.config/xfce4/panel/launcher-14/novaos.desktop'
        self.assertIn('Exec=novaos music',launcher.read_text())
        wp=data['xfce4-desktop']['/backdrop/screen0/monitorVirtual-1/workspace0/last-image']
        self.assertEqual(wp,str(ROOT/'wallpapers/novaos-desktop.png'))

    def test_second_run_preserves_custom_layout(self):
        self.run_theme('lite','dark')
        data=json.loads(self.store.read_text())
        data['xfce4-panel']['/panels/panel-1/size']='99'
        self.store.write_text(json.dumps(data))
        self.run_theme('balanced','light')
        data=json.loads(self.store.read_text())
        self.assertEqual(data['xfce4-panel']['/panels/panel-1/size'],'99')
        self.assertEqual(data['xfwm4']['/general/use_compositing'],'true')
        self.assertEqual(data['xsettings']['/Net/ThemeName'],'NovaOS-Light')
        self.assertEqual(len(list((self.home/'.config/novaos/backups').iterdir())),1)

    def test_explicit_reset_makes_new_backup(self):
        self.run_theme('lite','dark')
        self.run_theme('lite','dark','--reset-layout')
        self.assertEqual(len(list((self.home/'.config/novaos/backups').iterdir())),2)

    def test_portrait_uses_mobile_wallpaper(self):
        (self.bin/'xrandr').write_text('#!/bin/sh\nprintf "  1080x2400 60.0*+\\n"\n')
        self.run_theme('lite','dark')
        data=json.loads(self.store.read_text())
        self.assertTrue(data['xfce4-desktop']['/backdrop/screen0/monitorVirtual-1/workspace0/last-image'].endswith('novaos-mobile.png'))

    def test_fresh_profile_discovers_real_monitor_connector(self):
        self.store.write_text('{}')
        (self.bin/'xrandr').write_text(
            '#!/bin/sh\nprintf "screen connected 1920x1080+0+0\\n  1920x1080 60.0*+\\n"\n')
        self.run_theme('lite','dark')
        data=json.loads(self.store.read_text())
        for workspace in (0,1):
            key=f'/backdrop/screen0/monitorscreen/workspace{workspace}/last-image'
            self.assertEqual(data['xfce4-desktop'][key],str(ROOT/'wallpapers/novaos-desktop.png'))
        self.assertEqual(data['xfce4-desktop']['/backdrop/single-workspace-mode'],'true')

    def test_panel_shutdown_is_bounded(self):
        import time
        (self.bin/'xfce4-panel').write_text(
            '#!/bin/sh\nif [ "$1" = "--quit" ]; then sleep 20; fi\nexit 0\n')
        began=time.monotonic()
        self.run_theme('lite','dark')
        self.assertLess(time.monotonic()-began,10)
        self.assertTrue((self.home/'.config/novaos/layout-v1').exists())

    def test_rejects_invalid_args_without_modification(self):
        before=self.store.read_bytes()
        for args in [('fake','dark'),('lite','invalid'),('lite','dark','oops')]:
            self.assertEqual(self.run_theme(*args,check=False).returncode,2)
        self.assertEqual(before,self.store.read_bytes())

    def test_requires_real_session(self):
        env={**self.env,'DISPLAY':''}
        self.assertNotEqual(self.run_theme('lite','dark',env=env,check=False).returncode,0)

    def test_static_art_and_icons_are_valid_original_svg(self):
        for path in list((ROOT/'wallpapers').glob('*.svg'))+list((ROOT/'themes/icons').rglob('*.svg')):
            root=ET.parse(path).getroot()
            self.assertTrue(root.tag.endswith('svg'))
            self.assertNotIn('http://', ''.join(root.itertext()))
        png=ROOT/'wallpapers/novaos-desktop.png'
        self.assertEqual(png.read_bytes()[:8],b'\x89PNG\r\n\x1a\n')

    def test_generator_is_deterministic(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('novaos_asset_generator',ROOT/'themes/generate-assets.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        self.assertEqual(mod.wallpaper(3840,2160),(ROOT/'wallpapers/novaos-desktop.svg').read_text())
        self.assertEqual(mod.wallpaper(1080,2400,True),(ROOT/'wallpapers/novaos-mobile.svg').read_text())


if __name__=='__main__': unittest.main()
