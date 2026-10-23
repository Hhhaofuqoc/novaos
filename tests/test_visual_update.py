"""Exercise the actual small update archive and its integrity-checked loader."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class VisualUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='novaos-visual-tests-')
        self.root=Path(self.temp.name)
        subprocess.run([sys.executable,str(ROOT/'scripts/build-visual-update.py'),'--output',str(self.root)],check=True,capture_output=True)

    def tearDown(self):self.temp.cleanup()

    def test_archive_includes_real_backend_switch_and_fetch_assets(self):
        with tarfile.open(self.root/'novaos-visual-update.tar.gz') as archive:
            archive.extractall(self.root,filter='data')
        payload=self.root/'novaos-visual-update'
        run=subprocess.run(['sha256sum','--check','--strict','SHA256SUMS'],cwd=payload,capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn('startplasma-x11',(payload/'mobile/guest-session.sh').read_text())
        self.assertIn('org.kde.PlasmaShell.evaluateScript',(payload/'themes/apply-plasma.sh').read_text())
        for style in ('compact','wide'):
            config=json.loads((payload/f'themes/fetch/{style}.jsonc').read_text())
            self.assertTrue(any(module['type']=='os' for module in config['modules']))
            self.assertTrue(any(module['type']=='memory' for module in config['modules']))

    def test_public_loader_checksum_matches_generated_script(self):
        script=self.root/'install-novaos-visual.sh'
        digest=Path(str(script)+'.sha256').read_text().split()[0]
        self.assertEqual(hashlib.sha256(script.read_bytes()).hexdigest(),digest)

    def test_corrupt_download_never_runs_installer(self):
        bindir=self.root/'bin';bindir.mkdir()
        curl=bindir/'curl'
        curl.write_text('#!/bin/bash\nwhile (($#)); do if [[ $1 == --output ]]; then printf invalid > "$2"; exit 0; fi; shift; done\nexit 1\n')
        curl.chmod(0o755)
        run=subprocess.run(['bash',str(self.root/'install-novaos-visual.sh'),'--download-only'],
                           env={**os.environ,'PATH':str(bindir)+os.pathsep+os.environ['PATH'],'TMPDIR':str(self.root)},
                           capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0)
        self.assertEqual(list(self.root.glob('novaos-visual.*')),[])


if __name__=='__main__':unittest.main()
