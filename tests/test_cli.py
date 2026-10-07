import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FILM = str(ROOT / 'examples' / 'tour.py')


def run(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    return subprocess.run([sys.executable, '-m', 'videobuilder', *args], cwd=cwd, env=env,
                          capture_output=True, text=True, check=True)


class Cli(unittest.TestCase):
    def test_still_formats_and_names(self):
        with tempfile.TemporaryDirectory() as d:
            run('still', FILM, '30', '--format', 'all', '--scale', '0.25', '--out', 'stills', cwd=d)
            sizes = {p.name: Image.open(p).size for p in Path(d, 'stills').iterdir()}
        self.assertEqual(sizes, {'tour-16x9-f00030.png': (480, 270), 'tour-9x16-f00030.png': (270, 480),
                                 'tour-1x1-f00030.png': (270, 270)})

    def test_single_still_to_path(self):
        with tempfile.TemporaryDirectory() as d:
            run('still', FILM, '100', '--format', '9x16', '--overlay', '--out', 'x.png', cwd=d)
            self.assertEqual(Image.open(Path(d, 'x.png')).size, (1080, 1920))

    def test_sheet_defaults_to_segment_frames(self):
        with tempfile.TemporaryDirectory() as d:
            out = run('sheet', FILM, '--format', '1x1', '--width', '100', '--cols', '4', cwd=d).stdout.strip()
            self.assertEqual(out, 'tour-1x1-sheet.png')
            w, h = Image.open(Path(d, out)).size
        self.assertEqual(w, 4 * 108 + 8)  # 4 segments x (in, middle, out) = 12 thumbs, 3 rows
        self.assertEqual(h, 3 * (100 + 22 + 8) + 8)

    def test_bad_format(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(subprocess.CalledProcessError) as e:
                run('still', FILM, '0', '--format', '4x3', cwd=d)
        self.assertIn('no 4x3 format', e.exception.stderr)


class Edit(unittest.TestCase):
    """`edit roll` and `edit copy` write the film's edits.toml, or refuse and leave it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        Path(self.dir, 'film.py').write_text(
            "import videobuilder as vb\n"
            "T = vb.Timeline(vb.Grid(), [vb.Segment('intro', 0, 4, dict(title='Hi')), vb.Segment('body', 4, 8)], end=8)\n"
            "FILM = vb.Film(draw=lambda n, cv: None, timeline=T)\n")
        self.toml = self.dir / 'edits.toml'

    def tearDown(self):
        self.tmp.cleanup()

    def text(self):
        return self.toml.read_text()

    def test_edit_roll_and_copy(self):
        env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}

        def vb(*args):
            return subprocess.run([sys.executable, '-m', 'videobuilder', 'edit', *args], cwd=self.dir, env=env,
                                  capture_output=True, text=True)
        r = vb('roll', 'film.py', 'intro', '6.5')
        self.assertEqual((r.returncode, r.stdout.strip()), (0, str(self.toml)))
        r = vb('copy', 'film.py', 'intro', 'title', 'Line "one"\\two')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.text(), '[segments.intro]\nuntil = 6.5\n\n[segments.intro.data]\n'
                                      'title = "Line \\"one\\"\\\\two"\n')
        before = self.text()
        r = vb('roll', 'film.py', 'intro', '6.25')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('not edited', r.stderr)
        self.assertIn('half-beat grid', r.stderr)
        self.assertEqual(self.text(), before)
        self.assertEqual(vb('roll', 'film.py', 'intro', '4').returncode, 0)  # the film's own end: no edit
        self.assertEqual(self.text(), '[segments.intro.data]\ntitle = "Line \\"one\\"\\\\two"\n')


class RunnableFilm(unittest.TestCase):
    """A film that ends with videobuilder.main(__file__) runs the CLI on itself."""

    SOURCE = (
        "import videobuilder as vb\n"
        "LAYOUT = {'1x1': 'mine'}\n"
        "FILM = vb.Film(draw=lambda n, cv: cv.rect(0, 0, 10, 10, '#f00'), fps=30, frames=3, formats='1x1')\n"
        "if __name__ == '__main__':\n"
        "    vb.main(__file__)\n")

    def test_film_runs_itself(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, 'self_run.py')
            path.write_text(self.SOURCE)
            env = {**os.environ, 'PYTHONPATH': str(ROOT)}
            other = Path(d, 'elsewhere')
            other.mkdir()
            subprocess.run([sys.executable, str(path), 'still', '1', '--scale', '0.1', '--out', 'one.png'],
                           cwd=other, env=env, capture_output=True, text=True, check=True)
            self.assertEqual(Image.open(other / 'one.png').size, (108, 108))
            usage = subprocess.run([sys.executable, str(path)], cwd=d, env=env, capture_output=True, text=True)
            self.assertIn('render', usage.stdout)

    def test_load_module_reaches_the_films_own_data(self):
        from videobuilder import load_module
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, 'data_film.py')
            path.write_text(self.SOURCE)
            mod = load_module(str(path))
            self.assertEqual((mod.LAYOUT, mod.FILM.frames), ({'1x1': 'mine'}, 3))


if __name__ == '__main__':
    unittest.main()
