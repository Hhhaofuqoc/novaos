"""NovaMonitor: leitura real, valores indisponíveis explicitados."""
import datetime
import os
import time
from gi.repository import Gtk, Gdk, GLib
from services import status
from services.mpris import Mpris
from widgets.history import History

START = time.monotonic()

def gigabytes(v): return f'{v/(1024**3):.1f} GiB'

class Sidebar(Gtk.Window):
    def __init__(self,width,height):
        super().__init__(title='NovaMonitor')
        self.set_decorated(False);self.set_keep_above(True);self.set_skip_taskbar_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_resizable(False);self.set_default_size(min(240,max(170,width//4)), min(650,height-52))
        self.get_style_context().add_class('nova')
        sc = Gtk.ScrolledWindow();sc.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        self.add(sc)
        self.root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.root.set_border_width(6);sc.add(self.root)
        self.widgets={}
        self.cpu_graph=History(100.0)
        self.card('⚙ Sistema', [('CPU','CPU'),('RAM Android','RAM'),('Armazenamento','DISK')], graph=self.cpu_graph)
        self.net_graph=History(1024*1024)
        self.card('⇵ Rede', [('Download','DOWN'),('Upload','UP')], graph=self.net_graph)
        mcard=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5)
        mcard.get_style_context().add_class('nova-sidebar');mcard.set_border_width(12)
        mcard.pack_start(self.heading('♫ Em reprodução'),False,False,0)
        self.music_title=Gtk.Label(label='Sem player MPRIS');self.music_title.set_xalign(0)
        self.music_author=Gtk.Label(label='—');self.music_author.set_xalign(0)
        mcard.pack_start(self.music_title,False,False,0);mcard.pack_start(self.music_author,False,False,0)
        self.music_progress=Gtk.ProgressBar();mcard.pack_start(self.music_progress,False,False,0)
        musicbuttons=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.player=Mpris();self.music_buttons=[]
        for title,meth in [('◀◀','Previous'),('▶Ⅱ','PlayPause'),('▶▶','Next')]:
            b=Gtk.Button(label=title);b.connect('clicked',lambda _,f=meth:self.player.control(f))
            musicbuttons.pack_start(b,True,True,0);self.music_buttons.append(b)
        mcard.pack_start(musicbuttons,False,False,0);self.root.pack_start(mcard,False,False,0)
        self.card('▣ Sessão', [('Termux:X11','X11'),('Container','CONT'),('Atividade','UPTIME')])
        self.connect('realize',lambda *_:self.move(max(0,width-self.get_allocated_width()-7),48))
        self.screenwidth=width
        GLib.timeout_add_seconds(3,self.tick);self.tick()

    def heading(self,text):
        l=Gtk.Label(label=text);l.set_xalign(0);l.get_style_context().add_class('heading');return l

    def card(self,title,fields,graph=None):
        b=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=7)
        b.get_style_context().add_class('nova-sidebar');b.set_border_width(12)
        b.pack_start(self.heading(title),False,False,0)
        for text,key in fields:
            row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=5)
            lab=Gtk.Label(label=text);lab.set_xalign(0)
            val=Gtk.Label(label='Indisponível');val.set_xalign(1)
            val.get_style_context().add_class('muted')
            row.pack_start(lab,True,True,0);row.pack_end(val,False,False,0)
            b.pack_start(row,False,False,0);self.widgets[key]=val
        if graph is not None:b.pack_start(graph,False,False,0)
        self.root.pack_start(b,False,False,0)

    def tick(self):
        m=status.host(); cpu=m.get('cpu_percent')
        self.widgets['CPU'].set_text(f'{cpu:.0f}%' if cpu is not None else 'Indisponível')
        self.cpu_graph.push(cpu)
        self.net_graph.push(m.get('download_bps'))
        ram=status.ram_android()
        self.widgets['RAM'].set_text(f'{gigabytes(ram[0])}/{gigabytes(ram[1])}' if ram else 'Indisponível')
        disk=status.storage()
        self.widgets['DISK'].set_text(f'{gigabytes(disk[2])} livres' if disk else 'Indisponível')
        self.widgets['DOWN'].set_text(status.human_rate(m.get('download_bps')))
        self.widgets['UP'].set_text(status.human_rate(m.get('upload_bps')))
        self.widgets['X11'].set_text('Ativo' if os.environ.get('DISPLAY') else 'Indisponível')
        self.widgets['CONT'].set_text('NovaOS (PRoot)')
        elapsed=int(time.monotonic()-START)
        self.widgets['UPTIME'].set_text(f'{elapsed//3600}h {(elapsed//60)%60:02}m')
        song=self.player.refresh()
        self.music_title.set_text(str(song.get('title') or 'Sem título')[:35] if song else 'Sem player MPRIS')
        self.music_author.set_text(str(song.get('artist') or '—')[:35] if song else '—')
        for b in self.music_buttons:b.set_sensitive(bool(song))
        if song and song.get('length') and song.get('position') is not None:
            self.music_progress.set_fraction(max(0,min(1,song['position']/song['length'])))
            self.music_progress.set_show_text(False)
        else:
            self.music_progress.set_fraction(0)
        self.move(max(0,self.screenwidth-self.get_allocated_width()-7),48)
        return True
