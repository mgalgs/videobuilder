"""The compendium: the component format, the seed components, the reference
recipes, the index, and `compendium build`."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videobuilder import compendium
from videobuilder.compendium.schema import KINDS, SlotError

ROOT = Path(__file__).resolve().parent.parent


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

    def test_missing_optional_slot_falls_back_to_the_sample(self):
        out = self.c.validate({'headline': 'ok'})
        self.assertEqual(out['accent'], self.c.sample['accent'])

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


if __name__ == '__main__':
    unittest.main()
