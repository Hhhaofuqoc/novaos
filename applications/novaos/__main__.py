"""CLI keeps graphical libraries lazy: diagnostics and configuration work offline."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from . import __version__

def main(argv=None):
    parser = argparse.ArgumentParser(prog="novaos", description="NovaOS — Your universe. Your system.")
    parser.add_argument("--version", action="version", version=__version__)
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("welcome", "settings", "monitor", "notes", "store", "updater",
                    "files", "terminal", "browser", "editor", "processes"):
        subs.add_parser(command)
    for command, choices in (("profile", ("auto", "lite", "balanced", "ultra")), ("theme", ("dark", "light"))):
        subs.add_parser(command).add_argument("value", choices=choices, nargs="?")
    subs.add_parser("diagnostics")
    subs.add_parser("session-init").add_argument("--once", action="store_true")
    # Keep GApplication's player control options intact.
    args_list = list(sys.argv[1:] if argv is None else argv)
    if args_list and args_list[0] == "fetch":
        try:
            return subprocess.call(["novafetch", *args_list[1:]])
        except OSError as error:
            print(f"NovaOS: {error}", file=sys.stderr)
            return 1
    if args_list and args_list[0] == "music":
        from .music import main as music_main
        return music_main(args_list[1:])
    subs.add_parser("music", help="Player local; novaos music --help")
    subs.add_parser("fetch", help="Informações reais com identidade NovaOS")
    args = parser.parse_args(args_list)
    from . import system
    try:
        if args.command in ("profile", "theme"):
            from .config import read_config, update_config
            if args.value:
                settings = update_config({args.command: args.value})
                print(system.apply_appearance(settings))
            else:
                print(read_config()[args.command])
        elif args.command == "diagnostics":
            print(json.dumps(system.snapshot(), indent=2))
        elif args.command == "session-init":
            return system.session(args.once)
        elif args.command in system.APPS:
            system.launch(args.command)
        else:
            from .ui import main as gui_main
            return gui_main(args.command)
    except (OSError, RuntimeError, ValueError, ImportError) as error:
        print(f"NovaOS: {error}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
