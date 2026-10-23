#!/usr/bin/env python3
"""NovaOS Termux session supervisor. No network listeners and no Android root."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import threading
import time

ALIAS = "novaos"
MAX_LOG = 2 * 1024 * 1024


def process_identity(pid):
    """Linux PID + start tick identity; refuses recycled PIDs and zombies."""
    try:
        raw = Path(f"/proc/{int(pid)}/stat").read_text()
        fields = raw[raw.rfind(")") + 2:].split()
        if fields[0] == "Z":
            return None
        return {"pid": int(pid), "start": fields[19]}
    except (OSError, ValueError, IndexError):
        return None


def alive(identity):
    return bool(identity and process_identity(identity.get("pid", -1)) == identity)


def terminate_tree(identity):
    """Only signal the verified child and its descendants, never name matches."""
    if not alive(identity):
        return
    pending = {identity["pid"]}
    identities = [identity]
    # Snapshot descendants while the parent is still alive. PID identity is
    # rechecked immediately before every signal, including forced cleanup.
    for _ in range(16):
        found = set()
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit() or int(entry.name) in pending:
                continue
            try:
                raw = (entry / "stat").read_text()
                fields = raw[raw.rfind(")") + 2:].split()
                if int(fields[1]) in pending:
                    found.add(int(entry.name))
                    ident = process_identity(int(entry.name))
                    if ident:
                        identities.append(ident)
            except (OSError, ValueError, IndexError):
                continue
        if not found:
            break
        pending.update(found)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for item in reversed(identities):
            if alive(item):
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.kill(item["pid"], sig)
        if sig == signal.SIGTERM:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and any(alive(x) for x in identities):
                time.sleep(0.1)


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_backup(path):
    """Do not allow a NovaOS restore to overwrite another PRoot container."""
    count = 0
    with tarfile.open(path, "r:*") as archive:
        for member in archive:
            parts = Path(member.name).parts
            if not parts or member.name.startswith("/") or ".." in parts:
                raise ValueError("Caminho inválido no backup")
            if parts[0] == "installed-rootfs":
                valid = len(parts) > 1 and parts[1] == ALIAS
            else:
                valid = parts[0] == ALIAS
            if not valid:
                raise ValueError("O backup contém outro ambiente além de novaos")
            if member.isdev() or member.isfifo():
                raise ValueError("Backup contém arquivo especial não permitido")
            if member.islnk():
                target = Path(member.linkname).parts
                if not target or member.linkname.startswith("/") or ".." in target:
                    raise ValueError("Hard link inválido no backup")
                if target[0] != parts[0]:
                    raise ValueError("Hard link aponta para fora do backup")
            count += 1
    if not count:
        raise ValueError("Backup vazio")


class Mobile:
    def __init__(self, state=None, prefix=None):
        self.prefix = Path(prefix or os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
        self.state = Path(state or Path.home() / ".local/state/novaos-mobile")
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.state.chmod(0o700)
        self.runtime = self.prefix / "tmp" / f"novaos-mobile-{os.getuid()}"
        self.file = self.state / "session.json"
        self.log_lock = threading.Lock()

    @contextlib.contextmanager
    def lock(self):
        with (self.state / "control.lock").open("w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield

    def read(self):
        try:
            data = json.loads(self.file.read_text())
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def write(self, data):
        path = self.file.with_suffix(".tmp")
        path.write_text(json.dumps(data, indent=2) + "\n")
        path.chmod(0o600)
        path.replace(self.file)

    def is_running(self):
        data = self.read()
        return alive(data.get("supervisor")) and data.get("phase") == "running"

    def require_termux(self):
        if not str(self.prefix).startswith("/data/") or not shutil.which("termux-x11"):
            raise RuntimeError("Execute no Termux após mobile/install-termux.sh")

    def log(self, message):
        with self.log_lock:
            path = self.state / "session.log"
            if path.exists() and path.stat().st_size > MAX_LOG:
                path.replace(self.state / "session.previous.log")
            with path.open("a") as handle:
                handle.write(message[:8192])
                if not message.endswith("\n"):
                    handle.write("\n")

    def stream_log(self, pipe, label):
        try:
            for line in iter(pipe.readline, b""):
                self.log(f"[{label}] {line.decode('utf-8', errors='replace')}")
        finally:
            pipe.close()

    def open_activity(self):
        am = shutil.which("am") or "/system/bin/am"
        subprocess.run([am, "start", "--user", "0", "-n", "com.termux.x11/com.termux.x11.MainActivity"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    def start(self, display=1, legacy=False):
        self.require_termux()
        with self.lock():
            data = self.read()
            if alive(data.get("supervisor")):
                print("Sessão já ativa; abrindo Termux:X11.")
                self.open_activity()
                return
            # A killed supervisor may leave children. Clean only known identities.
            for ident in data.get("children", {}).values():
                terminate_tree(ident)
            self.clear_stale_display(data)
            command = [sys.executable, str(Path(__file__).resolve()), "_serve", "--display", str(display)]
            if legacy:
                command.append("--legacy-drawing")
            self.write({"phase": "starting", "children": {}})
            with (self.state / "supervisor.log").open("w") as log:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                           start_new_session=True, close_fds=True)
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                data = self.read()
                if data.get("phase") == "running" and alive(data.get("supervisor")):
                    print("NovaOS iniciado. Abra o aplicativo Termux:X11; gire o aparelho para paisagem.")
                    self.open_activity()
                    return
                if process.poll() is not None or data.get("phase") == "failed":
                    raise RuntimeError(f"Falha ao iniciar. Veja novaos-mobile logs. {data.get('error', '')}")
                time.sleep(0.2)
            # No orphan start attempt on timeout.
            terminate_tree(process_identity(process.pid))
            raise RuntimeError("Tempo limite de inicialização; execute novaos-mobile logs")

    def clear_stale_display(self, data):
        """Recover only a refused socket recorded as belonging to our previous X server."""
        identity = data.get("children", {}).get("x11")
        display = data.get("display")
        if not identity or alive(identity) or not isinstance(display, int) or not 1 <= display <= 99:
            return
        path = self.prefix / "tmp/.X11-unix" / f"X{display}"
        try:
            if not path.is_socket() or path.stat().st_uid != os.getuid():
                return
            with socket.socket(socket.AF_UNIX) as probe:
                probe.settimeout(.5)
                try:
                    probe.connect(str(path))
                    return  # A live server owns it, even if its PID is not in our registry.
                except ConnectionRefusedError:
                    pass
            path.unlink()
            lock = self.prefix / "tmp" / f".X{display}-lock"
            if lock.exists() and lock.stat().st_uid == os.getuid() and lock.read_text().strip() == str(identity["pid"]):
                lock.unlink()
        except (OSError, ValueError):
            return

    def serve(self, display, legacy):
        stop_event = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stop_event.set())
        signal.signal(signal.SIGINT, lambda *_: stop_event.set())
        data = {"phase": "starting", "supervisor": process_identity(os.getpid()),
                "children": {}, "display": display, "started": time.time()}
        self.write(data)
        children = []

        def launch(label, command, env=None):
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, start_new_session=True, env=env)
            children.append(process)
            data["children"][label] = process_identity(process.pid)
            self.write(data)
            threading.Thread(target=self.stream_log, args=(process.stdout, label), daemon=True).start()
            return process

        def await_socket(path, process, seconds=15):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                if stop_event.is_set() or process.poll() is not None:
                    raise RuntimeError(f"Serviço não iniciou: {path}")
                if path.is_socket():
                    return
                stop_event.wait(0.1)
            raise RuntimeError(f"Socket não apareceu: {path}")

        try:
            self.runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.runtime.chmod(0o700)
            x_socket = self.prefix / "tmp/.X11-unix" / f"X{display}"
            if x_socket.exists():
                raise RuntimeError(f"Display :{display} ocupado; encerre a sessão X11 anterior ou use --display 2")
            auth = self.runtime / "Xauthority"
            auth.touch(mode=0o600)
            subprocess.run(["xauth", "-f", str(auth), "add", f":{display}", "MIT-MAGIC-COOKIE-1", secrets.token_hex(16)], check=True)
            records = subprocess.check_output(["xauth", "-f", str(auth), "nlist"])
            # Wildcard address family supports PRoot's different hostname.
            records = b"\n".join(b"ffff" + line[4:] for line in records.splitlines()) + b"\n"
            subprocess.run(["xauth", "-f", str(auth), "nmerge", "-"], input=records, check=True)
            pulse_dir = self.runtime / "pulse"
            pulse_dir.mkdir(exist_ok=True, mode=0o700)
            pulse_socket = pulse_dir / "native"
            # This socket belongs only to this private runtime directory.
            if pulse_socket.exists():
                pulse_socket.unlink()
            pulse = launch("pulse", ["pulseaudio", "--daemonize=no", "--use-pid-file=no", "--exit-idle-time=-1",
                             "--disable-shm=true", "-n", "--load=module-sles-sink",
                             f"--load=module-native-protocol-unix socket={pulse_socket} auth-anonymous=1"])
            await_socket(pulse_socket, pulse)
            command = ["termux-x11", f":{display}", "-nolisten", "tcp", "-auth", str(auth)]
            if legacy:
                command.append("-legacy-drawing")
            x11 = launch("x11", command)
            await_socket(x_socket, x11)
            guest_runtime = f"/tmp/{self.runtime.name}"
            guest = launch("desktop", ["proot-distro", "login", ALIAS, "--user", "nova", "--isolated", "--shared-tmp", "--",
                "/usr/bin/env", f"DISPLAY=:{display}", f"XAUTHORITY={guest_runtime}/Xauthority",
                f"PULSE_SERVER=unix:{guest_runtime}/pulse/native", "NOVAOS_MOBILE=1", "/usr/local/libexec/novaos-mobile-session"])
            # An immediate missing desktop/permission error should not appear as success.
            if stop_event.wait(2) or guest.poll() is not None:
                raise RuntimeError("A sessão XFCE terminou durante a inicialização")
            data["phase"] = "running"
            self.write(data)
            while not stop_event.wait(1):
                if any(process.poll() is not None for process in children):
                    break
            data["phase"] = "stopping"
        except Exception as error:
            data["phase"] = "failed"
            data["error"] = str(error)
            self.log(str(error))
        finally:
            for identity in reversed(list(data["children"].values())):
                terminate_tree(identity)
            for process in children:
                with contextlib.suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=1)
            if data["phase"] != "failed":
                data["phase"] = "stopped"
            self.write(data)

    def stop(self):
        with self.lock():
            data = self.read()
            identity = data.get("supervisor")
            if alive(identity):
                os.kill(identity["pid"], signal.SIGTERM)
                deadline = time.monotonic() + 15
                while alive(identity) and time.monotonic() < deadline:
                    time.sleep(0.1)
                if alive(identity):
                    terminate_tree(identity)
            for ident in data.get("children", {}).values():
                terminate_tree(ident)
            data["phase"] = "stopped"
            self.write(data)
        print("Sessão encerrada; seus arquivos permanecem em /home/nova.")

    def require_stopped(self):
        data = self.read()
        if alive(data.get("supervisor")) or any(alive(x) for x in data.get("children", {}).values()):
            raise RuntimeError("Encerre primeiro: novaos-mobile stop")

    def backup(self, target):
        self.require_stopped()
        target = Path(target).expanduser().resolve()
        if target.exists() or Path(str(target) + ".sha256").exists():
            raise RuntimeError("O destino já existe; não será sobrescrito")
        if target.suffix not in ("gz", ".gz", ".xz", ".tar"):
            raise RuntimeError("Use um nome terminado em .tar.gz, .tar.xz ou .tar")
        subprocess.run(["proot-distro", "backup", ALIAS, "--output", str(target)], check=True)
        checksum = digest_file(target)
        Path(str(target) + ".sha256").write_text(f"{checksum}  {target.name}\n")
        print(f"Backup: {target}\nSHA256: {checksum}")

    def restore(self, source):
        self.require_stopped()
        source = Path(source).expanduser().resolve()
        checksum = Path(str(source) + ".sha256").read_text().split()[0]
        if len(checksum) != 64 or digest_file(source) != checksum:
            raise RuntimeError("Checksum do backup inválido")
        validate_backup(source)
        print("A restauração substitui todo o ambiente novaos, incluindo /home/nova.")
        if input('Digite RESTAURAR novaos para continuar: ') != "RESTAURAR novaos":
            raise RuntimeError("Restauração cancelada")
        subprocess.run(["proot-distro", "restore", str(source)], check=True)
        print("Backup restaurado. Execute novaos-mobile start.")

    def uninstall(self):
        self.require_stopped()
        print("Isto apaga o Debian NovaOS e todos os arquivos de /home/nova. Faça backup antes.")
        if input('Digite EXCLUIR novaos para continuar: ') != "EXCLUIR novaos":
            raise RuntimeError("Desinstalação cancelada")
        subprocess.run(["proot-distro", "remove", ALIAS], check=True)
        for path in (self.prefix / "bin/novaos-mobile", Path.home() / ".shortcuts/NovaOS"):
            with contextlib.suppress(FileNotFoundError):
                path.unlink()
        print("Ambiente removido. Termux, Termux:X11, fontes e backups foram preservados.")

    def doctor(self):
        report = {"architecture": os.uname().machine, "prefix": str(self.prefix),
                  "free_gib": round(shutil.disk_usage(self.prefix).free / 1024**3, 2),
                  "state": self.read(), "tools": {x: bool(shutil.which(x)) for x in
                  ("proot-distro", "termux-x11", "pulseaudio", "xauth")}}
        print(json.dumps(report, indent=2, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description="NovaOS Mobile Lite — controle da sessão no Termux")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("start", "_serve"):
        item = sub.add_parser(command)
        item.add_argument("--display", type=int, choices=range(1, 100), default=1, metavar="1..99")
        item.add_argument("--legacy-drawing", action="store_true")
    for command in ("stop", "restart", "doctor", "logs", "uninstall"):
        sub.add_parser(command)
    item = sub.add_parser("status")
    item.add_argument("--quiet", action="store_true")
    for command in ("backup", "restore"):
        item = sub.add_parser(command)
        item.add_argument("archive")
    item = sub.add_parser("shell")
    item.add_argument("--root", action="store_true", help="root emulado apenas dentro do Debian")
    args = parser.parse_args(argv)
    app = Mobile()
    try:
        if args.command == "start":
            app.start(args.display, args.legacy_drawing)
        elif args.command == "_serve":
            app.serve(args.display, args.legacy_drawing)
        elif args.command == "stop":
            app.stop()
        elif args.command == "restart":
            app.stop()
            app.start()
        elif args.command == "status":
            running = app.is_running()
            if not args.quiet:
                print("NovaOS em execução" if running else "NovaOS parado; execute novaos-mobile start")
            return 0 if running else 1
        elif args.command == "logs":
            for name in ("session.log", "supervisor.log"):
                path = app.state / name
                if path.exists():
                    print(f"--- {name} ---\n" + path.read_text(errors="replace")[-18000:])
        elif args.command == "doctor":
            app.doctor()
        elif args.command == "backup":
            app.backup(args.archive)
        elif args.command == "restore":
            app.restore(args.archive)
        elif args.command == "uninstall":
            app.uninstall()
        elif args.command == "shell":
            subprocess.run(["proot-distro", "login", ALIAS, "--user", "root" if args.root else "nova"], check=True)
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError, EOFError) as error:
        print(f"NovaOS: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
