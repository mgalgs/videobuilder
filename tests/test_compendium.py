"""The compendium: the component format, the seed components, the reference
recipes, the index, and `compendium build`."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videobuilder import compendium
from videobuilder.compendium.schema import KINDS, SlotError

ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / 'skill' / 'make-a-video' / 'scripts' / 'check.py'
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


class Catalog(unittest.TestCase):
    def test_at_least_six_components_covering_every_kind(self):
        self.assertGreaterEqual(len(compendium.CATALOG), 6)
        self.assertEqual(set(c.kind for c in compendium.CATALOG), set(KINDS))

    def test_ids_are_unique_kebab_case(self):
        seen = set()
        for c in compendium.CATALOG:
            self.assertRegex(c.id, r'\A[a-z][a-z0-9]*(-[a-z0-9]+)*\Z')
            self.assertNotIn(c.id, seen)
            seen.add(c.id)

    def test_component_metadata_is_complete(self):
        for c in compendium.CATALOG:
            with self.subTest(id=c.id):
                self.assertIn(c.kind, KINDS)
                self.assertTrue(c.description)
                self.assertTrue(c.tags)
                self.assertTrue(c.formats)
                self.assertLessEqual(set(c.formats), {'16x9', '9x16', '1x1'})
                lo, hi = c.beats
                self.assertGreater(lo, 0)
                self.assertGreaterEqual(hi, lo)
                self.assertTrue(c.slots)
                for s in c.slots:
                    self.assertTrue(s.hint)
                # the sample fills every slot and is itself valid (Component.__post_init__
                # already checked this at import time; re-check here so a future change that
                # skips __post_init__ validation still fails a test, not just at import).
                validated = c.validate(c.sample)
                self.assertEqual(set(validated), {s.name for s in c.slots})

    def test_two_or_more_recipes(self):
        self.assertGreaterEqual(len(compendium.RECIPES), 2)
        for r in compendium.RECIPES:
            with self.subTest(id=r.id):
                self.assertTrue(r.title)
                self.assertTrue(r.description)
                self.assertGreater(r.bpm, 0)
                self.assertTrue(r.formats)
                self.assertTrue(r.steps)
                for step in r.steps:
                    self.assertIn(step.component, compendium.ids())


class Rendering(unittest.TestCase):
    def test_every_component_renders_in_every_declared_format(self):
        for c in compendium.CATALOG:
            with self.subTest(id=c.id):
                film = compendium.component_film(c)
                self.assertEqual([f.name for f in film.formats], list(c.formats))
                self.assertGreaterEqual(film.frames, 2)
                for fmt in film.formats:
                    for n in (0, film.frames // 2, film.frames - 1):
                        with self.subTest(format=fmt.name, frame=n):
                            film.frame(n, fmt, scale=0.1)

    def test_every_component_shows_marked_content_once_landed(self):
        """Not necessarily on frame 0 (an entrance may still be springing in),
        but by its last frame every component has drawn something marked."""
        for c in compendium.CATALOG:
            with self.subTest(id=c.id):
                film = compendium.component_film(c)
                fmt = film.formats[0]
                cv = film.frame(film.frames - 1, fmt, scale=0.1)
                self.assertTrue(cv.marks, 'nothing marked on screen by the last frame')

    def test_every_recipe_renders(self):
        for r in compendium.RECIPES:
            with self.subTest(id=r.id):
                film = compendium.build_recipe_film(r)
                self.assertEqual([f.name for f in film.formats], list(r.formats))
                for fmt in film.formats:
                    for n in (0, film.frames // 2, film.frames - 1):
                        with self.subTest(format=fmt.name, frame=n):
                            film.frame(n, fmt, scale=0.1)

    def test_recipe_duration_matches_its_brief(self):
        teaser = compendium.build_recipe_film(compendium.get_recipe('product-teaser'))
        self.assertTrue(15 <= teaser.frames / teaser.fps <= 20)
        explainer = compendium.build_recipe_film(compendium.get_recipe('how-it-works'))
        self.assertTrue(20 <= explainer.frames / explainer.fps <= 30)

    def test_recipe_rejects_beats_outside_the_components_range(self):
        from videobuilder.compendium.schema import Recipe, RecipeStep
        bad = Recipe(id='bad', title='bad', description='bad', bpm=120, formats=('16x9',),
                     steps=(RecipeStep('stat-counter', 999, {'value': 1, 'label': 'x'}),))
        with self.assertRaises(ValueError):
            compendium.build_recipe_film(bad)


class SlotValidation(unittest.TestCase):
    def setUp(self):
        self.c = compendium.get('kinetic-title')  # headline: text, max_length=40; accent: color, optional

    def test_wrong_type_is_rejected(self):
        with self.assertRaises(SlotError) as cm:
            self.c.validate({'headline': 12345})
        msg = str(cm.exception)
        self.assertIn('kinetic-title', msg)
        self.assertIn('headline', msg)
        self.assertIn('text', msg)

    def test_overlong_text_is_rejected(self):
        with self.assertRaises(SlotError) as cm:
            self.c.validate({'headline': 'x' * 41})
        msg = str(cm.exception)
        self.assertIn("'headline'", msg)
        self.assertIn('41 characters', msg)
        self.assertIn('40', msg)

    def test_unknown_slot_is_rejected(self):
        with self.assertRaises(SlotError) as cm:
            self.c.validate({'headline': 'ok', 'nonexistent': 1})
        msg = str(cm.exception)
        self.assertIn('nonexistent', msg)
        self.assertIn('unknown', msg)

    def test_missing_required_slot_is_rejected(self):
        with self.assertRaises(SlotError) as cm:
            self.c.validate({})
        msg = str(cm.exception)
        self.assertIn('kinetic-title', msg)
        self.assertIn('headline', msg)
        self.assertIn('required', msg)

    def test_missing_optional_color_slot_falls_back_to_the_sample(self):
        """`color`/`palette` are a style default, so they keep falling back
        to the component's own sample (unlike every other type: see the next
        test) when a builder leaves them out."""
        out = self.c.validate({'headline': 'ok'})
        self.assertEqual(out['accent'], self.c.sample['accent'])

    def test_missing_optional_text_slot_is_empty_not_the_sample(self):
        """A builder who fills only the required slots must not get the
        sample's placeholder copy in their film (end-card's sample line3,
        say) -- an optional non-colour slot left out is empty, not borrowed
        from the sample."""
        end_card = compendium.get('end-card')
        out = end_card.validate({'headline': 'ok'})
        self.assertEqual(out['line2'], '')
        self.assertNotEqual(out['line2'], end_card.sample['line2'])

    def test_bad_color_is_rejected(self):
        with self.assertRaises(SlotError):
            self.c.validate({'headline': 'ok', 'accent': 'not-a-color'})

    def test_series_rejects_a_bad_item(self):
        bar = compendium.get('bar-chart')
        with self.assertRaises(SlotError):
            bar.validate({'title': 't', 'series': [('a', 'not-a-number')]})

    def test_images_slot_enforces_count(self):
        from videobuilder.compendium.schema import Slot
        slot = Slot('pics', 'images', True, 'a few pictures', min_count=2, max_count=3)
        from videobuilder.compendium.schema import check_value
        with self.assertRaises(SlotError):
            check_value('x', slot, [compendium.kit.sample_photo()])

    def test_bar_chart_series_enforces_bar_count(self):
        bar = compendium.get('bar-chart')
        with self.assertRaises(SlotError):
            bar.validate({'title': 't', 'series': [1.0]})

    def test_bar_chart_handles_an_all_zero_series(self):
        """A series whose values are all 0 must not crash the draw (there is
        no largest value to scale the axis against)."""
        bar = compendium.get('bar-chart')
        film = compendium.component_film(bar, {'title': 't', 'series': [('a', 0), ('b', 0)]})
        film.frame(film.frames - 1, film.formats[0], scale=0.1)


class Fingerprint(unittest.TestCase):
    def test_every_id_has_a_12_hex_fingerprint_stable_across_calls(self):
        for id in (*compendium.ids(), *compendium.recipe_ids()):
            with self.subTest(id=id):
                fp = compendium.fingerprint(id)
                self.assertRegex(fp, r'\A[0-9a-f]{12}\Z')
                self.assertEqual(fp, compendium.fingerprint(id))  # stable across rebuilds of unchanged files

    def test_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            compendium.fingerprint('no-such-id')

    def test_every_recipe_shares_the_recipes_file_fingerprint(self):
        """All recipes live in the one `recipes.py`, so decision 1 ("the
        entry's own source file") makes them share a fingerprint."""
        fps = {compendium.fingerprint(r.id) for r in compendium.RECIPES}
        self.assertEqual(len(fps), 1)

    def test_hash_changes_when_the_file_content_changes(self):
        from videobuilder.compendium.catalog import _hash_file
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'f.py')
            with open(path, 'wb') as fh:
                fh.write(b'hello')
            h1 = _hash_file(path)
            with open(path, 'wb') as fh:
                fh.write(b'world')
            h2 = _hash_file(path)
        self.assertNotEqual(h1, h2)
        self.assertEqual(len(h1), len(h2), 12)

    def test_index_json_exposes_the_fingerprint(self):
        data = compendium.index_data()
        for c in data['components']:
            self.assertEqual(c['fingerprint'], compendium.fingerprint(c['id']))
        for r in data['recipes']:
            self.assertEqual(r['fingerprint'], compendium.fingerprint(r['id']))


class Index(unittest.TestCase):
    def test_markdown_lists_every_component_and_recipe(self):
        md = compendium.index_markdown()
        for c in compendium.CATALOG:
            self.assertIn(c.id, md)
            for s in c.slots:
                self.assertIn(s.name, md)
        for r in compendium.RECIPES:
            self.assertIn(r.id, md)

    def test_json_lists_every_component_and_recipe(self):
        data = json.loads(compendium.index_json())
        self.assertEqual({c['id'] for c in data['components']}, set(compendium.ids()))
        self.assertEqual({r['id'] for r in data['recipes']}, set(compendium.recipe_ids()))

    def test_json_round_trips(self):
        data = compendium.index_data()
        self.assertEqual(json.loads(compendium.index_json()), data)
        self.assertEqual(json.loads(json.dumps(data)), data)


class Check(unittest.TestCase):
    """Every preview must pass the same review check the showcase and
    capability demos do (`tests/test_capabilities.py` runs it the same way):
    storyboard read times, and marks in the safe area with none overlapping,
    skipping frames mid-overlap-transition by design."""

    def _run(self, source):
        with tempfile.TemporaryDirectory() as d:
            film_path = Path(d) / 'film.py'
            film_path.write_text(source)
            return subprocess.run([sys.executable, str(CHECK), str(film_path)],
                                  capture_output=True, text=True, env=ENV)

    @staticmethod
    def _overlap_ok(components):
        pairs = {p for c in components for p in c.overlap_ok}
        return f'OVERLAP_OK = {pairs!r}\n' if pairs else ''

    def test_every_component_preview_passes_check(self):
        for c in compendium.CATALOG:
            with self.subTest(id=c.id):
                src = ('import videobuilder.compendium as compendium\n\n'
                      f'FILM = compendium.component_film(compendium.get({c.id!r}))\n'
                      f'{self._overlap_ok([c])}')
                result = self._run(src)
                self.assertIn('0 failed', result.stdout, result.stdout + result.stderr)

    def test_every_recipe_passes_check(self):
        for r in compendium.RECIPES:
            with self.subTest(id=r.id):
                comps = [compendium.get(s.component) for s in r.steps]
                src = ('import videobuilder.compendium as compendium\n\n'
                      f'FILM = compendium.build_recipe_film(compendium.get_recipe({r.id!r}))\n'
                      f'{self._overlap_ok(comps)}')
                result = self._run(src)
                self.assertIn('0 failed', result.stdout, result.stdout + result.stderr)


class Build(unittest.TestCase):
    def test_build_only_renders_the_given_id(self):
        rendered = []

        def fake_render(film, out, fmt, **kw):
            rendered.append((os.path.basename(out), fmt.width, fmt.height))
            Path(out).write_bytes(b'mp4')

        with tempfile.TemporaryDirectory() as d, mock.patch('videobuilder.render.render', fake_render):
            results = compendium.build(d, only={'stat-counter'})
            ids = {r['id'] for r in results}
            self.assertEqual(ids, {'stat-counter-16x9', 'stat-counter-9x16', 'stat-counter-1x1'})
            for name in ids:
                self.assertTrue((Path(d) / f'{name}.jpg').stat().st_size > 0)
                self.assertTrue((Path(d) / f'{name}.mp4').exists())

    def test_build_rejects_an_unknown_id(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                compendium.build(d, only={'no-such-id'})

    def test_build_writes_the_fingerprint_for_every_clip(self):
        def fake_render(film, out, fmt, **kw):
            Path(out).write_bytes(b'mp4')

        with tempfile.TemporaryDirectory() as d, mock.patch('videobuilder.render.render', fake_render):
            compendium.build(d, only={'stat-counter', compendium.recipe_ids()[0]})
            with open(Path(d) / 'index.json', encoding='utf-8') as fh:
                index = json.load(fh)
        for entry in index['clips']:
            self.assertEqual(entry['fingerprint'], compendium.fingerprint(entry['id']))


if __name__ == '__main__':
    unittest.main()
