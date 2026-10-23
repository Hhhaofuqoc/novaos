#!/usr/bin/env python3
"""NovaCenter: configurações REAIS, arquivo JSON persistente."""
import os
import sys
import subprocess
import sys
from pathlib import Path
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, Gdk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services import state

ROOT=Path('/opt/novaos/app')
class Settings(Gtk.Window):
    def __init__(self):
        super().__init__(title='NovaCenter • Configurações')
        self.set_default_size(560,480)
        self.get_style_context().add_class('nova-settings')
        self.cfg=state.load()
        notebook=Gtk.Notebook();self.add(notebook)
        appearance=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=15)
        appearance.set_border_width(20)
        label=Gtk.Label(label='NovaDark • aparência da NovaShell');label.set_xalign(0)
        appearance.pack_start(label,False,False,0)
        self.toggle(appearance,'Mostrar dock', 'show_dock')
        self.toggle(appearance,'Mostrar widgets laterais', 'show_sidebar')
        accent=Gtk.ComboBoxText()
        for k in ('violet','blue','cyan'):accent.append_text(k)
        accent.set_active(['violet','blue','cyan'].index(self.cfg.get('accent','violet')) if self.cfg.get('accent') in ('violet','blue','cyan') else 0)
        accent.connect('changed',self.change_accent)
        appearance.pack_start(Gtk.Label(label='Cor de destaque (aplicada após reiniciar a NovaShell):'),False,False,0)
        appearance.pack_start(accent,False,False,0)
        wallpaper=Gtk.Button(label='Escolher papel de parede...')
        wallpaper.connect('clicked',self.choose_wallpaper)
        appearance.pack_start(wallpaper,False,False,0)
        note=Gtk.Label(label='Configurações visuais salvas automaticamente.\nUse novaos restart para aplicar dock, sidebar e cores.')
        note.set_xalign(0);appearance.pack_start(note,False,False,0)
        notebook.append_page(appearance,Gtk.Label(label='Aparência'))
        info=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=15);info.set_border_width(20)
        for s in ['NovaOS 1.0 • NovaShell em GTK 3','Gerenciador de janelas: Openbox','Base: Debian/Ubuntu PRoot ARM64 existente','Kernel: Android (informações podem ser mascaradas pelo PRoot)','Terminal: comando nova-info','Diagnóstico no Termux: novaos repair']:
            label=Gtk.Label(label=s);label.set_xalign(0);info.pack_start(label,False,False,0)
        notebook.append_page(info,Gtk.Label(label='Sobre'))
        self.connect('destroy',Gtk.main_quit)

    def toggle(self,box,title,key):
        t=Gtk.CheckButton(label=title);t.set_active(bool(self.cfg.get(key,True)))
        t.connect('toggled',lambda v:self.set_key(key,v.get_active()))
        box.pack_start(t,False,False,0)

    def set_key(self,key,value):
        self.cfg[key]=value;state.save(self.cfg)

    def change_accent(self,chooser):
        if chooser.get_active_text():self.set_key('accent',chooser.get_active_text())

    def choose_wallpaper(self,*_):
        dialog=Gtk.FileChooserDialog(title='Selecionar imagem real',transient_for=self,
            action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK)
        flt=Gtk.FileFilter();flt.set_name('Imagens');flt.add_pixbuf_formats();dialog.add_filter(flt)
        if dialog.run()==Gtk.ResponseType.OK:
            path=dialog.get_filename()
            try:
                subprocess.run(['feh','--no-fehbg','--bg-fill',path],check=True,timeout=15)
                self.set_key('wallpaper',path)
            except (OSError,subprocess.SubprocessError) as error:
                err=Gtk.MessageDialog(transient_for=self,flags=0,message_type=Gtk.MessageType.ERROR,
                                      buttons=Gtk.ButtonsType.OK,text='Falha ao definir wallpaper')
                err.format_secondary_text(str(error));err.run();err.destroy()
        dialog.destroy()

def main():
    Gtk.init(sys.argv)
    css=Gtk.CssProvider();css.load_from_path(str(ROOT/'themes/NovaDark/gtk.css'))
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    app=Settings();app.show_all();Gtk.main()
if __name__=='__main__':main()
