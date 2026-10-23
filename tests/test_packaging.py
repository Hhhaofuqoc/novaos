"""Checks real Debian payloads; no installation or root privileges required."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackagingInputsTests(unittest.TestCase):
    def test_package_lists_valid_and_shared_list_has_no_boot_services(self):
        for name in ('packages-lite.txt', 'packages-desktop.txt', 'packages-plasma.txt'):
            packages = [line for line in (ROOT / 'desktop' / name).read_text().splitlines()
                        if line and not line.startswith('#')]
            self.assertEqual(len(packages), len(set(packages)), name)
            for package in packages:
                self.assertRegex(package, r'^[a-z0-9][a-z0-9+.-]+$')
        lite = (ROOT / 'desktop/packages-lite.txt').read_text().splitlines()
        for desktop_only in ('lightdm', 'systemd-sysv', 'linux-image-amd64', 'network-manager'):
            self.assertNotIn(desktop_only, lite)
        self.assertIn('python3-gi', lite)
        self.assertIn('gstreamer1.0-pulseaudio', lite)

    def test_shell_syntax(self):
        for path in (ROOT / 'desktop/build-iso.sh', ROOT / 'scripts/build-deb.sh',
                     ROOT / 'scripts/release.sh'):
            result = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_version_rejected_before_staging(self):
        result = subprocess.run(['bash', str(ROOT / 'scripts/build-deb.sh')],
                                env={**os.environ, 'NOVAOS_VERSION': '../invalid'},
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Invalid Debian package version', result.stderr)

    def test_iso_invalid_edition_rejected_without_tools_or_root(self):
        result = subprocess.run(['bash', str(ROOT / 'desktop/build-iso.sh'), '--edition', 'imaginary'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Edition must be', result.stderr)


@unittest.skipUnless(shutil.which('dpkg-deb'), 'dpkg-deb is required for real package checks')
class DebianPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='novaos-package-test-')
        cls.out = Path(cls.temp.name) / 'dist'
        env = {**os.environ, 'NOVAOS_DIST_DIR': str(cls.out), 'NOVAOS_VERSION': '0.1.0'}
        result = subprocess.run(['bash', str(ROOT / 'scripts/build-deb.sh')], env=env,
                                capture_output=True, text=True, timeout=180)
        if result.returncode:
            cls.temp.cleanup()
            raise AssertionError(result.stdout + result.stderr)
        cls.package = cls.out / 'novaos-desktop_0.1.0_all.deb'
        cls.extracted = Path(cls.temp.name) / 'payload'
        subprocess.run(['dpkg-deb', '--extract', str(cls.package), str(cls.extracted)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_debian_archive_and_installed_files(self):
        result = subprocess.run(['dpkg-deb', '--field', str(self.package), 'Package', 'Architecture'],
                                capture_output=True, text=True, check=True)
        self.assertIn('novaos-desktop', result.stdout)
        self.assertIn('all', result.stdout)
        self.assertTrue((self.extracted / 'usr/bin/novaos').is_file())
        self.assertTrue(os.access(self.extracted / 'usr/bin/novaos', os.X_OK))
        self.assertTrue((self.extracted / 'usr/lib/python3/dist-packages/novaos/__main__.py').is_file())
        self.assertTrue((self.extracted / 'usr/share/novaos/wallpapers/novaos-desktop.svg').is_file())
        self.assertTrue(list((self.extracted / 'usr/share/applications').glob('*.desktop')))

    def test_album_not_in_core_package(self):
        self.assertFalse((self.extracted / 'usr/share/novaos/music/generated').exists())
        if (ROOT / 'music/generated/manifest.json').exists():
            self.assertTrue((self.out / 'novaos-music_0.1.0_all.deb').is_file())

    def test_control_dependencies_and_config_preservation(self):
        result = subprocess.run(['dpkg-deb', '--field', str(self.package), 'Depends'],
                                capture_output=True, text=True, check=True)
        for dependency in ('python3-gi', 'python3-psutil', 'gstreamer1.0-plugins-good'):
            self.assertIn(dependency, result.stdout)
        control = Path(self.temp.name) / 'control'
        subprocess.run(['dpkg-deb', '--control', str(self.package), str(control)], check=True)
        installed_config = [p for p in (self.extracted / 'etc').rglob('*') if p.is_file()]
        if installed_config:
            conffiles = (control / 'conffiles').read_text().splitlines()
            for path in installed_config:
                self.assertIn('/' + str(path.relative_to(self.extracted)), conffiles)


if __name__ == '__main__':
    unittest.main()
