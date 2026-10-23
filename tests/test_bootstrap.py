import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_bootstrap', ROOT/'scripts/build-bootstrap.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='novaos-bootstrap-')
        self.root = Path(self.temp.name)
        self.home = self.root/'home'
        self.home.mkdir()
        self.bin = self.root/'bin'
        self.bin.mkdir()
        (self.bin/'pkg').touch(mode=0o755)
        self.marker = self.home/'installed'
        self.bundle = self.root/'bundle.tar.gz'
        installer = b'#!/bin/bash\nprintf installed > "$HOME/installed"\n'
        manifest = (hashlib.sha256(installer).hexdigest()+'  mobile/install-termux.sh\n').encode()
        with tarfile.open(self.bundle, 'w:gz') as archive:
            for name, contents in [('mobile/install-termux.sh', installer), ('SHA256SUMS', manifest)]:
                entry = tarfile.TarInfo('novaos-0.1.0/'+name)
                entry.size = len(contents)
                archive.addfile(entry, io.BytesIO(contents))
        self.bootstrap = self.root/'install-novaos.sh'
        builder.render(self.bundle, 'https://downloads.example.test/v0.1.0', '0.1.0', self.bootstrap)
        curl = self.bin/'curl'
        curl.write_text('#!/bin/bash\nset -eu\nwhile (($#)); do if [[ $1 == --output ]]; then cp "$TEST_ARCHIVE" "$2"; exit; fi; shift; done\nexit 2\n')
        curl.chmod(0o755)
        self.env = {**os.environ, 'HOME': str(self.home), 'PREFIX': str(self.root),
                    'PATH': str(self.bin)+os.pathsep+os.environ['PATH'], 'TEST_ARCHIVE': str(self.bundle)}

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, args=(), env=None):
        return subprocess.run(['bash', str(self.bootstrap), *args], env=env or self.env,
                              capture_output=True, text=True)

    def test_verified_download_installs_and_preserves_sources(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(self.marker.read_text(), 'installed')
        self.assertEqual(len(list(self.home.glob('novaos-0.1.0.*/novaos-0.1.0/mobile/install-termux.sh'))), 1)
        self.assertEqual(list((self.home/'.cache').iterdir()), [])

    def test_tampered_archive_never_extracts_or_executes(self):
        self.bundle.write_bytes(b'tampered archive')
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.marker.exists())
        self.assertEqual(list(self.home.glob('novaos-0.1.0.*')), [])

    def test_download_only_never_executes_installation(self):
        result = self.run_script(['--download-only'])
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertFalse(self.marker.exists())

    def test_source_manifest_failure_never_installs(self):
        with tarfile.open(self.bundle, 'w:gz') as archive:
            for name, contents in [('mobile/install-termux.sh', b'exit 0'), ('SHA256SUMS', b'0'*64+b'  mobile/install-termux.sh\n')]:
                entry = tarfile.TarInfo('novaos-0.1.0/'+name)
                entry.size = len(contents)
                archive.addfile(entry, io.BytesIO(contents))
        builder.render(self.bundle, 'https://downloads.example.test/v0.1.0', '0.1.0', self.bootstrap)
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.marker.exists())
        self.assertEqual(list(self.home.glob('novaos-0.1.0.*')), [])

    def test_generated_script_checksum_and_https_requirement(self):
        expected = hashlib.sha256(self.bootstrap.read_bytes()).hexdigest()
        self.assertEqual(Path(str(self.bootstrap)+'.sha256').read_text().split()[0], expected)
        for invalid in ('http://example.test', 'https://user:secret@example.test', 'https://example.test/?secret=x'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                builder.render(self.bundle, invalid, '0.1.0', self.bootstrap)

    def test_download_failure_preserves_existing_home_data(self):
        (self.bin/'curl').write_text('#!/bin/bash\nexit 22\n')
        note = self.home/'important-note.txt'
        note.write_text('keep me')
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.marker.exists())
        self.assertEqual(note.read_text(), 'keep me')


if __name__ == '__main__':
    unittest.main()
