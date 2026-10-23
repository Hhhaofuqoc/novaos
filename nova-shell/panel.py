"""NovaBar: barra X11 nativa em GTK3, quatro desktops reais."""
import datetime
import re
import subprocess
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
from services import status


def cmd(*args):
    try: return subprocess.run(args, capture_output=True, text=True, timeout=1.8).stdout.strip()
    except (OSError, subprocess.TimeoutExpired): return ''

class Panel(Gtk.Window):
    def __init__(self, width, open_menu, open_settings):
        super().__init__(title='NovaBar')
        self.set_decorated(False); self.set_keep_above(True); self.set_skip_taskbar_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_default_size(width, 40)
        self.set_resizable(False); self.get_style_context().add_class('nova')
        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        root.get_style_context().add_class('nova-panel'); self.add(root)
        logo = Gtk.Button(); logo.get_style_context().add_class('brand')
        brand = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale('/opt/novaos/app/assets/icons/logo.svg',25,25,True)
        im = Gtk.Image.new_from_pixbuf(pix); brand.pack_start(im, False, False, 0)
        brand.pack_start(Gtk.Label(label='NovaOS'), False, False, 0)
        logo.add(brand)
        logo.connect('clicked', lambda *_: open_menu()); root.pack_start(logo, False, False, 2)
        self.workspaces = []
        for i in range(4):
            b = Gtk.Button(label=str(i+1)); b.set_size_request(38, 32)
            b.connect('clicked', lambda _, k=i: cmd('wmctrl', '-s', str(k)))
            root.pack_start(b, False, False, 0); self.workspaces.append(b)
        root.pack_start(Gtk.Label(), True, True, 0)
        settings = Gtk.Button(label='⚙'); settings.connect('clicked', lambda *_: open_settings())
        root.pack_end(settings, False, False, 3)
        self.clock = Gtk.Button(); self.clock.connect('clicked', self.calendar)
        root.pack_end(self.clock, False, False, 3)
        self.battery = Gtk.Label(label='Bateria: —'); root.pack_end(self.battery, False, False, 5)
        self.net = Gtk.Label(label='Rede: —'); root.pack_end(self.net, False, False, 8)
        volume = Gtk.Button(label='♫'); volume.connect('clicked', self.volume)
        root.pack_end(volume, False, False, 0)
        self.connect('realize', lambda *_: self.move(0, 0))
        GLib.timeout_add_seconds(2, self.tick); self.tick()

    def tick(self):
        self.clock.set_label(datetime.datetime.now().strftime('%H:%M   %d/%m/%Y'))
        m = status.host(); b = m.get('battery_percent')
        self.battery.set_text(f'▣ {b}%' if b is not None else '▣ —')
        self.net.set_text('⇵ Rede' if m.get('download_bps') is not None else 'Rede: indisponível')
        work = cmd('wmctrl', '-d').splitlines()
        active = next((int(r.split()[0]) for r in work if len(r.split()) >= 2 and r.split()[1]=='*'), -1)
        for i, button in enumerate(self.workspaces):
            c = button.get_style_context()
            c.add_class('active') if active == i else c.remove_class('active')
        return True

    def calendar(self, button):
        pop = Gtk.Popover.new(button)
        cal = Gtk.Calendar(); pop.add(cal); pop.show_all()

    def volume(self, button):
        pop = Gtk.Popover.new(button)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        box.set_border_width(12)
        raw = cmd('pactl','get-sink-volume','@DEFAULT_SINK@')
        found = re.search(r'(\d+)%', raw)
        if not found:
            box.pack_start(Gtk.Label(label='Áudio indisponível'), False, False, 0)
        else:
            box.pack_start(Gtk.Label(label='Volume PulseAudio'), False, False, 0)
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,100,5)
            scale.set_value(min(100,int(found.group(1)))); scale.set_size_request(190,-1)
            scale.connect('value-changed', lambda s: cmd('pactl','set-sink-volume',
                     '@DEFAULT_SINK@',f'{int(s.get_value())}%'))
            box.pack_start(scale, False, False, 0)
        pop.add(box); pop.show_all()
