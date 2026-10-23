"""Observable Linux metrics, with unavailable readings represented by None."""
from __future__ import annotations
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time
from .config import config_dir, asset_root, read_config, effective_profile

def is_mobile():
    if os.environ.get("NOVAOS_MOBILE") == "1" or Path("/etc/novaos/mobile").exists():
        return True
    try:
        return Path("/etc/novaos-edition").read_text().strip() == "mobile-lite"
    except OSError:
        return False

def snapshot():
    import psutil
    errors = []
    def safe(label, callback, default=None):
        try:
            return callback()
        except (OSError, RuntimeError, ValueError, psutil.Error) as error:
            errors.append(f"{label}: {error}")
            return default
    mem = safe("memory", psutil.virtual_memory)
    disk = safe("storage", lambda: psutil.disk_usage(str(Path.home())))
    battery = safe("battery", psutil.sensors_battery)
    temperatures = safe("temperature", psutil.sensors_temperatures, {}) or {}
    net = safe("network", psutil.net_io_counters)
    boot = safe("uptime", psutil.boot_time)
    try:
        distro = platform.freedesktop_os_release().get("PRETTY_NAME", "Linux")
    except OSError:
        distro = "Linux"
    return {"timestamp": time.time(), "cpu_percent": safe("CPU", psutil.cpu_percent),
            "memory_total": mem.total if mem else None,
            "memory_available": mem.available if mem else None,
            "memory_used": mem.total-mem.available if mem else None,
            "disk_total": disk.total if disk else None,
            "disk_free": disk.free if disk else None,
            "battery_percent": battery.percent if battery else None,
            "plugged": battery.power_plugged if battery else None,
            "network_sent": net.bytes_sent if net else None,
            "network_received": net.bytes_recv if net else None,
            "temperatures": {k: [t.current for t in v] for k,v in temperatures.items()},
            "uptime": time.time()-boot if boot else None,
            "kernel": platform.release(), "architecture": platform.machine(),
            "distribution": distro, "desktop": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
            "mobile": is_mobile(), "errors": errors}

def current_profile(settings=None, metrics=None):
    settings = settings or read_config()
    metrics = metrics or snapshot()
    return effective_profile(settings, metrics.get("memory_total") or 0,
                             mobile=metrics.get("mobile", is_mobile()),
                             available_bytes=metrics.get("memory_available"),
                             battery_percent=metrics.get("battery_percent"),
                             plugged=metrics.get("plugged"))

def apply_appearance(settings=None, profile=None):
    settings = settings or read_config()
    if not os.environ.get("DISPLAY") or not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        return "Salvo. A aparência será aplicada na próxima sessão gráfica."
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "XFCE").upper()
    if "KDE" in desktop:
        return "Salvo. Integração visual Plasma ainda não implementada; use a sessão XFCE."
    script = asset_root()/"themes"/"apply-xfce.sh"
    result = subprocess.run(["bash", str(script), profile or current_profile(settings), settings["theme"]],
                            capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Falha ao aplicar tema")[-2000:])
    return "Tema e perfil aplicados."

APPS = {"files": ["thunar"], "terminal": ["xfce4-terminal"], "browser": ["firefox-esr"],
        "editor": ["mousepad"], "processes": ["xfce4-taskmanager"],
        "display": ["xfce4-display-settings"], "keyboard": ["xfce4-keyboard-settings"],
        "mouse": ["xfce4-mouse-settings"], "desktop-settings": ["xfce4-settings-manager"]}

def launch(command, arguments=()):
    args = APPS.get(command, ["novaos", command]) + list(arguments)
    if not shutil.which(args[0]):
        raise RuntimeError(f"Aplicativo não instalado: {args[0]}")
    return subprocess.Popen(args, start_new_session=True)

def package_terminal(action, package=None):
    import re
    if action not in ("install", "update", "upgrade"):
        raise ValueError("Invalid package action")
    args = ["/usr/lib/novaos/apt-helper", action]
    if action == "install":
        if not package or not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9]+)?", package):
            raise ValueError("Nome de pacote inválido")
        args.append(package)
    if os.geteuid() != 0:
        args.insert(0, "sudo" if is_mobile() else "pkexec")
    if not shutil.which(args[0]):
        raise RuntimeError(f"Instale {args[0]} ou use o terminal administrativo.")
    return launch("terminal", ["--disable-server", "--hold", "--title=NovaStore", "--execute", *args])

def session(once=False):
    """One small, single-instance polling process; no render loop and no app preloading."""
    import fcntl
    state = config_dir()
    state.mkdir(parents=True, exist_ok=True)
    with (state/"session.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        last = None
        while True:
            settings = read_config()
            profile = current_profile(settings)
            target = profile, settings["theme"]
            if target != last:
                try:
                    apply_appearance(settings, profile)
                    last = target
                except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
                    print(f"NovaOS: {error}", flush=True)
                    if once:
                        return 1
            if once:
                return 0
            time.sleep(20)
