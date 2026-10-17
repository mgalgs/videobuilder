"""vb.looks: the registry, the scene vocabulary, every look painting any
shape of scene, and the motion floor on every look's catalog demo."""
import re
import tempfile
import unittest
from pathlib import Path

import videobuilder as vb
from videobuilder import load, looks

ROOT = Path(__file__).resolve().parent.parent
SEEDED = ('swirl', 'pointillism', 'woodblock', 'melt', 'bauhaus', 'pop-art', 'pixel', 'blueprint')


class Registry(unittest.TestCase):
    def test_the_eight_seeded_looks_in_order(self):
        self.assertEqual(looks.names()[:8], SEEDED)

    def test_get_by_name_alias_or_title_in_any_case_and_spacing(self):
        self.assertIs(looks.get('pop-art'), looks.get('Pop Art'))
        self.assertIs(looks.get('pop-art'), looks.get('pop-art halftone'))
        self.assertIs(looks.get('pop-art'), looks.get('POP'))
        self.assertIs(looks.get('pixel'), looks.get('8-bit'))
        self.assertIs(looks.get('woodblock'), looks.get('Ukiyo-e woodblock'))
        self.assertIs(looks.get('swirl'), looks.get('impressionist'))

    def test_an_unknown_look_names_every_look(self):
        with self.assertRaises(KeyError) as cm:
            looks.get('watercolour')
        for name in SEEDED:
            self.assertIn(name, str(cm.exception))

    def test_every_look_has_a_title_and_a_line(self):
        for name in looks.names():
            look = looks.get(name)
            self.assertTrue(look.title and look.line, name)

    def test_register_refuses_a_taken_name_or_alias(self):
        def paint(cv, scene, t, age):
            pass
        with self.assertRaises(ValueError):
            looks.register(looks.Look('pixel', 'Another pixel', 'x', paint))
        with self.assertRaises(ValueError):
            looks.register(looks.Look('crayon', 'Crayon', 'x', paint, aliases=('8-bit',)))
        self.assertNotIn('crayon', looks.names())
        with self.assertRaises(ValueError):
            looks.Look('Not A Name', 'x', 'x', paint)

    def test_a_videos_own_look_registers_and_paints(self):
        calls = []

        def paint(cv, scene, t, age, tint='#000'):
            calls.append((t, age, tint))
        look = looks.register(looks.Look('test-only-look', 'Test only', 'nothing moves', paint))
        try:
            scene = looks.Scene(100, 100)
            looks.paint(vb.Canvas(100, 100), 'test only', scene, 1.0, tint='#fff')
            looks.get('test-only-look')(vb.Canvas(100, 100), scene, 2.0, 0.5)
            self.assertEqual(calls, [(1.0, 1.0, '#fff'), (2.0, 0.5, '#000')])
        finally:
            looks._REGISTRY.pop(look.name)
            for k in [k for k, v in looks._LOOKUP.items() if v is look]:
                looks._LOOKUP.pop(k)


class SceneVocabulary(unittest.TestCase):
    def test_roles_are_checked(self):
        with self.assertRaises(ValueError):
            looks.Region('tree', [(0, 0), (1, 0), (1, 1)])
        with self.assertRaises(ValueError):
            looks.Region('land', [(0, 0), (1, 0)])

    def test_role_at_front_most_region_then_sky_or_water(self):
        scene = looks.Scene(200, 100, [looks.Region('land', [(0, 40), (100, 40), (100, 100), (0, 100)]),
                                       looks.Region('building', [(20, 10), (40, 10), (40, 60), (20, 60)])],
                            horizon=50)
        self.assertEqual(scene.role_at(30, 50), 'building')
        self.assertEqual(scene.role_at(70, 80), 'land')
        self.assertEqual(scene.role_at(150, 20), 'sky')
        self.assertEqual(scene.role_at(150, 80), 'water')
        self.assertEqual(looks.Scene(200, 100).role_at(150, 80), 'sky')

    def test_open_water_and_ledge_find_the_open_side(self):
        scene = looks.lighthouse(720, 720)
        x0, x1 = scene.open_water()
        self.assertGreater(x0, 200)
        self.assertGreater(x1, 700)
        lx, ly = scene.ledge()
        self.assertLess(lx, 360)
        self.assertLess(ly, scene.horizon)
        self.assertIsNone(looks.Scene(10, 10).open_water())
        self.assertIsNone(looks.Scene(10, 10).ledge())

    def test_stars_are_seeded_and_clear_of_the_sun(self):
        a, b = looks.lighthouse(720, 720), looks.lighthouse(720, 720)
        self.assertEqual(a.stars, b.stars)
        sx, sy, sr = a.sun
        for x, y, _ in a.stars:
            self.assertGreater((x - sx) ** 2 + (y - sy) ** 2, sr ** 2)
            self.assertLess(y, a.horizon)


class EveryLookPaintsAnyScene(unittest.TestCase):
    SENTINEL = (255, 0, 255)

    def _corners_painted(self, cv):
        cv.surface.flush()
        data, stride = bytes(cv.surface.get_data()), cv.surface.get_stride()
        w, h = cv.surface.get_width(), cv.surface.get_height()
        for x, y in ((1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2), (w // 2, h // 2)):
            b, g, r = data[y * stride + 4 * x: y * stride + 4 * x + 3]
            self.assertNotEqual((r, g, b), self.SENTINEL, f'pixel {x},{y} left unpainted')

    def test_every_look_paints_every_pixel_in_three_shapes_and_a_bare_scene(self):
        scenes = [looks.lighthouse(w, h, 0.4) for w, h in ((720, 720), (1280, 720), (720, 1280))]
        scenes.append(looks.Scene(640, 360))                                    # no regions, no water, no sun
        scenes.append(looks.Scene(640, 360, [looks.Region('figure', [(300, 100), (340, 100), (320, 300)])],
                                  horizon=200, beacon=(320, 120)))               # water, no land, no sun
        for name in looks.names():
            for scene in scenes:
                with self.subTest(look=name, w=scene.w, h=scene.h, regions=len(scene.regions)):
                    cv = vb.Canvas(int(scene.w), int(scene.h), background=self.SENTINEL, scale=0.25)
                    for t, age in ((0.0, 0.0), (1.3, 0.4), (7.9, 7.9)):
                        looks.paint(cv, name, scene, t, age)
                    self._corners_painted(cv)

    def test_relay_wipes_from_one_look_to_the_next(self):
        scene = looks.lighthouse(320, 320)
        cv = vb.Canvas(320, 320, scale=0.5)
        self.assertEqual(looks.relay(cv, scene, 0.5, ['pixel', 'melt'], hold=1.0, wipe=0.4), 'pixel')
        self.assertEqual(looks.relay(cv, scene, 1.2, ['pixel', 'melt'], hold=1.0, wipe=0.4), 'melt')
        self.assertEqual(looks.relay(cv, scene, 2.6, ['pixel', 'melt'], hold=1.0, wipe=0.4), 'pixel')


class MotionFloor(unittest.TestCase):
    """Every seeded look keeps its signature motion on its catalog demo: at
    least looks.FLOOR of the frame's tiles move while it holds."""

    def test_every_look_demo_clears_the_floor(self):
        for name in SEEDED:
            with self.subTest(look=name):
                film = load(str(ROOT / 'examples' / 'capabilities' / f'look-{name}.py'))
                score = looks.motion_floor(film, 15, film.frames - 1)
                self.assertGreaterEqual(score, looks.FLOOR, f'{name}: only {100 * score:.0f}% of the frame moves')

    def test_a_still_picture_fails_the_floor(self):
        film = vb.Film(draw=lambda n, cv: cv.fill('#123456'), fps=30, frames=60, formats=(vb.Format('t', 240, 240),))
        self.assertLess(looks.motion_floor(film, 0, 59), looks.FLOOR)


class ReferenceDoc(unittest.TestCase):
    DOC = ROOT / 'skill' / 'make-a-video' / 'reference' / 'looks.md'

    def test_the_adoption_example_runs_in_both_shapes_and_moves(self):
        example = next(block for block in re.findall(r'```python\n(.*?)```', self.DOC.read_text(), re.DOTALL)
                       if 'FILM = ' in block)
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'film.py').write_text(example)
            film = load(str(Path(d, 'film.py')))
            for fmt in film.formats:
                film.frame(60, fmt, scale=0.25)
            self.assertGreaterEqual(looks.motion_floor(film, 0, film.frames - 1), looks.FLOOR)

    def test_the_doc_covers_every_seeded_look(self):
        doc = self.DOC.read_text()
        for name in SEEDED:
            self.assertIn(f'| `{name}` |', doc)


if __name__ == '__main__':
    unittest.main()
