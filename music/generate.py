#!/usr/bin/env python3
"""Generate NovaOS's original procedural ambient album without sampled audio.

Synthesis is deterministic for the same NumPy/encoder versions. Each stereo
track is rendered independently; no external recordings, MIDI or SoundFonts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import wave

TITLES = [
    'Neon Rain', 'Purple Orbit', 'Quiet Terminal', 'Digital Memories',
    'Blue Horizon', 'Floating Pixels', 'Midnight Kernel', 'Soft Geometry',
    'Distant Satellites', 'Empty Desktop', 'Celestial Code', 'Nova Dreams',
]
# Original four-voice progressions: semitone intervals above the track tonic.
PROGRESSIONS = [
    [(0, 3, 7, 14), (5, 8, 12, 19), (8, 12, 15, 22), (3, 7, 10, 17)],
    [(0, 4, 7, 11), (7, 11, 14, 21), (9, 12, 16, 19), (5, 9, 12, 16)],
    [(0, 2, 7, 12), (7, 10, 14, 19), (3, 7, 10, 14), (5, 9, 12, 17)],
]


def frequency(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)


def synthesize(index: int, seconds: float = 72.0, sample_rate: int = 44100):
    """Return float32 stereo audio; normalized peak <= 0.72 with soft edges."""
    import numpy as np
    if not 0 <= index < len(TITLES):
        raise ValueError('track index must be between 0 and 11')
    if seconds < 2 or seconds > 600 or not 8000 <= sample_rate <= 96000:
        raise ValueError('duration 2–600 seconds; sample rate 8000–96000 Hz')
    rng = np.random.default_rng(73011 + index * 1009)
    length = int(seconds * sample_rate)
    signal = np.zeros((length, 2), dtype=np.float32)
    root = [45, 48, 42, 50, 43, 47, 40, 46, 49, 44, 51, 41][index]
    progression = PROGRESSIONS[index % len(PROGRESSIONS)]
    bar = 7.2 + (index % 4) * .55

    def add_note(start, duration, midi, gain, instrument, pan):
        begin = int(start * sample_rate)
        if begin >= length:
            return
        count = min(int(duration * sample_rate), length - begin)
        time = np.arange(count, dtype=np.float32) / sample_rate
        hz = frequency(midi)
        if instrument == 'pad':
            attack = np.minimum(time / 1.9, 1)
            release = np.minimum((duration - time) / 3.8, 1)
            envelope = np.maximum(0, attack * release) ** 1.5
            # Gentle oscillator drift and an intentionally subdued overtone.
            oscillator = (
                np.sin(2*np.pi*hz*time + .07*np.sin(time*.63))
                + .32*np.sin(2*np.pi*hz*1.0021*time)
                + .12*np.sin(2*np.pi*hz*2*time)
            ) / 1.44
        elif instrument == 'piano':
            attack = 1-np.exp(-time*65)
            envelope = attack * np.exp(-time / 2.4)
            oscillator = (
                np.sin(2*np.pi*hz*time)
                + .29*np.sin(2*np.pi*hz*2.001*time)*np.exp(-time*1.3)
                + .10*np.sin(2*np.pi*hz*3.005*time)*np.exp(-time*2.2)
            ) / 1.39
            envelope *= np.minimum(np.maximum(duration-time, 0)/.3, 1)
        else:
            envelope = (1-np.exp(-time*110))*np.exp(-time/1.8)
            envelope *= np.minimum(np.maximum(duration-time, 0)/.5, 1)
            oscillator = (np.sin(2*np.pi*hz*time) + .12*np.sin(2*np.pi*hz*2.75*time))/1.12
        voice = np.asarray(oscillator*envelope*gain, dtype=np.float32)
        signal[begin:begin+count, 0] += voice*np.sqrt((1-pan)/2)
        signal[begin:begin+count, 1] += voice*np.sqrt((1+pan)/2)

    beat_count = int(seconds / bar) + 1
    for chord_i in range(beat_count):
        chord = progression[chord_i % len(progression)]
        start = chord_i * bar
        for voice, interval in enumerate(chord):
            add_note(start, bar + 3.4, root+interval, .055, 'pad', (voice-1.5)/2.6)
        # Sparse, non-repeating original phrase with breathing room.
        for note_i in range(4):
            if rng.random() < .21:
                continue
            degree = chord[(note_i + chord_i + index) % 4]
            displacement = [0, 12, 0, -12][(note_i+index) % 4]
            add_note(start + .4 + note_i*bar/4 + float(rng.uniform(-.08,.08)),
                     5.6, root+degree+12+displacement,
                     float(rng.uniform(.07,.12)), 'piano', float(rng.uniform(-.55,.55)))
        if chord_i % 2 == index % 2:
            add_note(start+bar*.69, 5.2, root+chord[-1]+24, .026, 'crystal', .48)

    # Three short fixed diffuse echoes, bounded and cheap at playback (baked in).
    dry = signal.copy()
    for delay, level in [(.317,.14), (.719,.09), (1.127,.055)]:
        shift = int(delay*sample_rate)
        if shift < length:
            signal[shift:] += dry[:-shift, ::-1]*level
    peak = float(np.max(np.abs(signal)))
    if peak:
        signal *= .72 / peak
    fade = min(int(3.5*sample_rate), length//3)
    if fade:
        ramp = np.sin(np.linspace(0, np.pi/2, fade, dtype=np.float32))**2
        signal[:fade] *= ramp[:, None]
        signal[-fade:] *= ramp[::-1, None]
    return signal


def write_track(destination: Path, index: int, seconds: float, sample_rate: int, codec: str):
    import numpy as np
    samples = synthesize(index, seconds, sample_rate)
    pcm = np.round(samples * 32767).astype('<i2')
    wav_path = destination / f'{index+1:02d}-{TITLES[index].lower().replace(" ", "-")}.wav'
    with wave.open(str(wav_path), 'wb') as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    result = wav_path
    if codec == 'flac':
        result = wav_path.with_suffix('.flac')
        subprocess.run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
            '-i', str(wav_path), '-c:a', 'flac', '-compression_level', '8',
            '-metadata', f'title={TITLES[index]}', '-metadata', 'artist=NovaOS',
            '-metadata', 'album=Your Universe', '-metadata', f'track={index+1}/12',
            '-metadata', 'copyright=CC0-1.0; original procedural synthesis', str(result)
        ], check=True)
        wav_path.unlink()
    return {
        'id': f'nova-{index+1:02d}', 'title': TITLES[index], 'artist': 'NovaOS',
        'album': 'Your Universe', 'track': index+1, 'path': result.name,
        'duration_seconds': len(samples)/sample_rate, 'sample_rate': sample_rate,
        'channels': 2, 'bits_per_sample': 16, 'license': 'CC0-1.0',
        'sha256': hashlib.sha256(result.read_bytes()).hexdigest(),
        'peak': round(float(np.abs(samples).max()), 7),
        'rms': round(float(np.sqrt(np.mean(samples**2))), 7),
        'bytes': result.stat().st_size,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent/'generated')
    parser.add_argument('--seconds', type=float, default=72.0)
    parser.add_argument('--sample-rate', type=int, default=44100)
    parser.add_argument('--format', choices=['wav','flac'], default='flac')
    parser.add_argument('--track', type=int, choices=range(1,13), help='Generate only one track')
    options = parser.parse_args(argv)
    if options.format == 'flac' and not shutil.which('ffmpeg'):
        parser.error('FLAC requires ffmpeg; install it or choose --format wav')
    options.output.mkdir(parents=True, exist_ok=True)
    tracks=[]
    for index in ([options.track-1] if options.track else range(12)):
        track = write_track(options.output, index, options.seconds, options.sample_rate, options.format)
        tracks.append(track)
        print(f'{track["title"]}: {track["duration_seconds"]:.1f}s, {track["bytes"]} bytes', flush=True)
    manifest = {'schema_version': 1, 'album': 'Your Universe', 'artist': 'NovaOS',
                'license': 'CC0-1.0', 'generator_version': 1,
                'description': 'Original mathematical synthesis; no samples, SoundFonts or existing melodies.',
                'tracks': tracks}
    target=options.output/'manifest.json'
    temp=target.with_suffix('.json.tmp')
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temp.replace(target)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
