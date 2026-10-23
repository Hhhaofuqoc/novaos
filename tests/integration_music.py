#!/usr/bin/env python3
"""Opt-in real GTK/GStreamer integration. Requires DISPLAY and a D-Bus session.

Run: NOVAOS_AUDIO_SINK=fakesink dbus-run-session -- xvfb-run -a \
     /usr/bin/python3 tests/integration_music.py
No audio hardware is exercised by this test.
"""
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'applications'))
os.environ['NOVAOS_ASSETS']=str(ROOT)
os.environ['NOVAOS_AUDIO_SINK']='fakesink'


def main():
    from novaos.music import create_application, _runtime
    Gtk,Gst,GLib,_,_,_= _runtime()
    events=[]
    def pump(seconds=.12):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            while GLib.MainContext.default().pending():
                GLib.MainContext.default().iteration(False)
            time.sleep(.005)
    def check(condition,name):
        if not condition:
            raise AssertionError(name)
        events.append(name)
    with tempfile.TemporaryDirectory(prefix='nova-music-gui-') as directory:
        os.environ['XDG_CONFIG_HOME']=directory
        app=create_application()
        check(app.register(None),'application registration')
        app.activate()
        pump()
        window=app.window
        try:
            check(window is not None and window.get_visible(),'real GTK window opens')
            window.resize(360,420)
            pump()
            scroll=window.get_child()
            adjustment=scroll.get_vadjustment()
            check(window.get_size().height <= 420 and adjustment.get_upper() > adjustment.get_page_size(),
                  'small landscape window scrolls to all controls')
            check(len(window.playlist.tracks)==12,'12 local tracks loaded')
            window.play_pause()
            pump(1.2)
            result,state,_=window.player.get_state(2*Gst.SECOND)
            valid,position=window.player.query_position(Gst.Format.TIME)
            check(state==Gst.State.PLAYING and valid and position>0,'real GStreamer playback position advances')
            window.play_pause()
            pump()
            _,state,_=window.player.get_state(2*Gst.SECOND)
            check(state==Gst.State.PAUSED,'pause reaches Gst PAUSED')
            window.seek(None,None,20)
            pump()
            valid,position=window.player.query_position(Gst.Format.TIME)
            check(valid and 19.8<=position/Gst.SECOND<=20.2,'seek reaches 20 seconds')
            window.next()
            pump()
            check(window.playlist.index==1 and window.title.get_text()=='Purple Orbit','next loads track and metadata')
            window.previous()
            pump()
            check(window.playlist.index==0,'previous returns to actual prior track')
            window.volume.set_value(.27)
            check(abs(window.player.get_property('volume')-.27)<.001,'volume changes real pipeline')
            window.shuffle.set_active(True)
            window.repeat.set_active_id('all')
            check(window.playlist.shuffle and window.playlist.repeat=='all','shuffle and repeat UI change backend')
            window.mini_button.set_active(True)
            pump()
            check(not window.expanded.get_visible() and not window.cover.get_visible(),'mini-player hides expanded interface')
            window.mini_button.set_active(False)
            pump()
            if shutil.which('xdotool'):
                windows=subprocess.check_output(['xdotool','search','--name','^NovaMusic$'],text=True).split()
                if windows:
                    subprocess.run(['xdotool','key','--window',windows[-1],'space'],check=True)
                    pump()
                    check(not window.playing,'X11 Space key pauses playback')
            window.ambient_button.set_active(True)
            check(window.on_close() is True and app.window is window,'Ambient close keeps application alive')
            window.save()
            config=Path(directory)/'novaos'/'music.json'
            saved=json.loads(config.read_text())
            check(saved['ambient'] and abs(saved['volume']-.27)<.001,'GUI state persisted to disk')
            # Full EOS handling through the real playbin, near the track end.
            window.ambient_button.set_active(False)
            window.shuffle.set_active(False)
            window.repeat.set_active_id('none')
            window.playlist.select(len(window.playlist.tracks)-1)
            window.start()
            pump(.2)
            window.seek(None,None,71.8)
            pump(.8)
            check(not window.playing and window.status.get_text()=='Playlist finished','real EOS stops final track without repeat')
            window.destroy()
            pump()
            check(app.window is None,'window destroy releases app reference')
            check(window.player.get_state(0)[1]==Gst.State.NULL,'quit releases GStreamer pipeline')
        finally:
            if app.window is not None:
                app.window.destroy()
            app.quit()
    report={'checks':events,'checks_passed':len(events),'backend':'GTK3 + GStreamer + Xvfb',
            'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'hardware_playback_tested':False,'android_tested':False}
    target=Path(os.environ.get('NOVAOS_MUSIC_TEST_REPORT', ROOT/'music'/'generated'/'gui-verification.json'))
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
