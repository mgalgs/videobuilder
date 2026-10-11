"""Declared mark contracts on a small deterministic film."""
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import videobuilder as vb
from videobuilder import expect
from videobuilder.edits import Edits, active
from videobuilder.cli import main


class Report:
    def __init__(self):
        self.passes = []
        self.fails = []

    def ok(self, msg): self.passes.append(msg)
    def fail(self, msg): self.fails.append(msg)


class Expectations(unittest.TestCase):
    def setUp(self):
        grid = vb.Grid(fps=10, bpm=600)
        self.timeline = vb.Timeline(grid, [vb.Segment('intro', 0, 5), vb.Segment('outro', 5, 10)], end=10)
        def draw(n, cv):
            cv.mark('hero', min(n, 5), 10, 10, 10)
            cv.mark('pad', 5, 22, 10, 4)
            cv.mark('copy', 30, 30, 10, 10)
            if n >= 5: cv.mark('logo', 40, 2, 8, 8)
        self.film = vb.Film(draw=draw, timeline=self.timeline, formats=(vb.Format('tiny', 60, 50),))
        self.fmt = self.film.formats[0]

    def check_one(self, e):
        r = Report()
        expect.check([e], self.film, self.fmt, r)
        return r

    def test_each_constructor_passes_and_fails(self):
        cases = [
            (vb.visible('logo', vb.seg('outro')), vb.visible('logo', vb.seg('intro'))),
            (vb.hidden('logo', vb.seg('intro')), vb.hidden('logo', vb.seg('outro'))),
            (vb.touches('hero', 'pad', 5), vb.touches('hero', 'pad', 5, tolerance=1)),
            (vb.apart('hero', 'copy', 0, 10), vb.apart('hero', 'copy', 0, 30)),
            (vb.still('copy', (1, 4)), vb.still('hero', (1, 4))),
            (vb.at_rest_by('hero', 6), vb.at_rest_by('hero', 4)),
        ]
        for good, bad in cases:
            with self.subTest(kind=good.kind):
                self.assertEqual(len(self.check_one(good).passes), 1)
                self.assertTrue(self.check_one(bad).fails)

    def test_format_safe_area_and_note(self):
        e = vb.visible('logo', 5, formats=('tiny',), note='Keep the logo clear')
        r = Report()
        expect.check([e], self.film, self.fmt, r, {'tiny': {'safe': (0, 0, 20, 20)}})
        self.assertIn('Keep the logo clear', r.fails[0])
        self.assertIn('f5', r.fails[0])
        self.assertIn('box', r.fails[0])

    def test_missing_name_fails_even_for_hidden(self):
        r = self.check_one(vb.hidden('typo', 0))
        self.assertTrue(any('never appears' in msg for msg in r.fails))

    def test_anchors_follow_roll_edit(self):
        self.assertEqual(expect.resolve(vb.seg('outro'), self.timeline), 5)
        self.assertEqual(expect.resolve(vb.seg('intro', 'end', -1), self.timeline), 3)
        self.assertEqual(expect.resolve(vb.seg('intro', 'mid'), self.timeline), 2)
        edits = Edits('test.edits.toml', {'intro': {'until': 7}})
        with active(edits):
            changed = vb.Timeline(vb.Grid(fps=10, bpm=600),
                                  [vb.Segment('intro', 0, 5), vb.Segment('outro', 5, 10)], end=10)
        self.assertEqual(expect.resolve(vb.seg('outro'), changed), 7)
        self.assertEqual(expect.resolve(vb.seg('intro', 'end', -1), changed), 5)
        self.assertEqual(expect.resolve(vb.seg('intro', 'mid'), changed), 3)

    def test_check_script_reports_director_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            film = Path(tmp) / 'film.py'
            film.write_text("import videobuilder as vb\n"
                            "def draw(n, cv): cv.mark('logo', 0, 0, 4, 4)\n"
                            "FILM = vb.Film(draw=draw, frames=2, fps=10, formats=(vb.Format('tiny', 60, 50),))\n"
                            "EXPECT = [vb.hidden('logo', 0, note='Remove the logo here')]\n")
            script = Path(__file__).resolve().parent.parent / 'skill/make-a-video/scripts/check.py'
            result = subprocess.run([sys.executable, str(script), str(film)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("FAIL", result.stdout)
            self.assertIn('Remove the logo here', result.stdout)
            self.assertIn('f0', result.stdout)

    def test_motion_command_png_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            film = Path(tmp) / 'film.py'
            film.write_text("import videobuilder as vb\n"
                            "def draw(n, cv): cv.mark('dot', n, 0, 4, 4)\n"
                            "FILM = vb.Film(draw=draw, frames=4, fps=10, formats=(vb.Format('tiny', 60, 50),))\n")
            out = Path(tmp) / 'motion.png'
            with contextlib.redirect_stdout(io.StringIO()):
                main(['motion', str(film), '--onion', '2', '-o', str(out)])
            with Image.open(out) as image:
                self.assertEqual(image.size, (1100, 978))


if __name__ == '__main__':
    unittest.main()
