"""Protect existing rootfs data while assigning a persistent Mobile container."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SELECT = ROOT/'mobile/select-container.py'
spec = importlib.util.spec_from_file_location('mobile_selection_runtime', ROOT/'mobile/novaos_mobile.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='novaos-selection-')
        self.root = Path(self.temp.name)
        self.bin = self.root/'bin'
        self.bin.mkdir()
        self.metadata = self.root/'installed.json'
        self.log = self.root/'calls.jsonl'
        proot = self.bin/'proot-distro'
        proot.write_text('#!'+sys.executable+'''\nimport json, os, sys
args=sys.argv[1:]
with open(os.environ['TEST_CALL_LOG'],'a') as log: log.write(json.dumps(args)+'\\n')
if args == ['list','--quiet']:
    if os.environ.get('TEST_LIST_ERROR') == '1':
        print('Cannot read inventory',file=sys.stderr);sys.exit(1)
    for name in json.loads(os.environ['TEST_INSTALLED']): print(name)
elif args[0] == 'login' and args[2:] == ['--','/usr/bin/test','-f','/etc/novaos-mobile-owner']:
    sys.exit(0 if args[1] in json.loads(os.environ['TEST_OWNED']) else 1)
else:
    print('Unexpected or mutating command',file=sys.stderr);sys.exit(99)
''')
        proot.chmod(0o755)

    def tearDown(self):
        self.temp.cleanup()

    def select(self, installed=(), owned=(), preferred=None, failure=False):
        if preferred is not None:
            self.metadata.write_text(json.dumps({'container':preferred,'edition':'mobile-lite'}))
        result = subprocess.run([sys.executable, str(SELECT), str(self.metadata)], text=True,
                                capture_output=True, env={**os.environ,
                                'PATH':str(self.bin)+os.pathsep+os.environ['PATH'],
                                'TEST_INSTALLED':json.dumps(installed), 'TEST_OWNED':json.dumps(owned),
                                'TEST_CALL_LOG':str(self.log),'TEST_LIST_ERROR':'1' if failure else '0'})
        calls=[json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertTrue(all(call[0] in ('list','login') for call in calls),calls)
        return result

    def test_unowned_novaos_is_preserved_and_lite_is_selected(self):
        result=self.select(['novaos'])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'novaos-lite')
        self.assertIn('novaos preservado',result.stderr)

    def test_multiple_collisions_select_an_unused_name(self):
        result=self.select(['novaos','novaos-lite','novaos-lite-2'])
        self.assertEqual(result.stdout.strip(),'novaos-lite-3',result.stderr)

    def test_owned_interrupted_install_is_reused(self):
        result=self.select(['novaos','novaos-lite'],['novaos-lite'])
        self.assertEqual(result.stdout.strip(),'novaos-lite',result.stderr)

    def test_saved_owned_name_takes_priority_over_free_default(self):
        result=self.select(['novaos-lite-10'],['novaos-lite-10'],preferred='novaos-lite-10')
        self.assertEqual(result.stdout.strip(),'novaos-lite-10',result.stderr)

    def test_legacy_installation_stays_on_its_existing_rootfs(self):
        result=self.select(['novaos'],['novaos'])
        self.assertEqual(result.stdout.strip(),'novaos',result.stderr)

    def test_inventory_failure_stops_without_selecting_a_container(self):
        result=self.select(failure=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(result.stdout,'')

    def test_invalid_saved_name_stops_without_falling_back(self):
        result=self.select(preferred='../another-rootfs')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(result.stdout,'')

    def test_runtime_backup_uses_saved_name(self):
        state=self.root/'state'
        state.mkdir()
        (state/'installed.json').write_text('{"container":"novaos-lite"}')
        app=runtime.Mobile(state,self.root/'prefix')
        target=self.root/'backup.tar.gz'
        def backup(command, **_kwargs):
            self.assertEqual(command,['proot-distro','backup','novaos-lite','--output',str(target)])
            target.write_bytes(b'fixture backup')
        with patch.object(runtime.subprocess,'run',side_effect=backup):
            app.backup(target)
        self.assertTrue(Path(str(target)+'.sha256').exists())

    def test_uninstall_requires_confirmation_for_the_selected_name(self):
        state=self.root/'state'
        state.mkdir()
        (state/'installed.json').write_text('{"container":"novaos-lite"}')
        app=runtime.Mobile(state,self.root/'prefix')
        with patch('builtins.input',return_value='EXCLUIR novaos'), patch.object(runtime.subprocess,'run') as run:
            with self.assertRaises(RuntimeError): app.uninstall()
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
