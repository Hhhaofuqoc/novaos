"""Small, atomic, per-user configuration; no daemon or network required."""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import tempfile

DEFAULTS = {"schema": 1, "profile": "auto", "theme": "dark", "power_save": False,
            "adaptive": True}

def config_dir():
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home()/".config"))/"novaos"

def asset_root():
    override = os.environ.get("NOVAOS_ASSETS")
    if override:
        return Path(override)
    installed = Path("/usr/share/novaos")
    return installed if installed.exists() else Path(__file__).resolve().parents[2]

def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".novaos-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def read_config(path=None):
    path = Path(path) if path else config_dir()/"settings.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    result = dict(DEFAULTS)
    if data.get("profile") in ("auto", "lite", "balanced", "ultra"):
        result["profile"] = data["profile"]
    if data.get("theme") in ("dark", "light"):
        result["theme"] = data["theme"]
    for key in ("power_save", "adaptive"):
        if isinstance(data.get(key), bool):
            result[key] = data[key]
    return result

def update_config(changes, path=None):
    path = Path(path) if path else config_dir()/"settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with (path.parent/".settings.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = read_config(path)
        data.update(changes)
        if data["profile"] not in ("auto", "lite", "balanced", "ultra"):
            raise ValueError("Invalid profile")
        if data["theme"] not in ("dark", "light"):
            raise ValueError("Invalid theme")
        atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2)+"\n")
    return data

def choose_profile(total_bytes, *, mobile=False):
    # These are effect budgets, not hardware compatibility guarantees.
    if mobile or total_bytes < 4 * 1024**3:
        return "lite"
    return "balanced" if total_bytes < 7 * 1024**3 else "ultra"

def effective_profile(settings, total_bytes, *, mobile=False, available_bytes=None,
                      battery_percent=None, plugged=None):
    base = settings["profile"]
    if base == "auto":
        base = choose_profile(total_bytes, mobile=mobile)
    if settings["power_save"]:
        return "lite"
    if settings["adaptive"]:
        if available_bytes is not None and available_bytes < 512 * 1024**2:
            return "lite"
        if battery_percent is not None and battery_percent <= 20 and plugged is False:
            return "lite"
    return base
