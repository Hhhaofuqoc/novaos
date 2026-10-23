"""Regress the real help-output stream that blocked Termux PRoot-Distro 5.10.2."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT/'mobile/check-proot.sh'
HELP = '''USAGE
  proot-distro install [OPTIONS] (IMAGE:TAG or URL or FILE)
OPTIONS
  -n, --name [NAME]          Set a custom name for the container.
PRoot-Distro version '5.10.2' by Termux (@sylirre).
'''


class MobilePreflightTests(unittest.TestCase):
    def run_check(self, text, *, stream=2, code=0):
        with tempfile.TemporaryDirectory(prefix='novaos-proot-preflight-') as temporary:
            directory = Path(temporary)
            command = directory/'proot-distro'
            command.write_text('#!/bin/bash\n'
                               '[[ $# == 2 && $1 == install && $2 == --help ]] || exit 99\n'
                               f"cat >&{stream} <<'NOVAOS_TEST_HELP'\n{text}\nNOVAOS_TEST_HELP\nexit {code}\n")
            command.chmod(0o755)
            return subprocess.run(['bash', str(CHECK)], capture_output=True, text=True,
                                  env={**os.environ, 'PATH': str(directory)+os.pathsep+os.environ['PATH']})

    def test_current_cli_help_on_stderr_is_accepted(self):
        result = self.run_check(HELP)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('Atualize', result.stderr)

    def test_help_on_stdout_is_also_accepted(self):
        result = self.run_check(HELP, stream=1)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_cli_is_rejected_before_installing_rootfs(self):
        result = self.run_check('proot-distro install --override-alias NAME debian')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('opção --name', result.stderr)

    def test_real_command_failure_is_not_reported_as_old_version(self):
        result = self.run_check('Permission denied', code=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Permission denied', result.stderr)
        self.assertNotIn('Atualize', result.stderr)


if __name__ == '__main__':
    unittest.main()
