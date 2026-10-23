import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'applications'))
from novaos.desktop_widgets import rate, read_playback


class DesktopWidgetsTests(unittest.TestCase):
    def test_bandwidth_counter_reset_and_first_observation(self):
        self.assertEqual(rate(100, None, 2), 0)
        self.assertEqual(rate(100, 200, 2), 0)
        self.assertEqual(rate(300, 100, 2), 100)
        self.assertEqual(rate(300, 100, 0), 0)

    def test_live_player_identity_and_stale_pid_are_distinguished(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'playback.json'
            data = {'pid': os.getpid(), 'created': psutil.Process().create_time(),
                    'playing': True, 'title': 'Local track'}
            path.write_text(json.dumps(data))
            self.assertEqual(read_playback(path)['title'], 'Local track')
            data['created'] -= 10
            path.write_text(json.dumps(data))
            self.assertEqual(read_playback(path), {})

    def test_invalid_or_missing_status_is_a_closed_player(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'playback.json'
            self.assertEqual(read_playback(path), {})
            for body in ['invalid', '[]', '{}']:
                path.write_text(body)
                self.assertEqual(read_playback(path), {})


if __name__ == '__main__':
    unittest.main()
