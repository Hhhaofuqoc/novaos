"""NovaMusic: local GTK3 / GStreamer player with no network dependency.

The playlist and persistence classes are deliberately independent of GTK so
headless tests can exercise real state transitions on every build platform.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import os
from pathlib import Path
import random
import sys
import tempfile
from typing import Optional

SUPPORTED = {'.flac', '.wav', '.ogg', '.opus', '.mp3', '.m4a', '.aac'}


@dataclass
class Track:
    path: Path
    title: str
    artist: str = 'Unknown artist'
    album: str = 'Local library'
    duration: float = 0

    @classmethod
    def local(cls, path):
        path = Path(path).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            raise ValueError(f'Unsupported or missing audio file: {path}')
        return cls(path, path.stem.replace('_', ' '))

    def as_dict(self):
        return {'path': str(self.path), 'title': self.title, 'artist': self.artist,
                'album': self.album, 'duration': self.duration}


def asset_root() -> Path:
    override = os.environ.get('NOVAOS_ASSETS')
    if override:
        return Path(override)
    installed = Path('/usr/share/novaos')
    if installed.is_dir():
        return installed
    return Path(__file__).resolve().parents[2]


def load_album(directory: Optional[Path] = None) -> list[Track]:
    directory = (directory or asset_root()/'music'/'generated').resolve()
    try:
        manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    if not isinstance(manifest, dict) or not isinstance(manifest.get('tracks'), list):
        return []
    tracks = []
    for item in manifest.get('tracks', []):
        try:
            path = (directory/item['path']).resolve()
            # A downloaded manifest must not escape its album directory.
            path.relative_to(directory)
            if path.is_file() and path.suffix.lower() in SUPPORTED:
                tracks.append(Track(path, str(item['title']), str(item.get('artist','NovaOS')),
                                    str(item.get('album','Your Universe')),
                                    max(0, float(item.get('duration_seconds',0)))))
        except (KeyError, ValueError, TypeError, OSError):
            continue
    return tracks


class Playlist:
    def __init__(self, tracks=(), *, rng=None):
        self.tracks = list(tracks)
        self.index = 0 if self.tracks else -1
        self.repeat = 'none'
        self._shuffle = False
        self._shuffle_seen = {self.index} if self.index >= 0 else set()
        self.history = []
        self.rng = rng or random.Random()

    @property
    def shuffle(self):
        return self._shuffle

    @shuffle.setter
    def shuffle(self, enabled):
        self._shuffle = bool(enabled)
        self._shuffle_seen = {self.index} if self.index >= 0 else set()

    @property
    def current(self):
        return self.tracks[self.index] if 0 <= self.index < len(self.tracks) else None

    def add(self, track):
        if any(t.path == track.path for t in self.tracks):
            return False
        self.tracks.append(track)
        if self.index < 0:
            self.index = 0
        return True

    def select(self, index):
        if not 0 <= index < len(self.tracks):
            raise IndexError(index)
        if self.index >= 0 and self.index != index:
            self.history.append(self.index)
            self.history = self.history[-128:]
        self.index = index
        self._shuffle_seen.add(index)
        return self.current

    def next(self, *, ended=False):
        if not self.tracks:
            return None
        if ended and self.repeat == 'one':
            return self.current
        if self.shuffle and len(self.tracks) > 1:
            choices = [i for i in range(len(self.tracks)) if i not in self._shuffle_seen]
            if not choices:
                if ended and self.repeat != 'all':
                    return None
                self._shuffle_seen = {self.index}
                choices = [i for i in range(len(self.tracks)) if i != self.index]
            return self.select(self.rng.choice(choices))
        destination = self.index + 1
        if destination >= len(self.tracks):
            if ended and self.repeat != 'all':
                return None
            destination = 0
        return self.select(destination)

    def previous(self):
        if not self.tracks:
            return None
        if self.history:
            self.index = self.history.pop()
        else:
            self.index = (self.index - 1) % len(self.tracks)
        return self.current


class PlayerState:
    def __init__(self, path=None):
        config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))
        self.path = Path(path) if path else config/'novaos'/'music.json'

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                return {}
            return data
        except (OSError, ValueError):
            return {}

    def save(self, playlist, volume, ambient=False, mini=False):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {'schema_version': 1, 'volume': min(1,max(0,float(volume))),
                'repeat': playlist.repeat, 'shuffle': playlist.shuffle,
                'index': playlist.index, 'ambient': bool(ambient), 'mini': bool(mini),
                'library': [t.as_dict() for t in playlist.tracks]}
        fd, filename = tempfile.mkstemp(prefix='.music-', dir=self.path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write('\n')
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(filename, self.path)
        finally:
            if os.path.exists(filename):
                os.unlink(filename)


def restore_library(data, album):
    playlist = Playlist(album)
    for item in data.get('library', []) if isinstance(data.get('library', []), list) else []:
        try:
            track = Track.local(item['path'])
            track.title = str(item.get('title', track.title))
            track.artist = str(item.get('artist', track.artist))
            track.album = str(item.get('album', track.album))
            playlist.add(track)
        except (ValueError, TypeError, KeyError, OSError):
            continue
    try:
        index = int(data.get('index', 0))
        if 0 <= index < len(playlist.tracks):
            playlist.index = index
    except (TypeError, ValueError):
        pass
    playlist.repeat = data.get('repeat') if data.get('repeat') in ('none','one','all') else 'none'
    playlist.shuffle = data.get('shuffle') is True
    return playlist


def _runtime():
    try:
        import gi
        gi.require_version('Gtk','3.0')
        gi.require_version('Gst','1.0')
        from gi.repository import Gtk, Gst, GLib, Gio, Gdk, GdkPixbuf
    except (ImportError, ValueError) as error:
        raise RuntimeError('NovaMusic requires python3-gi, gir1.2-gtk-3.0 and '
                           'gir1.2-gstreamer-1.0 from Debian APT.') from error
    Gst.init(None)
    return Gtk, Gst, GLib, Gio, Gdk, GdkPixbuf


def probe_audio(path, timeout=20):
    """Decode through GStreamer to fakesink; this does not test audio hardware."""
    _, Gst, _, _, _, _ = _runtime()
    player = Gst.ElementFactory.make('playbin','nova-audio-probe')
    if player is None:
        raise RuntimeError('GStreamer playbin plugin is unavailable')
    try:
        for prop in ('audio-sink','video-sink'):
            sink = Gst.ElementFactory.make('fakesink',None)
            if sink is None:
                raise RuntimeError('GStreamer fakesink plugin is unavailable')
            sink.set_property('sync',False)
            player.set_property(prop,sink)
        player.set_property('uri',Path(path).resolve().as_uri())
        player.set_state(Gst.State.PLAYING)
        message=player.get_bus().timed_pop_filtered(int(timeout*Gst.SECOND),
                                                   Gst.MessageType.ERROR|Gst.MessageType.EOS)
        if message is None:
            raise RuntimeError('Audio decode timed out')
        if message.type == Gst.MessageType.ERROR:
            error,_debug=message.parse_error()
            raise RuntimeError(error.message)
        valid,duration=player.query_duration(Gst.Format.TIME)
        return {'decoded':True, 'duration_seconds':duration/Gst.SECOND if valid else None,
                'sink':'fakesink', 'hardware_playback_tested':False}
    finally:
        player.set_state(Gst.State.NULL)


def create_application():
    Gtk,Gst,GLib,Gio,Gdk,GdkPixbuf=_runtime()
    GLib.set_prgname('novaos-music')
    GLib.set_application_name('NovaMusic')

    class MusicWindow(Gtk.ApplicationWindow):
        def __init__(self, app):
            super().__init__(application=app, title='NovaMusic')
            self.set_wmclass('novaos-music','NovaMusic')
            self.set_default_size(380,700)
            self.set_size_request(300,260)
            self.state=PlayerState()
            saved=self.state.load()
            self.playlist=restore_library(saved,load_album())
            self.ambient=saved.get('ambient') is True
            self.mini=saved.get('mini') is True
            self.playing=False
            self.loaded_path=None
            self.timer=0
            self.updating=False
            self.duration=0
            self.player=Gst.ElementFactory.make('playbin','nova-music-player')
            if self.player is None:
                raise RuntimeError('GStreamer playbin is unavailable; install gstreamer1.0-plugins-base')
            if os.environ.get('NOVAOS_AUDIO_SINK') == 'fakesink':
                sink=Gst.ElementFactory.make('fakesink',None)
                sink.set_property('sync',True)
                self.player.set_property('audio-sink',sink)
            # A music player must never create an accidental video window.
            video_sink=Gst.ElementFactory.make('fakesink',None)
            self.player.set_property('video-sink',video_sink)
            bus=self.player.get_bus()
            bus.add_signal_watch()
            bus.connect('message',self.message)
            self.connect('delete-event',self.on_close)
            self.connect('key-press-event',self.keypress)
            self.connect('destroy',self.cleanup)

            outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            outer.set_border_width(16)
            # Small landscape phone screens must be able to reach the playlist.
            scroll=Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
            scroll.set_min_content_height(180)
            scroll.add(outer)
            self.add(scroll)
            self.set_icon_name('novaos-music')
            heading=Gtk.Box(spacing=8)
            brand=Gtk.Label()
            brand.set_markup('<b>NOVA</b> MUSIC')
            brand.set_xalign(0)
            heading.pack_start(brand,True,True,0)
            self.mini_button=Gtk.ToggleButton(label='Mini')
            self.mini_button.set_tooltip_text('Toggle mini-player (M)')
            self.mini_button.set_active(self.mini)
            self.mini_button.connect('toggled',self.toggle_mini)
            heading.pack_end(self.mini_button,False,False,0)
            outer.pack_start(heading,False,False,0)

            self.cover=Gtk.Image()
            cover=asset_root()/'music'/'cover.svg'
            if cover.is_file():
                try:
                    self.cover.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(cover),240,240,True))
                except GLib.Error:
                    self.cover.set_from_icon_name('audio-x-generic',Gtk.IconSize.DIALOG)
            outer.pack_start(self.cover,False,False,0)
            self.title=Gtk.Label(label='Your universe. Your music.')
            self.title.set_ellipsize(3)
            self.title.set_selectable(True)
            outer.pack_start(self.title,False,False,0)
            self.subtitle=Gtk.Label(label='Local ambient library')
            self.subtitle.set_ellipsize(3)
            outer.pack_start(self.subtitle,False,False,0)
            self.progress=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,1,1)
            self.progress.set_draw_value(False)
            self.progress.set_sensitive(False)
            self.progress.connect('change-value',self.seek)
            outer.pack_start(self.progress,False,False,0)
            self.time_label=Gtk.Label(label='0:00 / 0:00')
            outer.pack_start(self.time_label,False,False,0)
            controls=Gtk.Box(spacing=10, homogeneous=True)
            for icon,tooltip,callback in [
                ('media-skip-backward-symbolic','Previous (Ctrl+Left)',self.previous),
                ('media-playback-start-symbolic','Play / pause (Space)',self.play_pause),
                ('media-skip-forward-symbolic','Next (Ctrl+Right)',self.next),
            ]:
                button=Gtk.Button.new_from_icon_name(icon,Gtk.IconSize.LARGE_TOOLBAR)
                button.set_size_request(64,44)
                button.set_tooltip_text(tooltip)
                button.connect('clicked',callback)
                controls.pack_start(button,True,True,0)
                if icon == 'media-playback-start-symbolic':
                    self.play_button=button
            outer.pack_start(controls,False,False,0)
            volume_row=Gtk.Box(spacing=8)
            volume_row.pack_start(Gtk.Label(label='Volume'),False,False,0)
            self.volume=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,1,.02)
            self.volume.set_draw_value(False)
            try:
                volume=float(saved.get('volume',.65))
            except (TypeError,ValueError):
                volume=.65
            self.volume.set_value(min(1,max(0,volume)))
            self.player.set_property('volume',self.volume.get_value())
            self.volume.connect('value-changed',lambda slider:self.player.set_property('volume',slider.get_value()))
            volume_row.pack_start(self.volume,True,True,0)
            outer.pack_start(volume_row,False,False,0)

            self.expanded=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
            mode_row=Gtk.Box(spacing=8)
            self.shuffle=Gtk.ToggleButton(label='Shuffle')
            self.shuffle.set_active(self.playlist.shuffle)
            self.shuffle.connect('toggled',lambda button:setattr(self.playlist,'shuffle',button.get_active()))
            mode_row.pack_start(self.shuffle,False,False,0)
            self.repeat=Gtk.ComboBoxText()
            for key,label in [('none','Repeat off'),('all','Repeat album'),('one','Repeat track')]:
                self.repeat.append(key,label)
            self.repeat.set_active_id(self.playlist.repeat)
            self.repeat.connect('changed',lambda combo:setattr(self.playlist,'repeat',combo.get_active_id()))
            mode_row.pack_end(self.repeat,False,False,0)
            self.expanded.pack_start(mode_row,False,False,0)
            self.ambient_button=Gtk.CheckButton(label='Ambient Desktop')
            self.ambient_button.set_tooltip_text('Closing minimizes this window and keeps local music playing. Ctrl+Q always quits.')
            self.ambient_button.set_active(self.ambient)
            self.ambient_button.connect('toggled',lambda button:setattr(self,'ambient',button.get_active()))
            self.expanded.pack_start(self.ambient_button,False,False,0)
            self.model=Gtk.ListStore(int,str,str)
            self.tree=Gtk.TreeView(model=self.model)
            self.tree.set_headers_visible(False)
            self.tree.append_column(Gtk.TreeViewColumn('Track',Gtk.CellRendererText(),text=1))
            self.tree.set_tooltip_column(2)
            self.tree.connect('row-activated',self.row_activated)
            scroll=Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC)
            scroll.set_min_content_height(110)
            scroll.add(self.tree)
            self.expanded.pack_start(scroll,True,True,0)
            import_button=Gtk.Button(label='Add local music…')
            import_button.set_size_request(-1,38)
            import_button.connect('clicked',self.import_files)
            self.expanded.pack_start(import_button,False,False,0)
            outer.pack_start(self.expanded,True,True,0)
            self.status=Gtk.Label(label='Offline playback · original ambient album')
            self.status.set_line_wrap(True)
            outer.pack_start(self.status,False,False,0)
            self.populate()
            self.update_track_labels()
            self.show_all()
            self.apply_mini()

        def populate(self):
            self.model.clear()
            for i,track in enumerate(self.playlist.tracks):
                self.model.append([i,f'{i+1:02d}   {track.title}',str(track.path)])
            if self.playlist.index >= 0:
                self.tree.get_selection().select_path(self.playlist.index)

        def update_track_labels(self):
            track=self.playlist.current
            if track:
                self.title.set_text(track.title)
                self.subtitle.set_text(f'{track.artist} · {track.album}')
                self.tree.get_selection().select_path(self.playlist.index)
            self.play_button.set_sensitive(track is not None)
            self.publish_playback()

        def publish_playback(self):
            # Private local IPC for the native desktop cards; no network service.
            from .desktop_widgets import playback_path
            from .config import atomic_write
            import psutil
            track=self.playlist.current
            valid, position=self.player.query_position(Gst.Format.TIME)
            payload={'pid':os.getpid(), 'created':psutil.Process().create_time(),
                     'title':track.title if track else 'NovaMusic',
                     'artist':track.artist if track else 'Biblioteca local',
                     'playing':self.playing, 'duration':self.duration,
                     'position':max(0,position/Gst.SECOND) if valid else 0}
            try:
                path=playback_path()
                path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                atomic_write(path,json.dumps(payload))
            except OSError:
                pass

        def set_playing(self,playing):
            self.playing=playing
            icon='media-playback-pause-symbolic' if playing else 'media-playback-start-symbolic'
            self.play_button.set_image(Gtk.Image.new_from_icon_name(icon,Gtk.IconSize.LARGE_TOOLBAR))
            if playing and not self.timer:
                self.timer=GLib.timeout_add_seconds(1,self.update_progress)
            elif not playing and self.timer:
                GLib.source_remove(self.timer)
                self.timer=0
            self.publish_playback()

        def start(self):
            track=self.playlist.current
            if track is None:
                self.status.set_text('Add local audio files to begin.')
                return
            self.player.set_state(Gst.State.NULL)
            self.player.set_property('uri',track.path.as_uri())
            self.loaded_path=track.path
            self.duration=0
            self.progress.set_value(0)
            self.player.set_state(Gst.State.PLAYING)
            self.set_playing(True)
            self.update_track_labels()
            self.status.set_text('Playing locally')

        def play_pause(self,*_args):
            if self.playing:
                self.player.set_state(Gst.State.PAUSED)
                self.set_playing(False)
                self.status.set_text('Paused')
            elif self.playlist.current and self.loaded_path == self.playlist.current.path:
                self.player.set_state(Gst.State.PLAYING)
                self.set_playing(True)
                self.status.set_text('Playing locally')
            else:
                self.start()

        def next(self,*_args):
            if self.playlist.next():
                self.start()

        def previous(self,*_args):
            if self.playlist.previous():
                self.start()

        def row_activated(self,_tree,path,_column):
            self.playlist.select(path.get_indices()[0])
            self.start()

        @staticmethod
        def time_text(seconds):
            seconds=max(0,int(seconds))
            return f'{seconds//60}:{seconds%60:02d}'

        def update_progress(self):
            ok,duration=self.player.query_duration(Gst.Format.TIME)
            valid,position=self.player.query_position(Gst.Format.TIME)
            if ok and duration > 0:
                self.duration=duration/Gst.SECOND
                if self.playlist.current:
                    self.playlist.current.duration=self.duration
                self.progress.set_range(0,self.duration)
                self.progress.set_sensitive(True)
            if valid and position >= 0:
                self.updating=True
                self.progress.set_value(position/Gst.SECOND)
                self.updating=False
                self.time_label.set_text(f'{self.time_text(position/Gst.SECOND)} / {self.time_text(self.duration)}')
            self.publish_playback()
            return True

        def seek(self,_scale,_scroll,value):
            if not self.updating and self.duration > 0:
                self.player.seek_simple(Gst.Format.TIME,Gst.SeekFlags.FLUSH|Gst.SeekFlags.KEY_UNIT,
                                        int(min(self.duration,max(0,value))*Gst.SECOND))
            return False

        def message(self,_bus,message):
            if message.type == Gst.MessageType.EOS:
                if self.playlist.next(ended=True):
                    self.start()
                else:
                    self.player.set_state(Gst.State.NULL)
                    self.loaded_path=None
                    self.set_playing(False)
                    self.status.set_text('Playlist finished')
            elif message.type == Gst.MessageType.ERROR:
                error,_debug=message.parse_error()
                self.player.set_state(Gst.State.NULL)
                self.loaded_path=None
                self.set_playing(False)
                self.status.set_text(f'Audio error: {error.message}')
            elif message.type == Gst.MessageType.TAG and self.playlist.current:
                tags=message.parse_tag()
                track=self.playlist.current
                for tag,attribute in [('title','title'),('artist','artist'),('album','album')]:
                    valid,value=tags.get_string(tag)
                    if valid:
                        setattr(track,attribute,value)
                self.update_track_labels()
                iterator=self.model.get_iter_from_string(str(self.playlist.index))
                if iterator is not None:
                    self.model.set_value(iterator,1,f'{self.playlist.index+1:02d}   {track.title}')
            elif message.type in (Gst.MessageType.DURATION_CHANGED,Gst.MessageType.ASYNC_DONE):
                self.update_progress()

        def import_files(self,*_args):
            chooser=Gtk.FileChooserDialog(title='Add local audio',transient_for=self,
                                           action=Gtk.FileChooserAction.OPEN)
            chooser.add_buttons('Cancel',Gtk.ResponseType.CANCEL,'Add',Gtk.ResponseType.OK)
            chooser.set_select_multiple(True)
            audio=Gtk.FileFilter()
            audio.set_name('Audio files')
            for suffix in sorted(SUPPORTED):
                audio.add_pattern('*'+suffix)
                audio.add_pattern('*'+suffix.upper())
            chooser.add_filter(audio)
            if chooser.run() == Gtk.ResponseType.OK:
                added=0
                for filename in chooser.get_filenames():
                    try:
                        added+=self.playlist.add(Track.local(filename))
                    except (ValueError,OSError):
                        continue
                self.populate()
                self.update_track_labels()
                self.save()
                self.status.set_text(f'{added} local file(s) added')
            chooser.destroy()

        def apply_mini(self):
            self.cover.set_visible(not self.mini)
            self.expanded.set_visible(not self.mini)
            self.resize(340 if self.mini else 380,300 if self.mini else 700)

        def toggle_mini(self,button):
            self.mini=button.get_active()
            if hasattr(self,'expanded'):
                self.apply_mini()

        def keypress(self,_window,event):
            control=bool(event.state&Gdk.ModifierType.CONTROL_MASK)
            if control and event.keyval in (Gdk.KEY_q,Gdk.KEY_Q):
                self.destroy()
                return True
            if control and event.keyval in (Gdk.KEY_o,Gdk.KEY_O):
                self.import_files()
                return True
            if control and event.keyval == Gdk.KEY_Right:
                self.next()
                return True
            if control and event.keyval == Gdk.KEY_Left:
                self.previous()
                return True
            if event.keyval == Gdk.KEY_space:
                self.play_pause()
                return True
            if event.keyval in (Gdk.KEY_m,Gdk.KEY_M):
                self.mini_button.set_active(not self.mini)
                return True
            return False

        def save(self):
            try:
                self.state.save(self.playlist,self.volume.get_value(),self.ambient,self.mini)
            except OSError as error:
                self.status.set_text(f'Could not save preferences: {error}')

        def on_close(self,*_args):
            self.save()
            if self.ambient:
                self.iconify()
                return True
            return False

        def cleanup(self,*_args):
            self.save()
            self.set_playing(False)
            self.player.set_state(Gst.State.NULL)
            self.player.get_bus().remove_signal_watch()
            from .desktop_widgets import playback_path
            try:
                playback_path().unlink(missing_ok=True)
            except OSError:
                pass
            self.get_application().window=None

    class MusicApplication(Gtk.Application):
        def __init__(self):
            super().__init__(application_id='org.novaos.Music',flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
            self.window=None

        def do_activate(self):
            if self.window is None:
                self.window=MusicWindow(self)
            self.window.present()

        def do_command_line(self,command_line):
            arguments=command_line.get_arguments()[1:]
            if '--background' in arguments:
                if self.window is None:
                    self.window=MusicWindow(self)
                    self.window.hide()
            else:
                self.activate()
            for argument in arguments:
                if argument == '--toggle':
                    self.window.play_pause()
                elif argument == '--next':
                    self.window.next()
                elif argument == '--previous':
                    self.window.previous()
                elif argument == '--mini':
                    self.window.mini_button.set_active(True)
                elif argument == '--ambient':
                    self.window.ambient_button.set_active(True)
            return 0

    return MusicApplication()


def main(argv=None):
    arguments=list(argv) if argv is not None else []
    parser=argparse.ArgumentParser(prog='novaos music',description='NovaMusic local GTK/GStreamer player')
    parser.add_argument('--mini',action='store_true',help='Open the mini-player')
    parser.add_argument('--ambient',action='store_true',help='Keep playing when the window is minimized on close')
    parser.add_argument('--toggle',action='store_true',help='Play or pause the current track')
    parser.add_argument('--next',action='store_true',help='Play the next track')
    parser.add_argument('--previous',action='store_true',help='Play the previous track')
    parser.add_argument('--background',action='store_true',help='Control or start the player without raising its window')
    parser.add_argument('--audio-test',metavar='PATH',help='Decode local audio to a test sink (no hardware output)')
    options=parser.parse_args(arguments)
    if options.audio_test:
        try:
            print(json.dumps(probe_audio(options.audio_test),indent=2))
            return 0
        except (RuntimeError,OSError) as error:
            print(str(error),file=sys.stderr)
            return 1
    try:
        return create_application().run(['novaos-music',*arguments])
    except RuntimeError as error:
        print(str(error),file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
