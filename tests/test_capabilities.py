"""The capabilities catalog: every entry has a demo and every demo loads,
draws, and passes the skill's own review check."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

from videobuilder import capabilities, load

ROOT = Path(__file__).resolve().parent.parent
DEMOS = ROOT / 'examples' / 'capabilities'
CHECK = ROOT / 'skill' / 'make-a-video' / 'scripts' / 'check.py'
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


class Catalog(unittest.TestCase):
    def test_every_entry_has_a_demo_and_every_demo_has_an_entry(self):
        demo_files = {p.name for p in DEMOS.glob('*.py') if not p.name.startswith('_')}
        catalog_files = {os.path.basename(e['demo']) for e in capabilities.CATALOG}
        self.assertEqual(catalog_files, demo_files)
        for e in capabilities.CATALOG:
            self.assertTrue((ROOT / e['demo']).is_file(), e['demo'])

    def test_ids_are_unique_kebab_case(self):
        seen = set()
        for e in capabilities.CATALOG:
            self.assertRegex(e['id'], r'\A[a-z][a-z0-9]*(-[a-z0-9]+)*\Z')
            self.assertNotIn(e['id'], seen)
            seen.add(e['id'])

    def test_every_demo_draws_first_middle_last_frame(self):
        for e in capabilities.CATALOG:
            with self.subTest(id=e['id']):
                film = load(str(ROOT / e['demo']))
                fmt = film.formats[0]
                self.assertGreaterEqual(film.frames, 2)
                for n in (0, film.frames // 2, film.frames - 1):
                    film.frame(n, fmt, scale=0.1)

    def test_every_demo_passes_check(self):
        for e in capabilities.CATALOG:
            with self.subTest(id=e['id']):
                result = subprocess.run([sys.executable, str(CHECK), str(ROOT / e['demo'])],
                                        capture_output=True, text=True, env=ENV)
                self.assertIn('0 failed', result.stdout, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
