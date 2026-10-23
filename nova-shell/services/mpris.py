"""Controles MPRIS reais; funcional apenas se houver player compatível."""
from gi.repository import Gio, GLib

class Mpris:
    def __init__(self): self.name = None; self.bus = None
    def refresh(self):
        try:
            if self.bus is None: self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            ans = self.bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                  'org.freedesktop.DBus', 'ListNames', None, GLib.VariantType('(as)'),
                  Gio.DBusCallFlags.NONE, 550, None)
            names = [n for n in ans.unpack()[0] if n.startswith('org.mpris.MediaPlayer2.')]
            self.name = names[0] if names else None
            if not self.name: return None
            props = self.bus.call_sync(self.name, '/org/mpris/MediaPlayer2',
                      'org.freedesktop.DBus.Properties', 'GetAll',
                      GLib.Variant('(s)', ('org.mpris.MediaPlayer2.Player',)),
                      GLib.VariantType('(a{sv})'), Gio.DBusCallFlags.NONE, 550, None)
            values = props.unpack()[0]
            meta = values.get('Metadata') or {}
            return {'title': meta.get('xesam:title', 'Sem título'),
                    'artist': ', '.join(meta.get('xesam:artist', [])),
                    'length': meta.get('mpris:length'),
                    'position': values.get('Position'),
                    'art': meta.get('mpris:artUrl'),
                    'playing': values.get('PlaybackStatus') == 'Playing'}
        except (GLib.Error, AttributeError, ValueError, TypeError): return None
    def control(self, method):
        if not self.name or method not in ('PlayPause','Next','Previous'): return False
        try:
            self.bus.call_sync(self.name, '/org/mpris/MediaPlayer2',
                'org.mpris.MediaPlayer2.Player', method, None, None,
                Gio.DBusCallFlags.NONE, 600, None)
            return True
        except GLib.Error: return False
