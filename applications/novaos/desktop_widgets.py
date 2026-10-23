"""Native desktop cards: measured host metrics and controls for the real player."""
from __future__ import annotations

from collections import deque
import json
import os
from pathlib import Path
import time

import psutil


def playback_path():
    return Path(os.environ.get('XDG_RUNTIME_DIR', str(Path.home()/'.cache')))/'novaos'/'playback.json'


def read_playback(path=None):
    """Discard stale PID identities; never present a stopped player as playing."""
    try:
        data = json.loads(Path(path or playback_path()).read_text())
        if not isinstance(data, dict):
            return {}
        process = psutil.Process(int(data['pid']))
        if abs(process.create_time()-float(data['created'])) > .01 or process.status() == psutil.STATUS_ZOMBIE:
            return {}
        return data
    except (OSError, ValueError, KeyError, TypeError, psutil.Error):
        return {}


def rate(current, previous, elapsed):
    # Counter resets and the first observation do not imply negative bandwidth.
    if previous is None or elapsed <= 0 or current < previous:
        return 0.0
    return (current-previous)/elapsed


def size(value):
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if abs(value) < 1024 or unit == 'TiB':
            return f'{value:.1f} {unit}'
        value /= 1024


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description='NovaOS native desktop widgets')
    parser.add_argument('--quit', action='store_true')
    args = parser.parse_args(argv)
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gdk, Gio, GLib
    from .config import asset_root

    class Widgets(Gtk.Application):
        def __init__(self):
            super().__init__(application_id='org.novaos.DesktopWidgets',
                             flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
            self.window = None
            self.timer = 0
            self.history = deque([0.0]*45, maxlen=45)
            self.network = None
            self.network_time = time.monotonic()
            self.began = time.monotonic()

        def do_command_line(self, command):
            if '--quit' in command.get_arguments():
                self.quit()
            else:
                self.activate()
            return 0

        def do_activate(self):
            if self.window:
                return
            self.window = Gtk.ApplicationWindow(application=self, title='NovaOS Desktop Widgets')
            self.window.set_wmclass('novaos-widgets', 'NovaOSWidgets')
            self.window.set_decorated(False)
            self.window.set_resizable(False)
            self.window.set_type_hint(Gdk.WindowTypeHint.NORMAL)
            self.window.set_skip_taskbar_hint(True)
            self.window.set_skip_pager_hint(True)
            self.window.set_accept_focus(False)
            self.window.set_keep_below(True)
            self.window.stick()
            self.window.set_name('nova-widgets')
            screen = self.window.get_screen()
            provider = Gtk.CssProvider()
            provider.load_from_data(b'''
                #nova-widgets { background: transparent; color: #e9e7f3; font-family: Sans; font-size: 11px; }
                .nova-card { background: #0b0d17; border: 1px solid #29263d; border-radius: 10px; padding: 9px; }
                .nova-heading { color: #bda7ff; font-weight: bold; font-size: 12px; }
                .nova-muted { color: #9893ac; font-size: 10px; }
                #nova-widgets progressbar trough { min-height: 5px; background: #222335; border: none; border-radius: 3px; }
                #nova-widgets progressbar progress { background: linear-gradient(to right, #5433de, #9b5cf6); border: none; border-radius: 3px; }
                #nova-widgets button { background: #181726; border: none; box-shadow: none; color: #e9e7f3; padding: 5px; min-height: 20px; }
                #nova-widgets button:hover { background: #392561; }
            ''')
            Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            visual = screen.get_rgba_visual()
            if visual and screen.is_composited():
                self.window.set_visual(visual)
            self.outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
            self.scroll = Gtk.ScrolledWindow()
            self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            self.scroll.set_propagate_natural_height(True)
            self.scroll.add(self.outer)
            self.window.add(self.scroll)
            self.cpu = self.metric(self.card('Sistema'), 'CPU')
            self.ram = self.metric(self.cpu[2], 'RAM / host')
            self.disk = self.metric(self.cpu[2], 'Armazenamento')
            note = Gtk.Label(label='GPU: utiliza\u00e7\u00e3o n\u00e3o monitorada')
            note.get_style_context().add_class('nova-muted')
            self.cpu[2].pack_start(note, False, False, 0)
            network_card = self.card('Rede')
            self.down = self.text(network_card, 'Download', 'Aguardando leitura')
            self.up = self.text(network_card, 'Upload', 'Aguardando leitura')
            self.graph = Gtk.DrawingArea()
            self.graph.set_size_request(190, 38)
            self.graph.connect('draw', self.draw_graph)
            network_card.pack_start(self.graph, False, False, 0)
            music = self.card('Em reprodu\u00e7\u00e3o')
            album = Gtk.Box(spacing=10)
            cover = Gtk.Image.new_from_file(str(asset_root()/'music'/'cover.svg'))
            from gi.repository import GdkPixbuf
            try:
                cover.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(asset_root()/'music'/'cover.svg'), 54, 54, True))
            except GLib.Error:
                cover.set_from_icon_name('novaos-music', Gtk.IconSize.DIALOG)
            album.pack_start(cover, False, False, 0)
            titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            self.song = Gtk.Label(label='NovaMusic', xalign=0)
            self.song.set_max_width_chars(21)
            self.song.set_ellipsize(3)
            titles.pack_start(self.song, False, False, 0)
            self.artist = Gtk.Label(label='Biblioteca local', xalign=0)
            self.artist.get_style_context().add_class('nova-muted')
            self.artist.set_max_width_chars(21)
            self.artist.set_ellipsize(3)
            titles.pack_start(self.artist, False, False, 0)
            album.pack_start(titles, True, True, 0)
            music.pack_start(album, False, False, 0)
            self.progress = Gtk.ProgressBar()
            music.pack_start(self.progress, False, False, 0)
            self.position = Gtk.Label(label='Player fechado', xalign=1)
            self.position.get_style_context().add_class('nova-muted')
            music.pack_start(self.position, False, False, 0)
            controls = Gtk.Box(spacing=8, homogeneous=True)
            for icon, option, tooltip in [('media-skip-backward-symbolic', '--previous', 'Anterior'),
                                           ('media-playback-start-symbolic', '--toggle', 'Reproduzir / pausar'),
                                           ('media-skip-forward-symbolic', '--next', 'Pr\u00f3xima')]:
                button = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
                button.set_tooltip_text(tooltip)
                button.connect('clicked', lambda _button, flag=option: self.control(flag))
                controls.pack_start(button, True, True, 0)
                if option == '--toggle':
                    self.play_button = button
            music.pack_start(controls, False, False, 0)
            session = self.card('Sess\u00e3o')
            self.text(session, 'Desktop', os.environ.get('XDG_CURRENT_DESKTOP', 'N/D'))
            self.text(session, 'Servidor', os.environ.get('XDG_SESSION_TYPE', 'N/D').upper())
            self.text(session, 'Perfil', 'Mobile' if os.environ.get('NOVAOS_MOBILE') == '1' else 'Desktop')
            self.elapsed = self.text(session, 'Widgets ativos', '0 min')
            self.window.show_all()
            self.place()
            screen.connect('monitors-changed', lambda *_: self.place())
            self.timer = GLib.timeout_add_seconds(2, self.update)
            self.update()

        def place(self):
            display = self.window.get_display()
            monitor = display.get_primary_monitor() or display.get_monitor(0)
            area = monitor.get_geometry()
            self.outer.set_size_request(min(250, max(200, area.width//5)), -1)
            self.scroll.set_max_content_height(max(200, area.height-130))
            # Short landscape displays can scroll the cards instead of clipping controls.
            self.window.move(area.x+area.width-self.outer.get_preferred_width()[1]-12, area.y+48)

        def card(self, title):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            box.get_style_context().add_class('nova-card')
            label = Gtk.Label(label=title, xalign=0)
            label.get_style_context().add_class('nova-heading')
            box.pack_start(label, False, False, 0)
            self.outer.pack_start(box, False, False, 0)
            return box

        @staticmethod
        def text(box, label, value):
            row = Gtk.Box(spacing=8)
            row.pack_start(Gtk.Label(label=label, xalign=0), True, True, 0)
            text = Gtk.Label(label=value, xalign=1)
            row.pack_start(text, False, False, 0)
            box.pack_start(row, False, False, 0)
            return text

        def metric(self, box, label):
            value = self.text(box, label, 'N/D')
            bar = Gtk.ProgressBar()
            box.pack_start(bar, False, False, 0)
            return value, bar, box

        def control(self, flag):
            try:
                Gio.Subprocess.new(['novaos', 'music', flag, '--background'], Gio.SubprocessFlags.NONE)
            except GLib.Error as error:
                self.position.set_text(str(error))

        def update(self):
            for item, reading in [(self.cpu, lambda: (psutil.cpu_percent(), None)),
                                  (self.ram, lambda: (psutil.virtual_memory().percent, psutil.virtual_memory())),
                                  (self.disk, lambda: (psutil.disk_usage('/').percent, psutil.disk_usage('/')))]:
                try:
                    percent, detail = reading()
                    item[0].set_text(f'{size(detail.used)} / {size(detail.total)}' if detail else f'{percent:.0f}%')
                    item[1].set_fraction(min(1, max(0, percent/100)))
                except (OSError, ValueError, psutil.Error):
                    item[0].set_text('N/D')
                    item[1].set_fraction(0)
            now = time.monotonic()
            try:
                current = psutil.net_io_counters()
                if current is None:
                    raise OSError('Counters unavailable')
                elapsed = now-self.network_time
                down = rate(current.bytes_recv, self.network.bytes_recv if self.network else None, elapsed)
                up = rate(current.bytes_sent, self.network.bytes_sent if self.network else None, elapsed)
                self.down.set_text(size(down)+'/s')
                self.up.set_text(size(up)+'/s')
                self.network, self.network_time = current, now
                self.history.append(down)
            except (OSError, psutil.Error):
                self.down.set_text('N/D')
                self.up.set_text('N/D')
            self.graph.queue_draw()
            playback = read_playback()
            self.song.set_text(str(playback.get('title', 'NovaMusic')))
            self.artist.set_text(str(playback.get('artist', 'Biblioteca local')))
            duration = max(0, float(playback.get('duration', 0)))
            position = max(0, float(playback.get('position', 0)))
            self.progress.set_fraction(min(1, position/duration) if duration else 0)
            if playback:
                self.position.set_text(f'{int(position)//60}:{int(position)%60:02d} / {int(duration)//60}:{int(duration)%60:02d}')
            else:
                self.position.set_text('Player fechado')
            icon = 'media-playback-pause-symbolic' if playback.get('playing') else 'media-playback-start-symbolic'
            self.play_button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
            self.elapsed.set_text(f'{int((now-self.began)//60)} min')
            return True

        def draw_graph(self, area, context):
            width, height = area.get_allocated_width(), area.get_allocated_height()
            ceiling = max(1024, max(self.history))
            context.set_source_rgb(.51, .31, .96)
            context.set_line_width(1.5)
            for index, value in enumerate(self.history):
                x = width*index/(len(self.history)-1)
                y = height-3-(height-6)*value/ceiling
                if index:
                    context.line_to(x, y)
                else:
                    context.move_to(x, y)
            context.stroke()
            return False

        def do_shutdown(self):
            if self.timer:
                GLib.source_remove(self.timer)
            Gtk.Application.do_shutdown(self)

    return Widgets().run(['novaos-widgets', *(['--quit'] if args.quit else [])])


if __name__ == '__main__':
    import sys
    raise SystemExit(main(sys.argv[1:]))
