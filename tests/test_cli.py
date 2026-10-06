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


if __name__ == '__main__':
    unittest.main()
