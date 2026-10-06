import os
import shutil
import subprocess
import tempfile
import unittest

from videobuilder import Film
from videobuilder.render import check_chunk, render


class ChunkDriftGuard(unittest.TestCase):
    def test_whole_microsecond_chunks_pass(self):
        for chunk, fps in ((15, 30), (30, 30), (3, 30), (24, 24), (15, 24), (60, 60), (1, 25), (5, 50)):
            with self.subTest(chunk=chunk, fps=fps):
                check_chunk(chunk, fps)

    def test_drifting_chunks_rejected(self):
        # 20 frames at 30 fps is 666666.67 us: the concat joins would drift.
        for chunk, fps in ((20, 30), (1, 30), (7, 30), (10, 60), (1, 24)):
            with self.subTest(chunk=chunk, fps=fps):
                with self.assertRaises(ValueError):
                    check_chunk(chunk, fps)

    def test_empty_chunk_rejected(self):
        with self.assertRaises(ValueError):
            check_chunk(0, 30)

    def test_render_checks_before_drawing(self):
        drawn = []
        film = Film(draw=lambda n, cv: drawn.append(n), fps=30, frames=60)
        with self.assertRaises(ValueError):
            render(film, os.devnull, chunk=20)
        self.assertEqual(drawn, [])


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg')
class RenderJoins(unittest.TestCase):
    def test_chunks_join_to_exact_length(self):
        def draw(n, cv):
            cv.rect(n, 0, 8, 8, '#ffffff')
        film = Film(draw=draw, fps=30, frames=50, formats=['1x1'])
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'x.mp4')
            with open(os.devnull, 'w') as quiet:
                render(film, out, jobs=2, chunk=15, log=quiet)  # 15 + 15 + 15 + 5
            probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-count_frames',
                                    '-show_entries', 'stream=nb_read_frames,width,height,duration',
                                    '-of', 'default=nw=1', out], capture_output=True, text=True, check=True).stdout
        facts = dict(line.split('=') for line in probe.split())
        self.assertEqual(int(facts['nb_read_frames']), 50)
        self.assertEqual((int(facts['width']), int(facts['height'])), (1080, 1080))
        self.assertAlmostEqual(float(facts['duration']), 50 / 30, places=3)


if __name__ == '__main__':
    unittest.main()
