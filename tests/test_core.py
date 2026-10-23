"""Testes independentes de Android para núcleo sem dependência GTK."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree

ROOT=Path(__file__).resolve().parents[1]

def module(filename,name):
    spec=importlib.util.spec_from_file_location(name,filename)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

class Tests(unittest.TestCase):
    def test_icons_are_svg(self):
        icons=list((ROOT/'assets/icons').glob('*.svg'))
        self.assertGreaterEqual(len(icons),18)
        for icon in icons:
            root=ElementTree.parse(icon).getroot()
            self.assertTrue(root.tag.endswith('svg'))
            self.assertIn('viewBox',root.attrib)
    def test_config_roundtrip(self):
        state=module(ROOT/'nova-shell/services/state.py','state')
        with tempfile.TemporaryDirectory() as d:
            state.PATH=Path(d)/'settings.json'
            self.assertTrue(state.load()['show_dock'])
            data=state.load();data['favorites']=['geany.desktop']
            state.save(data)
            self.assertEqual(state.load()['favorites'],['geany.desktop'])
    def test_metrics_absence_is_not_zero(self):
        status=module(ROOT/'nova-shell/services/status.py','status')
        with tempfile.TemporaryDirectory() as d:
            status.METRICS=Path(d)/'missing.json'
            self.assertEqual(status.host(),{})
            self.assertEqual(status.human_rate(None),'Indisponível')
    def test_no_xfce_dependency(self):
        self.assertNotIn('xfce4-', (ROOT/'scripts/setup-guest.sh').read_text())
    def test_openbox_has_four_workspaces(self):
        xml=ElementTree.parse(ROOT/'config/openbox/rc.xml')
        ns={'o':'http://openbox.org/3.4/rc'}
        count=xml.find('.//o:desktops/o:number',ns)
        self.assertEqual(count.text,'4')
    def test_wallpaper_exists(self):
        self.assertGreater((ROOT/'assets/wallpapers/nova-night.webp').stat().st_size,10000)


class BrandingTests(unittest.TestCase):
    def test_ascii_logos_are_consistent(self):
        import re
        logos = ROOT/'assets/logos'
        plain = (logos/'nova-ascii.txt').read_text().splitlines()
        for name in ('nova-fastfetch.txt', 'nova-neofetch.txt'):
            colored = (logos/name).read_text()
            colored = re.sub(r'\$[123]', '', colored)
            colored = re.sub(r'\$\{c[123]\}', '', colored)
            self.assertEqual(plain, colored.splitlines())

    def test_fastfetch_jsonc_logo_change_preserves_modules(self):
        brand = module(ROOT/'scripts/enable-branding.py', 'branding')
        original = '''// user config\n{\n  // custom logo\n  "logo": {"type": "builtin", "source": "debian"},\n  "modules": ["title", "os", "kernel"],\n  "display": {"separator": " ➔ "}\n}\n'''
        updated = brand.update_fastfetch(original)
        self.assertIn('"modules": ["title", "os", "kernel"]', updated)
        self.assertIn('// custom logo', updated)
        self.assertIn('nova-fastfetch.txt', updated)
        self.assertNotIn('"source": "debian"', updated)
        self.assertEqual(brand.update_fastfetch(updated), updated)

    def test_branding_is_idempotent_and_backups_existing(self):
        brand = module(ROOT/'scripts/enable-branding.py', 'branding_apply')
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            brand.APP = ROOT
            (home/'.config/fastfetch').mkdir(parents=True)
            (home/'.config/fastfetch/config.jsonc').write_text('{"modules":["os", "memory"]}\n')
            (home/'.bashrc').write_text('export ALPHA=beta\n')
            brand.apply(home)
            self.assertIn('ALPHA=beta', (home/'.bashrc').read_text())
            self.assertIn('"modules":["os", "memory"]', (home/'.config/fastfetch/config.jsonc').read_text())
            self.assertEqual(len(list(home.glob('.bashrc.backup-*'))), 1)
            current = (home/'.config/fastfetch/config.jsonc').read_text()
            brand.apply(home)
            self.assertEqual(current, (home/'.config/fastfetch/config.jsonc').read_text())
            self.assertEqual(len(list(home.glob('.bashrc.backup-*'))), 1)

if __name__ == '__main__':
    unittest.main()
