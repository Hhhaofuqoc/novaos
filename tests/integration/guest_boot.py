#!/usr/bin/python3
"""Boot the installed Mobile guest session on native Debian, not Android/PRoot.

Run as the installed `nova` user under xvfb-run. Needs psutil and wmctrl.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import psutil

report = {"scope": "Installed Mobile guest script under native Debian/Xvfb; no PRoot/Android", "passed": False}
with tempfile.TemporaryDirectory(prefix="novaos-boot-") as directory:
    env = {**os.environ, "HOME": directory, "XDG_CONFIG_HOME": directory+"/.config",
           "XDG_CACHE_HOME": directory+"/.cache", "XDG_DATA_HOME": directory+"/.local/share"}
    with open(directory+"/session.log", "w") as log:
        process = subprocess.Popen(["/usr/local/libexec/novaos-mobile-session"], env=env,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic()+35
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise AssertionError("XFCE exited early")
                wm = subprocess.run(["wmctrl", "-m"], capture_output=True, text=True)
                if "Xfwm4" in wm.stdout and Path(directory+"/.config/novaos/appearance").exists():
                    break
                time.sleep(.5)
            else:
                raise AssertionError("Desktop/profile did not finish startup")
            children = psutil.Process(process.pid).children(recursive=True)
            agents = [p for p in children if "session-init" in " ".join(p.cmdline())]
            assert len(agents) == 1, "Expected one adaptive session agent"
            appearance = Path(directory+"/.config/novaos/appearance").read_text().strip()
            assert appearance == "lite dark", appearance
            report.update(passed=True, window_manager="Xfwm4", profile=appearance,
                          adaptive_agents=len(agents), child_processes=len(children))
        finally:
            try:
                children = psutil.Process(process.pid).children(recursive=True)
            except psutil.NoSuchProcess:
                children = []
            for child in reversed(children):
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            _, remaining = psutil.wait_procs(children, timeout=3)
            for child in remaining:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            report["log_tail"] = Path(directory+"/session.log").read_text(errors="replace")[-3000:]
            print(json.dumps(report, indent=2))
