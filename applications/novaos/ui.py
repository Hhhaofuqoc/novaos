"""Native GTK utilities. All actions either execute locally or report a real error."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gio
from . import __version__, system
from .config import read_config, update_config, atomic_write, asset_root

def size(value):
    return "indisponível" if value is None else f"{value / 1024**3:.2f} GiB"

def label(text, *, wrap=False):
    widget = Gtk.Label(label=text, xalign=0)
    widget.set_line_wrap(wrap)
    widget.set_selectable(True)
    return widget

class Window(Gtk.ApplicationWindow):
    def __init__(self, app, title, width=760, height=560):
        super().__init__(application=app, title=title)
        self.set_wmclass(app.get_application_id(), title.split(" • ")[0])
        self.set_default_size(width, height)
        self.set_icon_name("novaos")
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin=22)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.box)
        self.add(scroll)
        self.status = label("")
        self.status.set_line_wrap(True)
        self.box.pack_end(self.status, False, False, 0)

    def text(self, text):
        widget = label(text, wrap=True)
        self.box.pack_start(widget, False, False, 0)
        return widget

    def button(self, title, callback, box=None):
        widget = Gtk.Button(label=title)
        widget.set_size_request(-1, 44)
        widget.connect("clicked", lambda *_: self.run(callback))
        (box or self.box).pack_start(widget, False, False, 0)
        return widget

    def run(self, callback):
        try:
            callback()
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            self.status.set_text(str(error))

class Welcome(Window):
    def __init__(self, app):
        super().__init__(app, "NovaWelcome • NovaOS")
        self.text("NovaOS  •  Your universe. Your system.")
        self.text("Synthwave Linux Experience  ·  "+__version__)
        self.text("Seus aplicativos Linux, arquivos e músicas funcionam localmente. "
                  "Na edição Mobile, Wi-Fi, Bluetooth, bateria e permissões continuam sob controle do Android.")
        grid = Gtk.Grid(column_spacing=12, row_spacing=12, column_homogeneous=True)
        self.box.pack_start(grid, True, True, 0)
        entries = [("Arquivos", "files"), ("Terminal", "terminal"), ("Navegador", "browser"),
                   ("NovaMusic", "music"), ("Notas", "notes"), ("Editor", "editor"),
                   ("Configurações", "settings"), ("Monitor", "monitor"),
                   ("Instalar aplicativos", "store"), ("Atualizações", "updater")]
        for index, (title, command) in enumerate(entries):
            button = Gtk.Button(label=title)
            button.set_size_request(120, 64)
            button.connect("clicked", lambda _, cmd=command: self.run(lambda: system.launch(cmd)))
            grid.attach(button, index % 2, index // 2, 1, 1)

class Settings(Window):
    def __init__(self, app):
        super().__init__(app, "NovaSettings")
        self.text("Aparência e desempenho")
        self.text("Lite desliga composição e animações. Balanced e Ultra ativam os efeitos disponíveis no XFCE. "
                  "O modo automático começa em Lite no Android. Não há blur nesta versão.")
        state = read_config()
        self.profile = Gtk.ComboBoxText()
        for ident, title in (("auto", "Automático"), ("lite", "Lite"), ("balanced", "Balanced"), ("ultra", "Ultra")):
            self.profile.append(ident, title)
        self.profile.set_active_id(state["profile"])
        self.profile.set_size_request(-1, 44)
        self.box.pack_start(self.profile, False, False, 0)
        self.theme = Gtk.ComboBoxText()
        for ident, title in (("dark", "Neon escuro"), ("light", "Claro")):
            self.theme.append(ident, title)
        self.theme.set_active_id(state["theme"])
        self.theme.set_size_request(-1, 44)
        self.box.pack_start(self.theme, False, False, 0)
        self.saver = Gtk.CheckButton(label="Economia de energia (forçar Lite)")
        self.saver.set_active(state["power_save"])
        self.adaptive = Gtk.CheckButton(label="Reduzir efeitos com pouca RAM ou bateria, quando mensuráveis")
        self.adaptive.set_active(state["adaptive"])
        for widget in (self.saver, self.adaptive):
            widget.set_size_request(-1, 42)
            self.box.pack_start(widget, False, False, 0)
        self.button("Aplicar", self.apply)
        row = Gtk.Box(spacing=8, homogeneous=True)
        self.box.pack_start(row, False, False, 0)
        for title, command in (("Tela", "display"), ("Teclado", "keyboard"), ("Mouse", "mouse")):
            self.button(title, lambda cmd=command: system.launch(cmd), row)
        self.button("Todas as configurações XFCE", lambda: system.launch("desktop-settings"))
        if system.is_mobile():
            self.text("Rede e Bluetooth: use os controles do Android. Para encerrar toda a sessão, "
                      "execute novaos-mobile stop no Termux. Desinstalar o Termux apaga os dados internos; faça backup antes.")

    def apply(self):
        settings = update_config({"profile": self.profile.get_active_id(), "theme": self.theme.get_active_id(),
                                  "power_save": self.saver.get_active(), "adaptive": self.adaptive.get_active()})
        self.status.set_text("Aplicando…")
        # Let GTK paint before launching a short configuration command.
        def configure():
            self.run(lambda: self.status.set_text(system.apply_appearance(settings)))
            return False
        GLib.idle_add(configure)

class Monitor(Window):
    def __init__(self, app):
        super().__init__(app, "NovaMonitor")
        self.summary = self.text("Coletando leituras reais…")
        self.summary.set_selectable(True)
        self.button("Gerenciar processos", lambda: system.launch("processes"))
        self.text("As métricas em PRoot podem ser limitadas pelo Android e não representam apenas o NovaOS. "
                  "Uma leitura bloqueada aparece como indisponível. O primeiro intervalo de CPU é descartado.")
        self.previous = None
        self.timer = GLib.timeout_add_seconds(3, self.refresh)
        self.connect("destroy", self.on_destroy)
        try:
            system.snapshot()  # Prime CPU counters; avoid presenting a fabricated initial zero.
        except (OSError, ImportError):
            pass

    def refresh(self):
        try:
            data = system.snapshot()
            cpu = "indisponível" if data["cpu_percent"] is None else f"{data['cpu_percent']:.1f}%"
            uptime = "indisponível" if data["uptime"] is None else f"{data['uptime']/3600:.1f} horas"
            battery = "indisponível" if data["battery_percent"] is None else f"{data['battery_percent']:.0f}%"
            temperatures = [f"{n}: {max(v):.1f} °C" for n,v in data["temperatures"].items() if v]
            net = "indisponível"
            if self.previous and data["network_received"] is not None and self.previous["network_received"] is not None:
                seconds = data["timestamp"]-self.previous["timestamp"]
                net = f"↓ {max(0, data['network_received']-self.previous['network_received'])/seconds/1024:.1f} KiB/s"
            self.previous = data
            self.summary.set_text("\n".join([
                f"CPU: {cpu}", f"RAM: {size(data['memory_used'])} / {size(data['memory_total'])}",
                f"Armazenamento livre: {size(data['disk_free'])} / {size(data['disk_total'])}",
                f"Rede: {net}", f"Bateria: {battery}", "Temperatura: "+(", ".join(temperatures) or "indisponível"),
                f"Uptime do kernel: {uptime}", f"Kernel: {data['kernel']}", f"Distribuição: {data['distribution']}",
                f"Desktop: {data['desktop']}", f"Arquitetura: {data['architecture']}",
                f"Perfil efetivo: {system.current_profile(metrics=data)}"]))
            self.status.set_text("Algumas leituras estão indisponíveis neste ambiente." if data["errors"] else "")
        except (OSError, ImportError, RuntimeError) as error:
            self.status.set_text(str(error))
        return True

    def on_destroy(self, *_):
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = None

class Notes(Window):
    def __init__(self, app):
        super().__init__(app, "NovaNotes")
        data = Path(os.environ.get("XDG_DATA_HOME", Path.home()/".local"/"share"))
        self.path = data/"novaos"/"notes.txt"
        self.timer = None
        self.dirty = False
        self.text("Notas locais • salvamento automático")
        self.text(str(self.path))
        self.editor = Gtk.TextView()
        self.editor.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.editor.set_left_margin(12)
        self.editor.set_right_margin(12)
        self.editor.set_top_margin(12)
        self.editor.set_bottom_margin(12)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(280)
        scrolled.add(self.editor)
        self.box.pack_start(scrolled, True, True, 0)
        self.buffer = self.editor.get_buffer()
        try:
            self.buffer.set_text(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass
        except (OSError, UnicodeError) as error:
            self.editor.set_editable(False)
            self.status.set_text(f"Não foi possível carregar as notas: {error}")
        self.buffer.connect("changed", self.changed)
        self.button("Salvar agora", self.save)
        self.connect("delete-event", self.close)

    def changed(self, *_):
        self.dirty = True
        if self.timer:
            GLib.source_remove(self.timer)
        self.timer = GLib.timeout_add(800, self.autosave)

    def autosave(self):
        self.timer = None
        self.run(self.save)
        return False

    def save(self):
        if not self.dirty:
            return
        start, end = self.buffer.get_bounds()
        atomic_write(self.path, self.buffer.get_text(start, end, True))
        self.dirty = False
        self.status.set_text("Salvo às "+time.strftime("%H:%M:%S"))

    def close(self, *_):
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = None
        try:
            self.save()
        except OSError as error:
            self.status.set_text(f"Não salvo; a janela continuará aberta: {error}")
            return True
        return False

class Store(Window):
    def __init__(self, app, update=False):
        super().__init__(app, "NovaUpdater" if update else "NovaStore")
        self.text("Pacotes dos repositórios APT configurados")
        self.text("A operação abre um terminal, mostra o comando e exige confirmação. "
                  "Baixar e atualizar pacotes requer internet. Seus arquivos pessoais não são removidos.")
        if update:
            self.button("1 · Atualizar catálogo APT", lambda: system.package_terminal("update"))
            self.button("2 · Atualizar pacotes instalados", lambda: system.package_terminal("upgrade"))
        else:
            self.query = Gtk.SearchEntry()
            self.query.set_placeholder_text("Buscar pacote, por exemplo: gimp")
            self.query.set_size_request(-1, 44)
            self.query.connect("activate", lambda *_: self.run(self.search))
            self.box.pack_start(self.query, False, False, 0)
            self.search_button = self.button("Buscar no catálogo local", self.search)
            self.results = Gtk.ListStore(str, str)
            tree = Gtk.TreeView(model=self.results)
            for i, name in enumerate(("Pacote", "Descrição")):
                renderer = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn(name, renderer, text=i)
                column.set_resizable(True)
                tree.append_column(column)
            self.selection = tree.get_selection()
            scroll = Gtk.ScrolledWindow()
            scroll.set_min_content_height(250)
            scroll.add(tree)
            self.box.pack_start(scroll, True, True, 0)
            self.button("Instalar pacote selecionado…", self.install)

    def search(self):
        import re
        query = self.query.get_text().strip()
        if len(query) < 2 or len(query) > 60:
            raise ValueError("Digite de 2 a 60 caracteres.")
        # Argument vector + escaped regex: no shell, and no option injection.
        self.search_button.set_sensitive(False)
        self.status.set_text("Buscando…")
        process = Gio.Subprocess.new(["apt-cache", "search", "--names-only", "--", re.escape(query)],
                                     Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
        def finish(proc, result):
            try:
                _, output, error = proc.communicate_utf8_finish(result)
                if not proc.get_successful():
                    raise RuntimeError(error)
                self.results.clear()
                lines = output.splitlines()
                for line in lines[:200]:
                    name, _, description = line.partition(" - ")
                    self.results.append((name, description))
                self.status.set_text(f"{len(lines)} resultados; exibindo até 200.")
            except (GLib.Error, RuntimeError) as error:
                self.status.set_text(str(error))
            finally:
                self.search_button.set_sensitive(True)
        process.communicate_utf8_async(None, None, finish)

    def install(self):
        model, iterator = self.selection.get_selected()
        if iterator is None:
            raise ValueError("Selecione um pacote primeiro.")
        system.package_terminal("install", model[iterator][0])

def main(command):
    GLib.set_prgname("novaos-"+command)
    GLib.set_application_name({"welcome": "NovaWelcome", "settings": "NovaSettings", "monitor": "NovaMonitor",
                               "notes": "NovaNotes", "store": "NovaStore", "updater": "NovaUpdater"}[command])
    application = Gtk.Application(application_id="org.novaos."+command,
                                  flags=Gio.ApplicationFlags.FLAGS_NONE)
    windows = []
    def activate(app):
        if windows:
            windows[0].present()
            return
        classes = {"welcome": Welcome, "settings": Settings, "monitor": Monitor, "notes": Notes}
        window = Store(app, update=command == "updater") if command in ("store", "updater") else classes[command](app)
        windows.append(window)
        window.connect("destroy", lambda *_: windows.clear())
        window.show_all()
    application.connect("activate", activate)
    return application.run(["novaos-"+command])
