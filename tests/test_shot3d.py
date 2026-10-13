import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import videobuilder as vb
from videobuilder.shot3d import build


class ClipTests(unittest.TestCase):
    def test_build_and_seek(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'shot.mp4')
            size = (16, 16)

            def source():
                for i in range(12):
                    yield i, bytes((i * 19, 20, 100, 255)) * (size[0] * size[1])

            build(path, source, size, 30, 12)
            clip = vb.Clip(path)
            self.assertEqual((clip.frames, clip.fps, clip.size), (12, 30, size))
            sequential = [clip.frame(i)._pil.tobytes() for i in range(12)]
            for i in (10, 0, 11, 3, 6):
                self.assertEqual(clip.frame(i)._pil.tobytes(), sequential[i])
            for i in (-1, 12):
                with self.assertRaises(IndexError):
                    clip.frame(i)
            clip.close()

    def test_incomplete_build_does_not_publish(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'shot.mp4')
            with self.assertRaisesRegex(ValueError, 'expected 2 frames'):
                build(path, lambda: iter([(0, bytes(16))]), (2, 2), 30, 2)
            self.assertFalse(path.exists())


class AdapterTests(unittest.TestCase):
    def test_early_close_stops_render_thread(self):
        from videobuilder.manimgx_shot import frames
        class Cut(Exception):
            pass
        class Frame:
            repeat = 1
            def __init__(self, index):
                self.index = index
            def pixels(self):
                return bytes(4)
        class Scene:
            def render(self, frames):
                for i in range(1000):
                    frames(Frame(i))
        fake = types.ModuleType('manimgx')
        fake.config = types.SimpleNamespace()
        film = types.ModuleType('manimgx.rendering.film')
        film.Cut = Cut
        rendering = types.ModuleType('manimgx.rendering')
        with patch.dict(sys.modules, {'manimgx': fake, 'manimgx.rendering': rendering,
                                      'manimgx.rendering.film': film}):
            before = set(threading.enumerate())
            stream = frames(Scene, (1, 1), 1000, 30)
            self.assertEqual(next(stream)[0], 0)
            stream.close()
            self.assertEqual(set(threading.enumerate()), before)
