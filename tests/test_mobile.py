"""Host logic tests with real subprocesses + mocked Android/X11/PRoot services.

These tests do NOT validate Termux, Android graphics, audio, or a real rootfs.
"""
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "mobile/novaos_mobile.py"
spec = importlib.util.spec_from_file_location("novaos_mobile", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IdentityTests(unittest.TestCase):
    def test_current_process_identity_and_reused_pid_rejection(self):
        identity = module.process_identity(os.getpid())
        self.assertTrue(module.alive(identity))
        self.assertFalse(module.alive({"pid": os.getpid(), "start": "0"}))
        self.assertFalse(module.alive(None))

    def test_termination_refuses_wrong_identity(self):
        with patch.object(module.os, "kill") as kill:
            module.terminate_tree({"pid": os.getpid(), "start": "invalid"})
        kill.assert_not_called()

    def test_stale_x_socket_cleanup_only_for_recorded_dead_server(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = module.Mobile(root/"state", root/"prefix")
            socket_dir = app.prefix/"tmp/.X11-unix"
            socket_dir.mkdir(parents=True)
            path = socket_dir/"X1"
            sock = socket.socket(socket.AF_UNIX)
            sock.bind(str(path))
            sock.close()
            data = {"display": 1, "children": {"x11": {"pid": 99999999, "start": "0"}}}
            app.clear_stale_display(data)
            self.assertFalse(path.exists())
            with socket.socket(socket.AF_UNIX) as live:
                live.bind(str(path))
                live.listen()
                app.clear_stale_display(data)
                self.assertTrue(path.exists())


class BackupTests(unittest.TestCase):
    def archive(self, root, names):
        path = root / "backup.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            for name in names:
                item = tarfile.TarInfo(name)
                item.size = 4
                archive.addfile(item, io.BytesIO(b"test"))
        return path

    def test_valid_backup(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.archive(Path(root), ["novaos/rootfs/home/nova/note.txt"])
            module.validate_backup(path)
            self.assertEqual(len(module.digest_file(path)), 64)

    def test_other_container_and_traversal_rejected(self):
        for name in ("ubuntu/rootfs/file", "novaos/../../file", "/novaos/file"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                path = self.archive(Path(root), [name])
                with self.assertRaises(ValueError):
                    module.validate_backup(path)

    def test_empty_backup_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.archive(Path(root), [])
            with self.assertRaises(ValueError):
                module.validate_backup(path)

    def test_restore_cancelled_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path = self.archive(root, ["novaos/rootfs/home/nova/note.txt"])
            Path(str(path) + ".sha256").write_text(module.digest_file(path) + "  backup.tar.gz\n")
            app = module.Mobile(root / "state", root / "prefix")
            with patch("builtins.input", return_value="no"), patch.object(module.subprocess, "run") as run:
                with self.assertRaises(RuntimeError):
                    app.restore(path)
            run.assert_not_called()

    def test_checksum_failure_never_extracts(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path = self.archive(root, ["novaos/rootfs/file"])
            Path(str(path) + ".sha256").write_text("0" * 64 + "  backup.tar.gz\n")
            app = module.Mobile(root / "state", root / "prefix")
            with patch.object(module.subprocess, "run") as run:
                with self.assertRaises(RuntimeError):
                    app.restore(path)
            run.assert_not_called()

    def test_uninstall_requires_exact_confirmation(self):
        with tempfile.TemporaryDirectory() as root:
            app = module.Mobile(Path(root) / "state", Path(root) / "prefix")
            with patch("builtins.input", return_value="yes"), patch.object(module.subprocess, "run") as run:
                with self.assertRaises(RuntimeError):
                    app.uninstall()
            run.assert_not_called()


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prefix = self.root / "prefix"
        (self.prefix / "tmp/.X11-unix").mkdir(parents=True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        fake = '''#!PYTHON
import os,sys,socket,time
from pathlib import Path
name=Path(sys.argv[0]).name
if name=='xauth':
    if 'nlist' in sys.argv: print('0100 0000 0001 31 0012 4d49542d4d414749432d434f4f4b49452d31 0010 0123456789abcdef0123456789abcdef')
    sys.exit(0)
if name=='termux-x11':
    destination=Path(os.environ['TEST_PREFIX'])/'tmp/.X11-unix'/('X'+sys.argv[1][1:])
elif name=='pulseaudio':
    destination=next(x.split('socket=')[1].split()[0] for x in sys.argv if 'socket=' in x)
else: destination=None
if destination:
    sock=socket.socket(socket.AF_UNIX); sock.bind(str(destination)); sock.listen()
while True: time.sleep(1)
'''.replace("PYTHON", sys.executable, 1)
        for name in ("pulseaudio", "xauth", "termux-x11", "proot-distro"):
            path = self.bin / name
            path.write_text(fake)
            path.chmod(0o755)
        self.app = module.Mobile(self.root / "state", self.prefix)
        self.process = None

    def tearDown(self):
        self.app.stop()
        if self.process:
            self.process.wait(timeout=8)
        self.temp.cleanup()

    def start_mock_services(self):
        code = ("import importlib.util;from pathlib import Path;"
                f"s=importlib.util.spec_from_file_location('mobile',{str(SOURCE)!r});"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                f"m.Mobile({str(self.app.state)!r},{str(self.prefix)!r}).serve(1,False)")
        env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"], TEST_PREFIX=str(self.prefix))
        self.process = subprocess.Popen([sys.executable, "-c", code], env=env, start_new_session=True,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if self.app.is_running():
                return
            if self.process.poll() is not None:
                self.fail("Mock supervisor exited: " + str(self.app.read()))
            time.sleep(0.1)
        self.fail("Mock startup timeout: " + str(self.app.read()))

    def test_start_stop_real_process_tracking(self):
        self.start_mock_services()
        children = self.app.read()["children"]
        self.assertEqual(set(children), {"pulse", "x11", "desktop"})
        self.assertTrue(all(module.alive(x) for x in children.values()))
        self.app.stop()
        self.assertFalse(self.app.is_running())
        self.assertTrue(all(not module.alive(x) for x in children.values()))

    def test_supervisor_crash_recovery_preserves_unrelated_process(self):
        self.start_mock_services()
        children = self.app.read()["children"]
        unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"])
        try:
            self.process.kill()
            self.process.wait(timeout=3)
            self.assertFalse(self.app.is_running())
            self.app.stop()
            self.assertTrue(all(not module.alive(x) for x in children.values()))
            self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=3)

    def test_logs_are_bounded(self):
        self.app.log("x" * (module.MAX_LOG + 1))
        # Each record is capped; rotation also handles larger previous logs.
        (self.app.state / "session.log").write_text("x" * (module.MAX_LOG + 1))
        self.app.log("next session")
        self.assertTrue((self.app.state / "session.previous.log").exists())
        self.assertLess((self.app.state / "session.log").stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
