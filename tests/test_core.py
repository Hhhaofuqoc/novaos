import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"applications"))
from novaos.config import (atomic_write, read_config, update_config, choose_profile,
                           effective_profile, DEFAULTS)
from novaos import system

loader = importlib.machinery.SourceFileLoader("apt_helper", str(ROOT/"installers"/"apt-helper"))
spec = importlib.util.spec_from_loader(loader.name, loader)
helper = importlib.util.module_from_spec(spec)
loader.exec_module(helper)

class CoreTests(unittest.TestCase):
    def test_mobile_always_starts_lite(self):
        self.assertEqual(choose_profile(16*1024**3, mobile=True), "lite")
        self.assertEqual(choose_profile(3*1024**3), "lite")
        self.assertEqual(choose_profile(6*1024**3), "balanced")
        self.assertEqual(choose_profile(8*1024**3), "ultra")

    def test_adaptive_pressure_and_battery(self):
        settings = {**DEFAULTS, "profile": "ultra"}
        self.assertEqual(effective_profile(settings, 8*1024**3, available_bytes=200*1024**2), "lite")
        self.assertEqual(effective_profile(settings, 8*1024**3, battery_percent=10, plugged=False), "lite")
        self.assertEqual(effective_profile(settings, 8*1024**3, battery_percent=10, plugged=True), "ultra")
        self.assertEqual(effective_profile({**settings, "adaptive": False}, 8*1024**3,
                                          available_bytes=200*1024**2), "ultra")

    def test_manual_saver_overrides_disabled_adaptation(self):
        settings = {**DEFAULTS, "profile": "ultra", "adaptive": False, "power_save": True}
        self.assertEqual(effective_profile(settings, 8*1024**3), "lite")

    def test_config_survives_updates_and_invalid_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"settings.json"
            update_config({"theme": "light"}, path)
            update_config({"profile": "lite"}, path)
            self.assertEqual(read_config(path)["theme"], "light")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            path.write_text('{"profile": "garbage", "adaptive": "false"}')
            self.assertEqual(read_config(path), DEFAULTS)
            path.write_text("not-json")
            self.assertEqual(read_config(path), DEFAULTS)

    def test_failed_atomic_replace_preserves_previous_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"notes.txt"
            atomic_write(path, "existing note")
            with patch("novaos.config.os.replace", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    atomic_write(path, "new note")
            self.assertEqual(path.read_text(), "existing note")
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_apt_helper_only_allows_package_operations(self):
        self.assertEqual(helper.arguments(["install", "gimp"]), ["/usr/bin/apt-get", "install", "--", "gimp"])
        self.assertEqual(helper.arguments(["upgrade"]), ["/usr/bin/apt-get", "upgrade"])
        for args in (["install", "-oAPT::Update::Pre-Invoke::=evil"], ["install", "./evil.deb"],
                     ["install", "a;id"], ["remove", "bash"], ["update", "--yes"], [],
                     ["install", "gimp", "-y"], ["install", "$(id)"]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                helper.arguments(args)

    def test_package_launch_never_invokes_shell(self):
        with patch("novaos.system.os.geteuid", return_value=1000), \
             patch("novaos.system.is_mobile", return_value=True), \
             patch("novaos.system.shutil.which", return_value="/usr/bin/sudo"), \
             patch("novaos.system.launch") as launch:
            system.package_terminal("install", "gimp")
            args = launch.call_args[0][1]
            self.assertIn("sudo", args)
            self.assertEqual(args[-3:], ["/usr/lib/novaos/apt-helper", "install", "gimp"])

    def test_headless_cli_preserves_profile_without_gtk(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, "PYTHONPATH": str(ROOT/"applications"), "XDG_CONFIG_HOME": directory}
            env.pop("DISPLAY", None)
            run = subprocess.run([sys.executable, "-m", "novaos", "profile", "lite"], env=env,
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads((Path(directory)/"novaos/settings.json").read_text())["profile"], "lite")

if __name__ == "__main__":
    unittest.main()
