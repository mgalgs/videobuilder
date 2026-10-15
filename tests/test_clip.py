import tempfile
import unittest
from pathlib import Path

import videobuilder as vb
from videobuilder.shot3d import build


class FrameAt(unittest.TestCase):
    def test_floors_to_the_covering_frame(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'shot.mp4')
            size = (16, 16)

            def source():
                for i in range(20):
                    yield i, bytes((i * 11, 20, 100, 255)) * (size[0] * size[1])

            build(path, source, size, 30, 20)
            clip = vb.Clip(path)
            self.assertEqual(clip.frame_at(0), 0)
            self.assertEqual(clip.frame_at(0.1), 3)
            self.assertEqual(clip.frame_at(10 / 30), 10)
            self.assertEqual(clip.frame_at(10.9 / 30), 10)  # still frame 10, not yet 11
            clip.close()


class Footage(unittest.TestCase):
    """Decision 4: a timeline segment and a source in-point, tied together."""

    def test_picture_and_sound_stay_in_sync(self):
        grid = vb.Grid(fps=30, bpm=120)
        tl = vb.Timeline(grid, [vb.Segment('a', 0, 2), vb.Segment('b', 2, 6)], end=6)
        at, z = tl.span('b')
        ft = vb.footage(tl, 'b', start=1.5)
        self.assertEqual((ft.at, ft.frames, ft.start, ft.fps), (at, z - at, 1.5, 30))

        for f in (at, at + 7, z - 1):
            self.assertAlmostEqual(ft.seconds_at(f), 1.5 + (f - at) / 30)

        snd = ft.sound('voice.wav', gain_db=-3)
        self.assertEqual(snd.path, 'voice.wav')
        self.assertEqual(snd.at, at)
        self.assertEqual(snd.frames, z - at)
        self.assertEqual(snd.gain_db, -3)
        # The Sound starts at the same source second the segment's first frame shows.
        self.assertEqual(snd.start, ft.seconds_at(at))

    def test_draws_the_right_source_frame_for_each_film_frame(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'shot.mp4')
            size = (16, 16)

            def source():
                for i in range(30):
                    yield i, bytes((i * 8, 0, 0, 255)) * (size[0] * size[1])

            build(path, source, size, 30, 30)
            clip = vb.Clip(path)
            grid = vb.Grid(fps=30, bpm=120)
            tl = vb.Timeline(grid, [vb.Segment('a', 0, 2), vb.Segment('b', 2, 4)], end=4)
            at, z = tl.span('b')
            ft = vb.footage(tl, 'b', start=0.5)  # source second 0.5 = frame 15
            for f, expected_source_frame in ((at, 15), (at + 5, 20), (z - 1, 15 + (z - 1 - at))):
                self.assertEqual(clip.frame_at(ft.seconds_at(f)), expected_source_frame)
            clip.close()


if __name__ == '__main__':
    unittest.main()
