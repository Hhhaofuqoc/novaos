"""Portable tests for playlist semantics, state persistence, and real album assets."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'applications'))
from novaos.music import Playlist, PlayerState, Track, load_album, restore_library
spec=importlib.util.spec_from_file_location('nova_music_generator',ROOT/'music'/'generate.py')
generator=importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class PlaylistTests(unittest.TestCase):
    def setUp(self):
        self.tracks=[Track(Path(f'/tmp/nova-{i}.wav'),f'Track {i}') for i in range(3)]
        self.playlist=Playlist(self.tracks,rng=random.Random(42))

    def test_empty_playlist_is_safe(self):
        playlist=Playlist()
        self.assertIsNone(playlist.current)
        self.assertIsNone(playlist.next())
        self.assertIsNone(playlist.previous())

    def test_sequential_eos_stops_without_repeat(self):
        self.assertEqual(self.playlist.next(ended=True),self.tracks[1])
        self.assertEqual(self.playlist.next(ended=True),self.tracks[2])
        self.assertIsNone(self.playlist.next(ended=True))

    def test_manual_next_wraps_but_repeat_one_only_repeats_eos(self):
        self.playlist.repeat='one'
        self.assertEqual(self.playlist.next(ended=True),self.tracks[0])
        self.assertEqual(self.playlist.next(),self.tracks[1])
        self.playlist.select(2)
        self.assertEqual(self.playlist.next(),self.tracks[0])

    def test_album_repeat(self):
        self.playlist.repeat='all'
        self.playlist.select(2)
        self.assertEqual(self.playlist.next(ended=True),self.tracks[0])

    def test_shuffle_visits_each_once_and_previous_uses_actual_history(self):
        self.playlist.shuffle=True
        visited=[self.playlist.current]
        visited.append(self.playlist.next(ended=True))
        visited.append(self.playlist.next(ended=True))
        self.assertEqual(len({track.title for track in visited}),3)
        self.assertIsNone(self.playlist.next(ended=True))
        self.assertEqual(self.playlist.previous(),visited[1])

    def test_shuffle_repeat_album_restarts(self):
        self.playlist.shuffle=True
        self.playlist.repeat='all'
        for _ in range(10):
            previous=self.playlist.current
            self.assertNotEqual(self.playlist.next(ended=True),previous)

    def test_duplicates_and_invalid_selection(self):
        self.assertFalse(self.playlist.add(self.tracks[0]))
        with self.assertRaises(IndexError):
            self.playlist.select(5)
        with self.assertRaises(IndexError):
            self.playlist.select(-1)


class PersistenceTests(unittest.TestCase):
    def test_atomic_state_round_trip_and_file_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'config'/'music.json'
            audio=Path(directory)/'local song.wav'
            audio.write_bytes(b'fixture; decoder not used in this state test')
            playlist=Playlist([Track.local(audio)])
            playlist.repeat='all'
            playlist.shuffle=True
            store=PlayerState(path)
            store.save(playlist,.37,True,True)
            loaded=store.load()
            self.assertEqual(loaded['volume'],.37)
            self.assertTrue(loaded['ambient'])
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            restored=restore_library(loaded,[])
            self.assertEqual(restored.current.path,audio)
            self.assertEqual(restored.repeat,'all')
            self.assertTrue(restored.shuffle)
            self.assertFalse(list(path.parent.glob('.music-*')))

    def test_corrupt_or_deleted_library_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'music.json'
            path.write_text('{broken')
            self.assertEqual(PlayerState(path).load(),{})
            playlist=restore_library({'library':[{'path':'/does/not/exist.wav'},42],
                                      'index':'bad','repeat':'bad'},[])
            self.assertIsNone(playlist.current)
            self.assertEqual(playlist.repeat,'none')

    def test_untrusted_album_manifest_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            album=root/'album'
            album.mkdir()
            (root/'private.wav').write_bytes(b'example')
            (album/'manifest.json').write_text(json.dumps({'tracks':[{
                'path':'../private.wav','title':'Escape'}]}))
            self.assertEqual(load_album(album),[])
            (album/'manifest.json').write_text('[]')
            self.assertEqual(load_album(album),[])


@unittest.skipUnless(importlib.util.find_spec('numpy'),'NumPy required for synthesis tests')
class SynthesisTests(unittest.TestCase):
    def test_original_synth_is_deterministic_non_silent_bounded_and_fades(self):
        import numpy as np
        audio=generator.synthesize(0,3,8000)
        self.assertEqual(audio.shape,(24000,2))
        self.assertTrue(np.array_equal(audio,generator.synthesize(0,3,8000)))
        self.assertFalse(np.array_equal(audio,generator.synthesize(1,3,8000)))
        self.assertLessEqual(float(np.max(np.abs(audio))),.720001)
        self.assertGreater(float(np.sqrt(np.mean(audio**2))),.01)
        self.assertTrue(np.all(audio[0]==0))
        self.assertTrue(np.all(audio[-1]==0))
        self.assertFalse(np.array_equal(audio[:,0],audio[:,1]))

    def test_actual_wav_generation_metadata_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            track=generator.write_track(Path(directory),2,2,8000,'wav')
            path=Path(directory)/track['path']
            with wave.open(str(path)) as audio:
                self.assertEqual(audio.getnchannels(),2)
                self.assertEqual(audio.getframerate(),8000)
                self.assertEqual(audio.getnframes(),16000)
                self.assertEqual(audio.getsampwidth(),2)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),track['sha256'])
            self.assertEqual(track['title'],'Quiet Terminal')

    def test_synthesis_rejects_unbounded_allocations(self):
        for index,seconds,rate in [(12,72,44100),(0,10000,44100),(0,72,1)]:
            with self.assertRaises(ValueError):
                generator.synthesize(index,seconds,rate)


class AlbumTests(unittest.TestCase):
    def test_every_manifest_asset_exists_and_matches_hash(self):
        directory=ROOT/'music'/'generated'
        if not (directory/'manifest.json').is_file():
            self.skipTest('Run python3 music/generate.py first to validate rendered album')
        manifest=json.loads((directory/'manifest.json').read_text())
        self.assertEqual(len(manifest['tracks']),12)
        self.assertEqual([t['title'] for t in manifest['tracks']],generator.TITLES)
        for track in manifest['tracks']:
            path=directory/track['path']
            self.assertTrue(path.is_file(),str(path))
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),track['sha256'])
            self.assertEqual(path.stat().st_size,track['bytes'])
            self.assertGreater(track['rms'],.01)
            self.assertLessEqual(track['peak'],.720001)
        self.assertEqual(len(load_album(directory)),12)


if __name__ == '__main__':
    unittest.main()
