import tempfile
import unittest
from pathlib import Path

from videobuilder.shot3d import ShotCache


class ShotCacheTests(unittest.TestCase):
    def test_cache_is_complete_ordered_and_reusable(self):
        with tempfile.TemporaryDirectory() as root:
            shot = ShotCache(root, b'scene A', (2, 2), 30, 3)
            calls = []

            def frames():
                calls.append(1)
                for n in range(3):
                    yield n, bytes([n * 60, 10, 20, 255]) * 4

            self.assertTrue(shot.build(frames))
            self.assertEqual(shot.image(2)._pil.getpixel((0, 0)), (120, 10, 20, 255))
            self.assertFalse(shot.build(frames))
            self.assertEqual(len(calls), 1)
            self.assertNotEqual(shot.path, ShotCache(root, b'scene B', (2, 2), 30, 3).path)
            self.assertNotEqual(shot.path, ShotCache(root, b'scene A', (2, 2), 60, 3).path)

    def test_incomplete_stream_is_not_published(self):
        with tempfile.TemporaryDirectory() as root:
            shot = ShotCache(root, b'scene', (1, 1), 30, 2)
            with self.assertRaisesRegex(ValueError, 'expected 2 frames'):
                shot.build(lambda: iter([(0, bytes([0, 0, 0, 255]))]))
            self.assertFalse((shot.path / 'complete').exists())
