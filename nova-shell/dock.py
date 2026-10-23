"""NovaDock: fixados, aplicações instaladas e foco de janelas X11 existentes."""
import re
import subprocess
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
from services import apps, state

DEFAULT_KEYS = ('pcmanfm','lxterminal','firefox','geany','mpv','gpicview','nova-center')

def windows():
    try:
        p = subprocess.run(['wmctrl','-lx'],capture_output=True,text=True,timeout=1.5)
        result = []
        for line in p.stdout.splitlines():
            parts = line.split(maxsplit=4)
            if len(parts) >= 4: result.append({'id':parts[0],'class':parts[2].casefold(),'name':parts[4] if len(parts)>4 else ''})
        return result
    except (OSError,subprocess.TimeoutExpired): return []

class Dock(Gtk.Window):
    def __init__(self, screen_width, screen_height, open_menu):
        super().__init__(title='NovaDock')
        self.screen_width = screen_width; self.screen_height = screen_height
        self.set_decorated(False); self.set_keep_above(True); self.set_skip_taskbar_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK); self.set_resizable(False)
        self.get_style_context().add_class('nova')
        self.outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=2)
        self.outer.get_style_context().add_class('nova-dock'); self.add(self.outer)
        self.open_menu = open_menu
        self.connect('size-allocate',self.position)
        self.render(); GLib.timeout_add_seconds(5, self.refresh)

    def position(self,*_):
        w = self.get_allocated_width()
        self.move(max(0, (self.screen_width-w)//2), self.screen_height-76)

    def pinned(self):
        available = apps.installed(); cfg = state.load(); entries=cfg['pinned']
        if not entries:
            entries = [k for k in available if any(key in k.casefold() for key in DEFAULT_KEYS)][:7]
        return [(k,available[k]) for k in entries if k in available]

    def render(self):
        for child in self.outer.get_children():self.outer.remove(child)
        logo = Gtk.Button(); logo.set_tooltip_text('NovaMenu')
        pix=GdkPixbuf.Pixbuf.new_from_file_at_scale('/opt/novaos/app/assets/icons/logo.svg',34,34,True)
        img = Gtk.Image.new_from_pixbuf(pix); logo.add(img)
        logo.connect('clicked',lambda *_:self.open_menu())
        self.outer.pack_start(logo,False,False,0)
        opened = windows()
        for ident, app in self.pinned():
            b=Gtk.Button(); b.set_tooltip_text(app.get_name())
            ico = app.get_icon()
            im=Gtk.Image.new_from_gicon(ico,Gtk.IconSize.LARGE_TOOLBAR) if ico else Gtk.Image.new_from_icon_name('application-x-executable',Gtk.IconSize.LARGE_TOOLBAR)
            im.set_pixel_size(32); b.add(im)
            hits=[w for w in opened if any(token in w['class'] for token in
                    re.findall(r'[a-z]{4,}',ident.casefold().replace('.desktop','')))]
            if hits: b.get_style_context().add_class('active')
            b.connect('clicked',lambda _,a=app,h=hits:self.activate(a,h))
            b.connect('button-press-event',lambda widget,event,k=ident:self.press(widget,event,k))
            self.outer.pack_start(b,False,False,0)
        trash=Gtk.Button(label='▤'); trash.set_tooltip_text('Lixeira (GVfs)')
        trash.connect('clicked',lambda *_:subprocess.Popen(['pcmanfm','trash:///']))
        self.outer.pack_end(trash,False,False,0)
        self.outer.show_all(); self.position()

    def activate(self, app, hits):
        if hits:
            try:
                subprocess.run(['wmctrl','-ia',hits[0]['id']],timeout=1.5,check=True)
                return
            except (OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired): pass
        try: apps.launch(app)
        except Exception as e: print('NovaDock: não pôde abrir:',e)

    def press(self,button,event,ident):
        if event.button != 3:return False
        menu=Gtk.Menu(); data=state.load(); pins=data['pinned']
        if not pins: pins=[k for k,_ in self.pinned()]
        options=[('Desafixar', 'remove'),('Mover à esquerda','left'),('Mover à direita','right')]
        for title,action in options:
            item=Gtk.MenuItem(label=title)
            item.connect('activate',lambda _, k=ident, a=action:self.adjust(k,a))
            menu.append(item)
        menu.show_all();menu.popup_at_pointer(event);return True

    def adjust(self,ident,action):
        data=state.load();pins=data['pinned'] or [k for k,_ in self.pinned()]
        if ident not in pins:return
        index=pins.index(ident)
        if action=='remove':pins.remove(ident)
        elif action=='left' and index>0:pins[index-1],pins[index]=pins[index],pins[index-1]
        elif action=='right' and index<len(pins)-1:pins[index+1],pins[index]=pins[index],pins[index+1]
        data['pinned']=pins;state.save(data);self.render()

    def refresh(self):
        # Reinicia visual quando estados mudam: mantém número de widgets limitado.
        if self.get_visible():self.render()
        return True
