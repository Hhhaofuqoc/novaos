#!/usr/bin/python3
"""Real integration test; no fake GTK windows, virtual WM, or mocked audio decoder.

Xvfb supplies a software display. Audio uses GStreamer fakesink, so no sound-card
or physical Android claims can be inferred from a successful run.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import signal
import subprocess
import sys
import time
import traceback

import psutil

WORK = Path(os.environ['NOVAOS_TEST_WORK'])
REPORT = Path(os.environ['NOVAOS_TEST_REPORT'])
PROCESSES = []
LOGS = []
RESULT = {
    'schema_version': 1,
    'environment': {'architecture': platform.machine(), 'kernel': platform.release(),
                    'python': platform.python_version(), 'display': 'Xvfb software X11',
                    'memory_total_bytes': psutil.virtual_memory().total},
    'scope': 'Native Linux integration; not Android, PRoot, ISO boot or hardware audio validation',
    'network_isolation': os.environ.get('NOVAOS_TEST_NETWORK_ISOLATION',
                                       'not enforced; tested workflows access local files only'),
    'checks': [], 'metrics': {}, 'errors': [],
}


def run(args, **kw):
    return subprocess.run(args, text=True, capture_output=True, check=True, **kw)


def launch(args, label):
    log = open(REPORT / f'{label}.log', 'w', encoding='utf-8')
    LOGS.append(log)
    process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=True)
    PROCESSES.append(process)
    return process


def eventually(test, timeout=12, description='condition'):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = test()
            if result:
                return result
        except (subprocess.CalledProcessError, ProcessLookupError):
            pass
        time.sleep(.12)
    raise AssertionError(f'Timed out waiting for {description}')


def check(name, details=True):
    RESULT['checks'].append({'name': name, 'passed': True, 'details': details})
    print(f'PASS {name}', flush=True)


def windows():
    data = run(['wmctrl', '-l']).stdout
    return [line.split(None, 3) for line in data.splitlines() if len(line.split(None, 3)) == 4]


def window_for(title):
    for row in windows():
        if title in row[3]:
            return row[0]
    return None


def properties(wid, prop):
    return run(['xprop', '-id', wid, prop]).stdout


def geometry(wid):
    result = run(['xdotool', 'getwindowgeometry', '--shell', str(int(wid, 16))]).stdout
    return {key: int(value) for key, value in (line.split('=', 1) for line in result.splitlines())}


def close_window(wid, process):
    run(['wmctrl', '-ic', wid])
    eventually(lambda: not any(row[0] == wid for row in windows()), description='window closure')
    eventually(lambda: process.poll() is not None, description='application exit')
    if process.returncode:
        raise AssertionError(f'Application exited with {process.returncode}')


def main():
    # Select an unused local X socket and use MIT-MAGIC-COOKIE authentication.
    display_number = next(n for n in range(170, 220)
                          if not Path(f'/tmp/.X11-unix/X{n}').exists()
                          and not Path(f'/tmp/.X{n}-lock').exists())
    os.environ['DISPLAY'] = f':{display_number}'
    Path(os.environ['XAUTHORITY']).touch(mode=0o600)
    run(['xauth', '-f', os.environ['XAUTHORITY'], 'add', os.environ['DISPLAY'],
         '.', secrets.token_hex(16)])
    launch(['Xvfb', os.environ['DISPLAY'], '-screen', '0', '1600x900x24',
            '-nolisten', 'tcp', '-noreset', '-auth', os.environ['XAUTHORITY']], 'xvfb')
    eventually(lambda: subprocess.run(['xdpyinfo'], stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL).returncode == 0,
               description='Xvfb')
    run(['dbus-update-activation-environment', 'DISPLAY', 'XAUTHORITY', 'HOME',
         'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_DATA_DIRS'])
    launch(['xfwm4', '--compositor=off', '--replace'], 'xfwm4')
    eventually(lambda: '_NET_SUPPORTING_WM_CHECK(WINDOW)' in
               run(['xprop', '-root', '_NET_SUPPORTING_WM_CHECK']).stdout,
               description='XFWM window manager')
    launch(['xfsettingsd', '--no-daemon'], 'xfsettingsd')
    launch(['xfdesktop', '--disable-wm-check'], 'xfdesktop')
    launch(['xfce4-panel', '--disable-wm-check'], 'panel-initial')
    time.sleep(1)
    check('x11_real_xfwm4_started')
    assets = Path(os.environ['NOVAOS_ASSETS'])
    applied = run(['bash', str(assets / 'themes/apply-xfce.sh'), 'lite', 'dark'])
    (REPORT / 'theme-apply.log').write_text(applied.stdout + applied.stderr, encoding='utf-8')
    assert run(['xfconf-query', '-c', 'xsettings', '-p', '/Net/ThemeName']).stdout.strip() == 'NovaOS-Dark'
    assert run(['xfconf-query', '-c', 'xfwm4', '-p', '/general/use_compositing']).stdout.strip() == 'false'
    check('real_theme_applied_lite')
    wallpaper = run(['xfconf-query', '-c', 'xfce4-desktop', '-lv']).stdout
    assert str(assets/'wallpapers/novaos-desktop.png') in wallpaper, wallpaper
    assert not window_for('Plugin loading failure'), 'Missing required XFCE panel plugin'
    check('wallpaper_configured_and_panel_plugins_load')
    # Reapplying must preserve an intentional user's change to the panel.
    run(['xfconf-query', '-c', 'xfce4-panel', '-p', '/panels/panel-1/size', '-s', '47'])
    run(['bash', str(assets / 'themes/apply-xfce.sh'), 'lite', 'dark'])
    assert run(['xfconf-query', '-c', 'xfce4-panel', '-p', '/panels/panel-1/size']).stdout.strip() == '47'
    check('theme_update_preserves_panel_customization')
    check('staged_install_and_reinstall_preserve_user_files')

    apps = {}
    for command, title in [('welcome', 'NovaWelcome'), ('settings', 'NovaSettings'),
                           ('monitor', 'NovaMonitor'), ('notes', 'NovaNotes'),
                           ('music', 'NovaMusic'), ('store', 'NovaStore'), ('updater', 'NovaUpdater')]:
        proc = launch(['novaos', command], f'app-{command}')
        wid = eventually(lambda: window_for(title), description=title)
        assert proc.poll() is None, f'{title} exited early'
        apps[command] = (proc, wid)
        check(f'launch_{command}', {'window': wid, 'pid': proc.pid})

    proc, wid = apps['notes']
    run(['wmctrl', '-ia', wid])
    run(['wmctrl', '-ir', wid, '-e', '0,90,110,690,470'])
    eventually(lambda: abs(geometry(wid)['WIDTH'] - 690) < 10,
               description='window resize')
    original = geometry(wid)
    assert original['X'] >= 50 and original['Y'] >= 50
    check('window_move_resize', original)
    # Real keyboard input reaches GtkTextView, then survives forced process death.
    note_path = Path(os.environ['XDG_DATA_HOME']) / 'novaos/notes.txt'
    test_note = 'NovaOS real X11 persistence test'
    run(['xdotool', 'mousemove', '--window', str(int(wid, 16)), '180', '190', 'click', '1'])
    run(['xdotool', 'type', '--clearmodifiers', '--delay', '8', test_note])
    eventually(lambda: note_path.exists() and note_path.read_text() == test_note,
               description='notes autosave')
    os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=5)
    eventually(lambda: not window_for('NovaNotes'), description='crashed window removal')
    proc = launch(['novaos', 'notes'], 'app-notes-recovered')
    wid = eventually(lambda: window_for('NovaNotes'), description='notes restart after crash')
    apps['notes'] = (proc, wid)
    run(['wmctrl', '-ia', wid])
    run(['xdotool', 'mousemove', '--window', str(int(wid, 16)), '180', '190', 'click', '1'])
    run(['xdotool', 'key', '--clearmodifiers', 'ctrl+End'])
    run(['xdotool', 'type', '--clearmodifiers', '--delay', '8', ' recovered'])
    eventually(lambda: note_path.read_text() == test_note + ' recovered',
               description='loaded notes appended after crash')
    check('notes_autosave_and_crash_recovery')
    run(['wmctrl', '-ir', wid, '-b', 'add,maximized_vert,maximized_horz'])
    eventually(lambda: '_NET_WM_STATE_MAXIMIZED_HORZ' in properties(wid, '_NET_WM_STATE'),
               description='maximize')
    check('window_maximize')
    run(['wmctrl', '-ir', wid, '-b', 'remove,maximized_vert,maximized_horz'])
    run(['xdotool', 'windowminimize', str(int(wid, 16))])
    eventually(lambda: 'Iconic' in properties(wid, 'WM_STATE'), description='minimize')
    check('window_minimize')
    run(['wmctrl', '-ia', wid])
    eventually(lambda: 'Normal' in properties(wid, 'WM_STATE'), description='restore')
    run(['wmctrl', '-n', '2'])
    run(['wmctrl', '-s', '1'])
    eventually(lambda: '= 1' in run(['xprop', '-root', '_NET_CURRENT_DESKTOP']).stdout,
               description='desktop switch')
    run(['wmctrl', '-s', '0'])
    check('multiple_workspaces')

    # Sample CPU time across 4 seconds, with all seven native apps open and idle.
    tracked = []
    for item in PROCESSES:
        try:
            parent = psutil.Process(item.pid)
            tracked += [parent, *parent.children(recursive=True)]
        except psutil.NoSuchProcess:
            pass
    tracked = list({p.pid: p for p in tracked}.values())
    def sample():
        result = {}
        for process in tracked:
            try:
                cpu = process.cpu_times()
                result[process.pid] = (cpu.user + cpu.system, process.memory_info().rss)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return result
    before = sample()
    began = time.monotonic()
    time.sleep(4)
    after = sample()
    elapsed = time.monotonic() - began
    delta = sum(max(0, after[p][0] - before[p][0]) for p in after.keys() & before.keys())
    RESULT['metrics'] = {
        'sample_seconds': elapsed, 'summed_rss_bytes': sum(v[1] for v in after.values()),
        'cpu_one_core_percent': delta / elapsed * 100,
        'tracked_processes': len(after),
        'note': 'Includes tracked Xvfb, XFWM, XFCE components and seven apps; RSS double-counts shared pages. '
                'Cloud x86_64 measurement, not a RAM minimum or Android performance prediction.',
        'apps': {name: {'rss_bytes': psutil.Process(p.pid).memory_info().rss}
                 for name, (p, _) in apps.items()},
    }
    check('measured_idle_cpu_and_memory', RESULT['metrics'])

    from novaos.music import load_album, probe_audio
    tracks = load_album()
    assert len(tracks) == 12, f'Expected generated album, found {len(tracks)} tracks'
    decodes = []
    for track in tracks:
        decoded = probe_audio(track.path)
        assert decoded['decoded']
        decodes.append({'title': track.title, **decoded})
    check('all_12_tracks_decode_gstreamer', decodes)

    # Capture the actual native desktop, then close windows through the WM.
    for command, (_p, app_wid) in apps.items():
        run(['wmctrl', '-ir', app_wid, '-b', 'remove,maximized_vert,maximized_horz'])
        if command not in ('music', 'monitor'):
            run(['xdotool', 'windowminimize', str(int(app_wid,16))])
    run(['wmctrl', '-ir', apps['music'][1], '-e', '0,1160,80,400,690'])
    run(['wmctrl', '-ir', apps['monitor'][1], '-e', '0,55,110,520,480'])
    run(['wmctrl', '-ia', apps['monitor'][1]])
    run(['wmctrl', '-ia', apps['music'][1]])
    run(['xdotool', 'mousemove', '800', '895'])
    time.sleep(.5)
    if shutil.which('import'):
        run(['import', '-window', 'root', str(REPORT / 'native-desktop.png')])
        check('native_desktop_screenshot', 'native-desktop.png')
    for command, (app_proc, app_wid) in apps.items():
        close_window(app_wid, app_proc)
    check('all_native_apps_close_cleanly')


try:
    main()
except Exception as error:
    RESULT['errors'].append({'type': type(error).__name__, 'message': str(error),
                             'traceback': traceback.format_exc()})
    traceback.print_exc()
finally:
    # Only terminate process groups created by this test, never arbitrary sessions.
    for proc in reversed(PROCESSES):
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for proc in reversed(PROCESSES):
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=3)
    for log in LOGS:
        log.close()
    RESULT['passed'] = not RESULT['errors']
    (REPORT / 'integration.json').write_text(json.dumps(RESULT, indent=2) + '\n', encoding='utf-8')
    print(f'Report: {REPORT / "integration.json"}', flush=True)
    sys.exit(0 if RESULT['passed'] else 1)
