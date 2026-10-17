"""vb.looks filter looks: the registry and how names resolve between scene
and filter looks, the offscreen block (what it treats, what it leaves), every
filter treating any picture purely, and the motion floor on a still
picture for every filter's catalog demo."""
import re
import unittest
from pathlib import Path

import videobuilder as vb
from videobuilder import load, looks
from videobuilder.looks import fx

ROOT = Path(__file__).resolve().parent.parent
SEEDED = ('pop-art', 'pixel', 'woodblock', 'blueprint', 'pointillism')


def _pixel(cv, x, y):
    cv.surface.flush()
    data, stride = bytes(cv.surface.get_data()), cv.surface.get_stride()
    b, g, r = data[y * stride + 4 * x: y * stride + 4 * x + 3]
    return r, g, b


def _picture(cv):
    """A stand-in capture: a light page, a dark header, a coloured chart."""
    cv.fill('#f4f6fa')
    cv.rect(0, 0, cv.width, cv.height * 0.15, '#1b2333')
    for i in range(6):
        cv.rect(cv.width * (0.1 + i * 0.13), cv.height * (0.8 - 0.08 * i), cv.width * 0.08,
                cv.height * (0.08 * i + 0.1), ('#3a6ff0', '#f0644a')[i % 2])


class Registry(unittest.TestCase):
    def test_the_five_seeded_filters_in_order(self):
        self.assertEqual(looks.filters()[:5], SEEDED)

    def test_a_filter_shares_its_scene_looks_names_aliases_and_title(self):
        for name in SEEDED:
            scene_look = looks.get(name)
            for key in (scene_look.name, scene_look.title, *scene_look.aliases):
                with self.subTest(name=name, key=key):
                    self.assertIs(looks.get_filter(key), looks.get_filter(name))
        self.assertIs(looks.get_filter('comic'), looks.get_filter('pop-art'))
        self.assertIs(looks.get_filter('8-bit'), looks.get_filter('pixel'))
        self.assertIs(looks.get_filter('Pop-art filter'), looks.get_filter('pop-art'))

    def test_the_call_decides_the_kind_paint_finds_scene_looks_filter_finds_filters(self):
        self.assertIsInstance(looks.get('pop-art'), looks.Look)
        self.assertIsInstance(looks.get_filter('pop-art'), looks.Filter)
        self.assertNotIn('pop-art filter', [looks.get(n).title.lower() for n in looks.names()])

    def test_a_scene_only_look_has_no_filter_and_says_so(self):
        with self.assertRaises(KeyError) as cm:
            looks.get_filter('melt')
        self.assertIn('scene look only', str(cm.exception))
        with self.assertRaises(KeyError) as cm:
            looks.get_filter('watercolour')
        for name in SEEDED:
            self.assertIn(name, str(cm.exception))

    def test_register_filter_refuses_a_taken_key(self):
        def treat(im, t, age, u):
            return im
        with self.assertRaises(ValueError):
            looks.register_filter(looks.Filter('pixel', 'Another', 'x', treat))
        with self.assertRaises(ValueError):
            looks.register_filter(looks.Filter('crayon', 'Crayon', 'x', treat, aliases=('comic',)))
        self.assertNotIn('crayon', looks.filters())

    def test_only_pixel_steps_its_time(self):
        self.assertEqual(looks.get_filter('pixel').step(1.3), 1.25)
        self.assertEqual(looks.get_filter('pop-art').step(1.3), 1.3)

    def test_no_filter_imports_numpy(self):
        for path in (ROOT / 'videobuilder' / 'looks' / 'fx').glob('*.py'):
            self.assertNotRegex(path.read_text(), r'(?m)^\s*(import|from)\s+numpy', path.name)


class TheBlock(unittest.TestCase):
    def test_the_body_draws_on_cv_and_the_whole_frame_is_treated(self):
        calls = []

        def treat(im, t, age, u, tint=(0, 0, 0)):
            calls.append((im.size, t, age, round(u, 3), im.getpixel((5, 5)), tint))
            return vb.looks.fx.Image.new('RGB', im.size, tint)
        flt = looks.register_filter(looks.Filter('test-only-filter', 'Test only filter', 'x', treat))
        try:
            cv = vb.Canvas(200, 100, background='#ff0000', scale=0.5)
            with looks.filter(cv, 'test only filter', 2.0, tint=(0, 0, 255)) as inner:
                self.assertIs(inner, cv)
                cv.rect(0, 0, 40, 40, '#00ff00')          # drawn offscreen, in frame px
            self.assertEqual(calls, [((100, 50), 2.0, 2.0, round(50 / 1080, 3), (0, 255, 0), (0, 0, 255))])
            self.assertEqual(_pixel(cv, 80, 40), (0, 0, 255))
            cv.rect(0, 0, 10, 10, '#ffffff')               # after the block: drawn as usual
            self.assertEqual(_pixel(cv, 1, 1), (255, 255, 255))
        finally:
            looks._FILTERS.pop(flt.name)
            for k in [k for k, v in looks._FILTER_LOOKUP.items() if v is flt]:
                del looks._FILTER_LOOKUP[k]

    def test_a_box_treats_only_its_pixels(self):
        cv = vb.Canvas(240, 240, background='#f4f6fa')
        with looks.filter(cv, 'blueprint', 1.0, box=(120, 0, 120, 240)):
            _picture(cv)
        self.assertEqual(_pixel(cv, 60, 200), (244, 246, 250))     # outside the box: untouched
        self.assertNotEqual(_pixel(cv, 180, 200), (244, 246, 250))

    def test_an_error_in_the_body_leaves_the_canvas_drawable(self):
        cv = vb.Canvas(64, 64)
        surface = cv.surface
        with self.assertRaises(RuntimeError):
            with looks.filter(cv, 'pixel', 0.0):
                raise RuntimeError('boom')
        self.assertIs(cv.surface, surface)
        cv.rect(0, 0, 64, 64, '#ffffff')
        self.assertEqual(_pixel(cv, 10, 10), (255, 255, 255))

    def test_marks_inside_the_block_land_in_frame_px(self):
        cv = vb.Canvas(200, 200, scale=0.5)
        with looks.filter(cv, 'pop-art', 0.0):
            cv.mark('chip', 10, 20, 30, 40)
        self.assertEqual(cv.marks[0][0], 'chip')
        self.assertEqual(tuple(round(v) for v in cv.marks[0][1]), (10, 20, 30, 40))


class EveryFilterTreatsAnyPicture(unittest.TestCase):
    def test_every_filter_keeps_the_size_in_three_shapes_and_is_pure(self):
        for name in looks.filters():
            for w, h, scale in ((720, 720, 0.25), (1280, 720, 0.25), (720, 1280, 0.25), (64, 48, 1.0)):
                with self.subTest(filter=name, w=w, h=h):
                    frames = []
                    for t in (1.3, 0.0, 1.3):
                        cv = vb.Canvas(w, h, scale=scale)
                        with looks.filter(cv, name, t, t):
                            _picture(cv)
                        frames.append(cv.bgra())
                    self.assertEqual(frames[0], frames[2])         # any frame, alone, in any order
                    self.assertNotEqual(frames[0], frames[1])      # and it moves

    def test_a_filter_changes_the_picture(self):
        plain = vb.Canvas(360, 360, scale=0.5)
        _picture(plain)
        for name in looks.filters():
            with self.subTest(filter=name):
                cv = vb.Canvas(360, 360, scale=0.5)
                with looks.filter(cv, name, 0.7):
                    _picture(cv)
                self.assertNotEqual(cv.bgra(), plain.bgra())


class MotionFloor(unittest.TestCase):
    """Every seeded filter moves on its own over a still picture: its demo
    holds a screenshot or a photo still, and at least looks.FLOOR of the
    frame's tiles still move."""

    def test_every_filter_demo_clears_the_floor_on_a_still_picture(self):
        for name in SEEDED:
            with self.subTest(filter=name):
                film = load(str(ROOT / 'examples' / 'capabilities' / f'look-filter-{name}.py'))
                score = looks.motion_floor(film, 15, film.frames - 1)
                self.assertGreaterEqual(score, looks.FLOOR, f'{name}: only {100 * score:.0f}% of the frame moves')


class ReferenceDoc(unittest.TestCase):
    DOC = ROOT / 'skill' / 'make-a-video' / 'reference' / 'looks.md'

    def test_the_doc_covers_every_filter_and_the_resolution_rule(self):
        doc = self.DOC.read_text()
        for name in SEEDED:
            self.assertIn(f'| `{name}` |', doc[doc.index('## Filter looks'):])
        self.assertIn('looks.filter(cv,', doc)
        self.assertNotIn("can't restyle a photo, a screen capture or footage", doc)

    def test_the_filter_example_runs_and_moves(self):
        example = next(block for block in re.findall(r'```python\n(.*?)```', self.DOC.read_text(), re.DOTALL)
                       if 'looks.filter(' in block and 'FILM = ' in block)
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'film.py').write_text(example)
            film = load(str(Path(d, 'film.py')))
            for fmt in film.formats:
                film.frame(30, fmt, scale=0.25)
            self.assertGreaterEqual(looks.motion_floor(film, 0, film.frames - 1), looks.FLOOR)


if __name__ == '__main__':
    unittest.main()
