#!/usr/bin/python3
"""Check resolved GTK colors in focused and unfocused native windows.

Run inside an X11 display, e.g. xvfb-run -a /usr/bin/python3
 tests/integration/theme_contrast.py --report dist/validation/theme-contrast.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import warnings

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

ROOT = Path(__file__).resolve().parents[2]


def rgb(color):
    return [round(color.red * 255), round(color.green * 255), round(color.blue * 255)]


def validate():
    if Gdk.Screen.get_default() is None:
        raise RuntimeError('A real X11 display or Xvfb is required.')
    results = {}
    for name, background, foreground in (
        ('NovaOS-Dark', [16, 9, 28], [237, 230, 255]),
        ('NovaOS-Light', [243, 237, 252], [38, 18, 55]),
    ):
        provider = Gtk.CssProvider()
        errors = []
        provider.connect('parsing-error', lambda _provider, _section, error: errors.append(str(error)))
        provider.load_from_path(str(ROOT / 'themes' / name / 'gtk-3.0/gtk.css'))
        assert not errors, (name, errors)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        window = Gtk.Window()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        label = Gtk.Label(label='NovaMonitor • CPU 2% RAM 120 MiB')
        button = Gtk.Button(label='Gerenciar processos')
        box.pack_start(label, True, True, 0)
        box.pack_start(button, True, True, 0)
        window.add(box)
        window.show_all()
        while Gtk.events_pending():
            Gtk.main_iteration()
        colors = {}
        try:
            for state_name, state in (
                ('focused', Gtk.StateFlags.NORMAL), ('backdrop', Gtk.StateFlags.BACKDROP),
            ):
                for widget in (window, box, label, button, button.get_child()):
                    widget.set_state_flags(state, True)
                while Gtk.events_pending():
                    Gtk.main_iteration()
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', DeprecationWarning)
                    bg = rgb(window.get_style_context().get_background_color(state))
                fg = rgb(label.get_style_context().get_color(state))
                button_fg = rgb(button.get_child().get_style_context().get_color(state))
                assert bg == background, (name, state_name, 'background', bg, background)
                assert fg == foreground, (name, state_name, 'label', fg, foreground)
                assert button_fg == foreground, (name, state_name, 'button label', button_fg, foreground)
                colors[state_name] = {'background_rgb': bg, 'label_rgb': fg, 'button_label_rgb': button_fg}
            results[name] = colors
        finally:
            window.destroy()
            Gtk.StyleContext.remove_provider_for_screen(screen, provider)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    encoded = json.dumps(validate(), indent=2) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding='utf-8')
    print(encoded, end='')
