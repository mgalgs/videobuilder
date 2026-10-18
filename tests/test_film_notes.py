"""`python -m videobuilder assemble --check`: the timeline file validated without rendering."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_films import three_clips, write_film


class AssembleCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        write_film(self.root, three_clips())

    def check(self):
        env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parent.parent)}
        return subprocess.run([sys.executable, '-m', 'videobuilder', 'assemble', str(self.root), '--check'],
                              capture_output=True, text=True, env=env)

    def test_check_validates_without_rendering(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('timeline.json: ok, 3 clips', result.stdout)
        self.assertIn('not on disk here (fine if it is an upload): sources/boat.mp4', result.stderr)
        self.assertFalse((self.root / '.vb-cache').exists())

        (self.root / 'clips' / 'c' / 'film.py').unlink()
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('clip "c": no film file clips/c/film.py', result.stderr)

        (self.root / 'timeline.json').write_text(json.dumps({**three_clips(), 'trim': 1}))
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('trim', result.stderr)


if __name__ == '__main__':
    unittest.main()
