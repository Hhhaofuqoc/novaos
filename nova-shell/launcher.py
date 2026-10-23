"""NovaMenu - categorias, busca por nome e favoritos XDG reais."""
from gi.repository import Gtk, Gdk
from services import apps, state

class Launcher(Gtk.Window):
    def __init__(self, screen_width, screen_height, on_settings):
        super().__init__()
        self.set_decorated(False); self.set_keep_above(True)
        self.set_skip_taskbar_hint(True); self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_title('NovaMenu'); self.get_style_context().add_class('nova-menu')
        self.set_default_size(min(575,screen_width-8), min(595,screen_height-60))
        self.set_size_request(min(400,screen_width-8), min(350,screen_height-60))
        self.connect('key-press-event', self.keypress)
        self.connect('focus-out-event', lambda *_: self.hide())
        self.apps = {}; self.category = 'Favoritos'; self.on_settings = on_settings
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        root.set_border_width(10); self.add(root)
        self.search = Gtk.SearchEntry(); self.search.set_placeholder_text('Pesquisar aplicativos...')
        self.search.connect('search-changed', self.render); root.pack_start(self.search, False, False, 0)
        mid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7); root.pack_start(mid, True, True, 0)
        catbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1); catbox.set_size_request(146,-1)
        for category in apps.CATEGORIES:
            b = Gtk.Button(label=category); b.set_halign(Gtk.Align.FILL)
            b.connect('clicked', lambda _, c=category: self.set_category(c)); catbox.pack_start(b,False,False,0)
        cs = Gtk.ScrolledWindow(); cs.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        cs.set_size_request(146,-1); cs.add(catbox); mid.pack_start(cs,False,False,0)
        scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        self.flow = Gtk.FlowBox(); self.flow.set_min_children_per_line(2)
        self.flow.set_max_children_per_line(4); self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_column_spacing(8); self.flow.set_row_spacing(8)
        scroll.add(self.flow); mid.pack_start(scroll,True,True,0)
        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=4)
        cfg = Gtk.Button(label='⚙ Configurações'); cfg.connect('clicked', self.settings)
        bottom.pack_start(cfg,False,False,0)
        close = Gtk.Button(label='Fechar menu'); close.connect('clicked',lambda *_:self.hide())
        bottom.pack_end(close,False,False,0); root.pack_end(bottom,False,False,0)

    def toggle(self):
        if self.get_visible(): self.hide(); return
        self.apps = apps.installed(); self.render()
        self.show_all(); self.move(5,43); self.search.grab_focus()

    def keypress(self, _, event):
        if event.keyval == Gdk.KEY_Escape: self.hide(); return True
        return False

    def set_category(self, cat):
        self.category = cat; self.render()

    def render(self, *_):
        if not hasattr(self,'flow'): return
        for child in self.flow.get_children(): self.flow.remove(child)
        query = self.search.get_text().strip().casefold(); favorites = state.load()['favorites']
        data = []
        for ident, app in self.apps.items():
            if query and query not in app.get_name().casefold(): continue
            if not query and self.category == 'Favoritos' and ident not in favorites:
                # Primeira instalação: preencher com apps REAIS detectados, sem persistir falsos pins.
                defaults = ('terminal', 'pcmanfm', 'firefox', 'geany', 'mpv', 'gpicview', 'nova-center')
                if favorites or not any(t in ident.casefold() for t in defaults): continue
            elif not query and self.category != 'Favoritos' and not apps.category(app,self.category): continue
            data.append((ident,app))
        for ident, app in data[:100]:
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            btn = Gtk.Button(); btn.get_style_context().add_class('app')
            vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
            icon = app.get_icon()
            im = Gtk.Image.new_from_gicon(icon,Gtk.IconSize.DIALOG) if icon else Gtk.Image.new_from_icon_name('application-x-executable',Gtk.IconSize.DIALOG)
            im.set_pixel_size(40); vb.pack_start(im,False,False,0)
            txt = Gtk.Label(label=app.get_name()); txt.set_line_wrap(True); txt.set_max_width_chars(16)
            txt.set_lines(2); vb.pack_start(txt,False,False,0)
            btn.add(vb); btn.connect('clicked',lambda _, a=app: self.open_app(a))
            outer.pack_start(btn,False,False,0)
            fav = Gtk.Button(label='★' if ident in favorites else '☆')
            fav.set_tooltip_text('Adicionar/remover dos favoritos')
            fav.connect('clicked',lambda _, k=ident:self.favorite(k))
            actions=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            actions.pack_start(fav,True,True,0)
            pinned=state.load()['pinned']
            pb=Gtk.Button(label='●' if ident in pinned else '+')
            pb.set_tooltip_text('Fixar/desafixar na NovaDock')
            pb.connect('clicked',lambda _,k=ident:self.pin(k))
            actions.pack_start(pb,True,True,0)
            outer.pack_start(actions,False,False,0); self.flow.add(outer)
        self.flow.show_all()

    def pin(self,ident):
        data=state.load(); pins=data['pinned']
        if not pins:
            found=apps.installed()
            defaults=('pcmanfm','lxterminal','firefox','geany','mpv','gpicview','nova-center')
            pins=[k for k in found if any(n in k.casefold() for n in defaults)][:7]
        if ident in pins:pins.remove(ident)
        else:pins.append(ident)
        data['pinned']=pins;state.save(data);self.render()

    def open_app(self, app):
        try: apps.launch(app)
        except Exception as e: self.error(str(e))
        else: self.hide()

    def favorite(self, ident):
        data = state.load(); fav = data['favorites']
        if ident in fav: fav.remove(ident)
        else: fav.append(ident)
        state.save(data); self.render()

    def settings(self,*_):
        self.hide(); self.on_settings()

    def error(self,message):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.ERROR,
                     buttons=Gtk.ButtonsType.CLOSE, text='Falha ao abrir aplicativo')
        dialog.format_secondary_text(message); dialog.run();dialog.destroy()
