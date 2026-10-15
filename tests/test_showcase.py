"""examples/showcase.py: every catalog capability has its own shot, in catalog
order, tagged with its card's title, and every shot draws in both formats;
`capabilities build` renders it and the /capabilities page shows it."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_every_segment_is_drawn(self):
        for seg in self.timeline.leaves():
            with self.subTest(segment=seg.name):
                self.assertIn(seg.name, self.mod.SCENES)

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


class ServedWithTheCatalog(unittest.TestCase):
    def test_the_full_build_renders_the_reel_in_both_formats_with_posters(self):
        rendered = []

        def fake_render(film, out, fmt, **kw):
            rendered.append((os.path.basename(out), fmt.width, fmt.height))
            Path(out).write_bytes(b'mp4')

        with tempfile.TemporaryDirectory() as d, mock.patch('videobuilder.render.render', fake_render):
            results = capabilities.build_showcase(d)
            self.assertEqual(rendered, [('showcase-16x9.mp4', 1280, 720), ('showcase-9x16.mp4', 720, 1280)])
            self.assertEqual([r['id'] for r in results], list(capabilities.SHOWCASE_FILES))
            for name in capabilities.SHOWCASE_FILES:
                self.assertTrue((Path(d) / f'{name}.jpg').stat().st_size > 0)

    def test_build_adds_the_reel_unless_only_some_ids_are_asked_for(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch('videobuilder.render.render'), \
                mock.patch.object(capabilities, 'build_showcase', return_value=[{'id': 'showcase-16x9'}]) as reel, \
                mock.patch.object(capabilities, 'CATALOG', ()):
            capabilities.build(d)
            self.assertEqual(reel.call_count, 1)
            capabilities.build(d, only={'showcase'})
            self.assertEqual(reel.call_count, 2)
            capabilities.build(d, only=set())
            self.assertEqual(reel.call_count, 2)

    def test_clip_file_serves_the_showcase_files_and_nothing_else_new(self):
        d = '/srv/caps'
        self.assertEqual(capabilities.clip_file(d, 'showcase-16x9', 'mp4'), '/srv/caps/showcase-16x9.mp4')
        self.assertEqual(capabilities.clip_file(d, 'showcase-9x16', 'jpg'), '/srv/caps/showcase-9x16.jpg')
        for bad in ('showcase', 'showcase-1x1', 'showcase-16x9-x'):
            self.assertIsNone(capabilities.clip_file(d, bad, 'mp4'))
        self.assertIsNone(capabilities.clip_file(None, 'showcase-16x9', 'mp4'))

    def test_the_page_shows_the_reel_muted_above_the_cards_only_when_built(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertNotIn(b'id="reel"', capabilities.page_html(d, '0'))
            Path(d, 'showcase-16x9.mp4').write_bytes(b'mp4')
            page = capabilities.page_html(d, '0').decode()
        video = page[page.index('<video id="reel"'):]
        video = video[:video.index('>')]
        self.assertIn('src="/capabilities/showcase-16x9.mp4"', video)
        self.assertIn(' muted', video)
        self.assertNotIn('autoplay', video)   # started muted from script, and not at all for reduced motion
        self.assertIn('id="reel-unmute"', page)
        self.assertLess(page.index('id="reel"'), page.index('data-card='))


if __name__ == '__main__':
    unittest.main()
