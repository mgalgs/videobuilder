"""examples/showcase.py: every catalog capability has its own shot, in catalog
order, tagged with its card's title, and every shot draws in both formats."""
import unittest
from pathlib import Path

from videobuilder import capabilities, load_module

ROOT = Path(__file__).resolve().parent.parent
SHOWCASE = ROOT / 'examples' / 'showcase.py'


class Showcase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module(str(SHOWCASE))
        cls.film = cls.mod.FILM
        cls.timeline = cls.mod.TIMELINE

    def test_every_capability_has_a_shot(self):
        segments = {s.name for s, _ in self.timeline.walk()}
        for e in capabilities.CATALOG:
            with self.subTest(id=e['id']):
                self.assertIn(e['id'], self.mod.SHOTS, f"{e['id']} has no shot in examples/showcase.py")
                self.assertIn(self.mod.SHOTS[e['id']], segments)

    def test_shots_run_in_catalog_order(self):
        starts = [self.timeline.start(self.mod.SHOTS[i]) for i in capabilities.ids()]
        self.assertEqual(starts, sorted(starts))
        self.assertEqual(len(set(starts)), len(starts), 'two capabilities share a shot')

    def test_each_shot_is_tagged_with_its_catalog_title(self):
        for e in capabilities.CATALOG:
            with self.subTest(id=e['id']):
                self.assertEqual(self.mod.TAGS[self.mod.SHOTS[e['id']]], e['title'])

    def test_two_formats_at_the_catalog_build_size(self):
        self.assertEqual([(f.name, f.width, f.height) for f in self.film.formats],
                         [('16x9', 1280, 720), ('9x16', 720, 1280)])

    def test_every_shot_draws_in_both_formats(self):
        for seg in self.timeline.leaves():
            a, z = self.timeline.span(seg)
            for fmt in self.film.formats:
                for n in (a, (a + z) // 2, z - 1):
                    with self.subTest(segment=seg.name, format=fmt.name, frame=n):
                        cv = self.film.frame(n, fmt, scale=0.1)
                        self.assertTrue(cv.marks, 'nothing marked on screen')

    def test_the_loop_rests_where_it_starts(self):
        """The end card's last frame is one step of the logo's turn before frame 0."""
        for fmt in self.film.formats:
            first = self.film.frame(0, fmt, scale=0.25)
            last = self.film.frame(self.film.frames - 1, fmt, scale=0.25)
            self.assertEqual([n for n, _ in first.marks], [n for n, _ in last.marks])
            self.assertEqual([tuple(b) for _, b in first.marks], [tuple(b) for _, b in last.marks])


if __name__ == '__main__':
    unittest.main()
