"""Stage and update the actual system installer without changing the host."""
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SystemInstallerTests(unittest.TestCase):
    def test_staging_update_preserves_user_data_and_modes(self):
        with tempfile.TemporaryDirectory(prefix='novaos-install-') as tmp:
            base = Path(tmp)
            target = base / 'stage with spaces'
            personal = target / 'home/nova/Documents/keep.txt'
            personal.parent.mkdir(parents=True)
            personal.write_text('private user note\n')
            user_config = target / 'home/nova/.config/novaos/config.json'
            user_config.parent.mkdir(parents=True)
            user_config.write_text('{"theme":"light"}\n')
            real_home = base / 'host-home'
            real_home.mkdir()
            marker = real_home / 'untouched'
            marker.write_text('yes')
            command = ['bash', str(ROOT / 'installers/install-system.sh'), '--destdir', str(target), '--without-music']
            for _ in range(2):
                result = subprocess.run(command, env={**os.environ, 'HOME': str(real_home)},
                                        capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(personal.read_text(), 'private user note\n')
            self.assertEqual(user_config.read_text(), '{"theme":"light"}\n')
            self.assertEqual(list(real_home.iterdir()), [marker])
            self.assertFalse((target / 'usr/share/novaos/music/generated').exists())
            for relative, mode in (
                ('usr/bin/novaos', 0o755),
                ('usr/bin/novaos-terminal', 0o755),
                ('usr/lib/novaos/apt-helper', 0o755),
                ('usr/lib/python3/dist-packages/novaos/__main__.py', 0o644),
                ('usr/share/novaos/themes/apply-xfce.sh', 0o755),
                ('usr/share/themes/NovaOS-Dark/gtk-3.0/gtk.css', 0o644),
                ('usr/share/icons/NovaOS/index.theme', 0o644),
                ('etc/xdg/autostart/novaos-session.desktop', 0o644),
            ):
                self.assertEqual(stat.S_IMODE((target / relative).stat().st_mode), mode, relative)
            self.assertEqual(stat.S_IMODE((target / 'usr/share/themes/NovaOS-Dark').stat().st_mode), 0o755)
            self.assertFalse(list(target.rglob('*.pyc')))
            self.assertIn('OnlyShowIn=XFCE;', (target / 'etc/xdg/autostart/novaos-session.desktop').read_text())

    def test_unknown_argument_does_not_install(self):
        result = subprocess.run(['bash', str(ROOT / 'installers/install-system.sh'), '--unknown'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Unknown option', result.stderr)


if __name__ == '__main__':
    unittest.main()
