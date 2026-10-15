from fractions import Fraction
import subprocess
import tempfile
import unittest
from pathlib import Path

import videobuilder as vb
from videobuilder.shot3d import build


def _rotated_clip(path, size, degrees, fps=10, duration=1):
    """A CFR testsrc2 clip carrying phone-style rotation metadata: a display
    matrix in its own tkhd, the same thing an iPhone writes for a portrait
    recording. ffmpeg's `-display_rotation` only takes effect as an input
    override (it errors as an output option), so this builds a plain coded
    clip, then remuxes it with that override in effect and `-c copy`, which
    carries the side data forward into the new file's own container."""
    w, h = size
    plain = path.with_name('.plain-' + path.name)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi',
                    '-i', f'testsrc2=size={w}x{h}:rate={fps}:duration={duration}',
                    '-pix_fmt', 'yuv420p', str(plain)], check=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-display_rotation:v:0', str(degrees),
                    '-i', str(plain), '-c', 'copy', str(path)], check=True)
    plain.unlink()


def _vfr_clip(path, segments):
    """Concatenate CFR segments recorded at different rates into one
    variable-rate file -- a phone-style recording where the interval between
    frames isn't constant -- without any downloaded media. `segments` is a
    sequence of (fps, count); frame `start + i` of the result (`start` being
    the running total of frames from earlier segments) carries color
    ((start + i) * 10 % 256, 0, 0)."""
    size = (16, 16)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        parts = []
        start = 0
        for fps, n in segments:
            def source(start=start, n=n):
                for i in range(n):
                    yield i, bytes(((start + i) * 10 % 256, 0, 0, 255)) * (size[0] * size[1])
            seg_path = tmp / f'seg{start}.mp4'
            build(seg_path, source, size, fps, n)
            parts.append(seg_path)
            start += n
        listing = tmp / 'concat.txt'
        listing.write_text(''.join(f"file '{p}'\n" for p in parts))
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0',
                        '-i', str(listing), '-c', 'copy', str(path)], check=True)


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
                for i in range(60):
                    yield i, bytes((i % 256, 0, 0, 255)) * (size[0] * size[1])

            build(path, source, size, 30, 60)
            clip = vb.Clip(path)
            grid = vb.Grid(fps=30, bpm=120)
            tl = vb.Timeline(grid, [vb.Segment('a', 0, 2), vb.Segment('b', 2, 4)], end=4)
            at, z = tl.span('b')
            ft = vb.footage(tl, 'b', start=0.5)  # source second 0.5 = frame 15
            # Sweep every frame of the segment: a single floating-point rounding
            # error in the arithmetic would otherwise only show up on some frames.
            for f in range(at, z):
                expected_source_frame = 15 + (f - at)
                self.assertEqual(clip.frame_at(ft.seconds_at(f)), expected_source_frame)
            clip.close()


class Rotation(unittest.TestCase):
    """Decision 1: Clip reports and decodes the displayed size, after rotation."""

    def _corner(self, img, x, y):
        return img._pil.convert('RGB').getpixel((x, y))

    def _is_red(self, rgb):
        r, g, b = rgb
        return r > 200 and g < 50 and b < 50

    def test_size_and_decoded_frame_are_rotated(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'phone.mp4')
            _rotated_clip(path, size=(64, 48), degrees=90)
            clip = vb.Clip(path)
            self.assertEqual(clip.size, (48, 64))  # swapped from the coded 64x48
            frame = clip.frame(0)
            self.assertEqual((frame.w, frame.h), (48, 64))
            # testsrc2's bottom-left corner is a solid red swatch; ffmpeg's own
            # autorotate (which Clip relies on, applying before any other -vf)
            # carries a +90 degree rotation to the bottom-right of the display.
            self.assertTrue(self._is_red(self._corner(frame, frame.w - 3, frame.h - 3)))
            self.assertFalse(self._is_red(self._corner(frame, 2, 2)))
            clip.close()

    def test_probe_reports_the_same_displayed_size(self):
        from videobuilder.sources import probe
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'phone.mp4')
            _rotated_clip(path, size=(64, 48), degrees=90)
            _, width, height, _ = probe(path)
            self.assertEqual((width, height), (48, 64))

    def test_unrotated_clip_is_unaffected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'flat.mp4')
            _rotated_clip(path, size=(64, 48), degrees=0)
            clip = vb.Clip(path)
            self.assertEqual(clip.size, (64, 48))
            clip.close()


class ConstantFrameRateRegression(unittest.TestCase):
    """Decision 2: Clip's decode now always runs through ffmpeg's `fps` filter
    (so a variable-rate source can present as constant-rate); a constant-rate
    source's own decoded frames must come out exactly as before."""

    def test_decoded_pixel_values_are_pinned(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'shot.mp4')
            size = (16, 16)

            def source():
                for i in range(20):
                    yield i, bytes((i * 11, 20, 100, 255)) * (size[0] * size[1])

            build(path, source, size, 30, 20)
            clip = vb.Clip(path)
            for i, expected_r in ((0, 0), (5, 55), (10, 110), (19, 209)):
                r, g, b = clip.frame(i)._pil.convert('RGB').getpixel((0, 0))
                self.assertAlmostEqual(r, expected_r, delta=3)
                self.assertAlmostEqual(g, 20, delta=3)
                self.assertAlmostEqual(b, 100, delta=3)
            clip.close()


class VariableFrameRate(unittest.TestCase):
    """Decision 2: frame `i` is the source frame displayed at `i / clip.fps`
    seconds on the source's own clock, even when the source itself isn't
    evenly spaced."""

    def test_frame_at_tracks_the_source_within_one_frame(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, 'vfr.mp4')
            _vfr_clip(path, [(10, 10), (20, 10)])  # 1.0s at 10fps, then 0.5s at 20fps
            clip = vb.Clip(path)
            self.assertEqual(clip.fps, Fraction(40, 3))  # 20 frames / 1.5s, exact

            def true_index_at(t):  # t: Fraction seconds, matching _vfr_clip's own construction
                if t < 1:
                    return min(9, int(t * 10))
                return 10 + min(9, int((t - 1) * 20))

            for i in (0, 2, 3, 6, 9, 12, 14, 16, 18, 19):
                t = Fraction(i) / clip.fps
                n = clip.frame_at(float(t))
                shown = round(clip.frame(n)._pil.convert('RGB').getpixel((0, 0))[0] / 10)
                self.assertLessEqual(abs(shown - true_index_at(t)), 1)
            clip.close()


if __name__ == '__main__':
    unittest.main()
