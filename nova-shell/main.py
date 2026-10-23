#!/usr/bin/env python3
"""NovaShell: shell GTK3 executável sobre Openbox, sem desktop pesado."""
import os
import sys
import subprocess
from pathlib import Path
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GLib
from panel import Panel
from launcher import Launcher
from dock import Dock
from sidebar import Sidebar
from services import state

ROOT = Path('/opt/novaos/app')

class NovaShell:
    def __init__(self):
        display=Gdk.Display.get_default()
        if display is None: raise RuntimeError('DISPLAY/Termux:X11 indisponível')
        monitor=display.get_primary_monitor() or display.get_monitor(0)
        rect=monitor.get_geometry()
        self.width,self.height=rect.width,rect.height
        self.cfg=state.load()
        self.profile=os.environ.get('NOVAOS_PROFILE','full')
        self.panel=Panel(self.width,self.toggle_menu,self.open_settings)
        self.panel.show_all()
        # A barra deve continuar funcionando mesmo se um widget opcional falhar.
        self.launcher=None
        self.dock=None
        self.sidebar=None
        import traceback
        try:
            self.launcher=Launcher(self.width,self.height,self.open_settings)
        except Exception:
            print('[NovaShell] Erro ao carregar NovaMenu:', flush=True)
            traceback.print_exc()
        if self.cfg['show_dock']:
            try:
                self.dock=Dock(self.width,self.height,self.toggle_menu)
                self.dock.show_all()
            except Exception:
                print('[NovaShell] Erro ao carregar NovaDock:', flush=True)
                traceback.print_exc()
        if self.profile=='full' and self.cfg['show_sidebar']:
            try:
                self.sidebar=Sidebar(self.width,self.height)
                self.sidebar.show_all()
            except Exception:
                print('[NovaShell] Erro ao carregar NovaMonitor:', flush=True)
                traceback.print_exc()
        GLib.timeout_add_seconds(2,self.health)

    def toggle_menu(self):
        if self.launcher is not None:
            self.launcher.toggle()
        else:
            print('[NovaShell] NovaMenu indisponivel: veja novashell.log', flush=True)

    def open_settings(self):
        try:subprocess.Popen(['/usr/local/bin/nova-settings'])
        except OSError as error:print('NovaCenter: ',error)

    def health(self):
        # Evita que um fechamento isolado do widget derrube a sessão toda.
        if not self.panel.get_visible():self.panel.show_all()
        return True

def main():
    Gtk.init(sys.argv)
    css=Gtk.CssProvider()
    css.load_from_path(str(ROOT/'themes/NovaDark/gtk.css'))
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    colors={'violet':'#7f5cff','blue':'#368cfa','cyan':'#24c4e0'}
    accent=colors.get(state.load().get('accent'),'#7f5cff')
    accentcss=Gtk.CssProvider()
    accentcss.load_from_data(('button.active,button.suggested-action { background-color: '+accent+'; } progressbar progress { background-color: '+accent+'; }').encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),accentcss,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION+1)
    Gtk.Window.set_default_icon_name('preferences-desktop-theme')
    shell=NovaShell()
    print(f'NovaShell 1.0 | {shell.width}x{shell.height} | {shell.profile}',flush=True)
    Gtk.main()

if __name__=='__main__':main()
