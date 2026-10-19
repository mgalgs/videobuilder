"""vb.type: the registry, the props every style shares (one clear error for
a bad one), every style laid out inside tall, wide and square frames with no
line leaving it, the hold that keeps moving (the motion floor), a style over
another picture or in a box, and its sound on the fixture pack."""
import logging
import os
import unittest
from pathlib import Path
from unittest import mock

import videobuilder as vb
from videobuilder import load, sfx
from videobuilder import type as vt

ROOT = Path(__file__).resolve().parent.parent
STYLES = ('split-flap', 'typewriter', 'terminal', 'rubber', 'rack-focus', 'letter-cloud', 'editorial')
LINES = ('Gate 14', 'Now boarding', 'Lisbon 09:40')
SHAPES = (vb.Format('tall', 540, 960), vb.Format('wide', 960, 540), vb.Format('square', 720, 720))


def _pixel(cv, x, y):
    cv.surface.flush()
    data, stride = bytes(cv.surface.get_data()), cv.surface.get_stride()
    b, g, r = data[y * stride + 4 * x: y * stride + 4 * x + 3]
    return r, g, b


class Registry(unittest.TestCase):
    def test_the_styles_in_order(self):
        self.assertEqual(vt.names(), STYLES)

    def test_get_by_name_alias_or_title_in_any_case_and_spacing(self):
        self.assertIs(vt.get('split-flap'), vt.get('Split Flap'))
        self.assertIs(vt.get('split-flap'), vt.get('departures board'))
        self.assertIs(vt.get('split-flap'), vt.get('Split-flap board'))
        self.assertIs(vt.get('rack-focus'), vt.get('focus pull'))
        self.assertIs(vt.get('letter-cloud'), vt.get('3D letters'))
        self.assertIs(vt.get('editorial'), vt.get('magazine cover'))
        self.assertIs(vt.get('terminal'), vt.get('command line'))
        self.assertIs(vt.get('rubber'), vt.get('bouncy letters'))

    def test_an_unknown_style_names_every_style(self):
        with self.assertRaises(KeyError) as cm:
            vt.get('neon sign')
        for name in STYLES:
            self.assertIn(name, str(cm.exception))

    def test_every_style_has_a_title_and_a_line(self):
        for name in vt.names():
            style = vt.get(name)
            self.assertTrue(style.title and style.line, name)

    def test_register_refuses_a_taken_name_or_alias(self):
        def draw(cv, p, t, box, clock):
            pass
        with self.assertRaises(ValueError):
            vt.register(vt.Style('rubber', 'Another rubber', 'x', draw))
        with self.assertRaises(ValueError):
            vt.register(vt.Style('neon', 'Neon', 'x', draw, aliases=('magazine',)))
        self.assertNotIn('neon', vt.names())
        with self.assertRaises(ValueError):
            vt.Style('Not A Name', 'x', 'x', draw)

    def test_vb_type_is_the_package(self):
        self.assertIs(vb.type, vt)
        self.assertNotIn('type', vb.__all__)    # `from videobuilder import *` keeps the builtin


class Props(unittest.TestCase):
    def test_defaults_and_the_shapes_lines_come_in(self):
        p = vt.props(lines='Gate 14\nNow  boarding ')
        self.assertEqual(p.lines, ('Gate 14', 'Now boarding'))
        self.assertEqual((p.ink, p.paper, p.accent, p.length, p.sound, p.font),
                         (vt.INK, vt.PAPER, vt.ACCENT, 6.0, False, None))
        self.assertEqual(vt.props(['a', 'b']).lines, ('a', 'b'))
        self.assertEqual(vt.props({'lines': ['a'], 'accent': '#fff'}).accent, '#fff')
        q = vt.props(p, length=18, paper=None)
        self.assertEqual((q.lines, q.length, q.paper), (p.lines, 18.0, None))
        self.assertEqual(vt.props(q), q)

    def test_a_bad_prop_gets_one_clear_error(self):
        cases = {
            'no lines': ({}, 'lines is required'),
            'five lines': ({'lines': ['a'] * 5}, '1 to 4 short lines, not 5'),
            'no lines at all': ({'lines': []}, '1 to 4 short lines, not 0'),
            'an empty line': ({'lines': ['a', '  ']}, 'line 2 is empty'),
            'a long line': ({'lines': ['x' * 30]}, 'line 1 is 30 characters'),
            'not text': ({'lines': [1, 2]}, 'string or a list of strings'),
            'a bad colour': ({'lines': ['a'], 'ink': 'tomato'}, 'ink must be a colour'),
            'no accent': ({'lines': ['a'], 'accent': None}, 'accent must be a colour'),
            'too long': ({'lines': ['a'], 'length': 90}, 'length is seconds, 2 to 30'),
            'length as text': ({'lines': ['a'], 'length': '6'}, 'length is seconds'),
            'sound as text': ({'lines': ['a'], 'sound': 'yes'}, 'sound is True or False'),
            'an unknown prop': ({'lines': ['a'], 'colour': '#fff'}, 'unknown prop colour'),
            'an empty font': ({'lines': ['a'], 'font': ' '}, 'font is a font family'),
        }
        for name, (kw, message) in cases.items():
            with self.subTest(name), self.assertRaises(vt.PropsError) as cm:
                vt.props(**kw)
            self.assertIn(message, str(cm.exception))
            self.assertIsInstance(cm.exception, ValueError)
        with self.assertRaises(vt.PropsError):          # draw and film check them too
            vt.draw(vb.Canvas(100, 100), 'rubber', {'lines': ['a'] * 6}, 1.0)
        with self.assertRaises(vt.PropsError):
            vt.film('rubber', ['a'], length=1)

    def test_the_clock_splits_a_run_into_enter_hold_and_exit(self):
        c = vt.Clock(6.0)
        self.assertEqual((round(c.hold, 2), round(c.exit, 2)), (2.4, 5.1))
        c = vt.Clock(18.0)
        self.assertEqual((c.hold, round(c.exit, 2)), (4.0, 16.6))
        for name in STYLES:
            for length in (3.0, 6.0, 18.0):
                with self.subTest(name=name, length=length):
                    c = vt.get(name).clock(vt.props(LINES, length=length))
                    self.assertTrue(0 < c.hold < c.exit < length)


class EveryStyleInEveryShape(unittest.TestCase):
    """Every style in a tall, a wide and a square frame, sampled through its
    whole run: every line it marks sits inside the frame, every line is
    marked (legible) at some point before the exit, and nothing is drawn before
    it starts or after it ends but its ground."""

    def _marks(self, name, fmt, p, times, scale=0.25):
        out = []
        for t in times:
            cv = vb.Canvas(fmt.width, fmt.height, scale=scale, format=fmt)
            vt.draw(cv, name, p, t)
            out.append((t, cv))
        return out

    def test_no_line_leaves_the_frame(self):
        for lines in (LINES, ('Ok',), ('One', 'Two', 'Three', 'Four four four four')):
            p = vt.props(lines)
            for name in STYLES:
                clock = vt.get(name).clock(p)
                times = [i * 0.2 for i in range(int(p.length / 0.2))]
                for fmt in SHAPES:
                    with self.subTest(style=name, shape=fmt.name, lines=len(lines)):
                        frame = vb.Box(0, 0, fmt.width, fmt.height)
                        seen = set()
                        for t, cv in self._marks(name, fmt, p, times):
                            for mark, box in cv.marks:
                                self.assertTrue(frame.contains(box, tolerance=1), f'{mark} at {t:.1f}s: {box}')
                                if t < clock.exit:
                                    seen.add(mark)
                        self.assertEqual(seen, {f'line-{i}' for i in range(len(lines))})

    def test_only_the_ground_outside_the_run(self):
        p = vt.props(LINES, paper='#203040')
        for name in STYLES:
            for t in (-0.5, p.length, p.length + 1):
                cv = vb.Canvas(200, 200)
                vt.draw(cv, name, p, t)
                cv.surface.flush()
                self.assertEqual({_pixel(cv, x, y) for x in range(0, 200, 23) for y in range(0, 200, 23)},
                                 {(0x20, 0x30, 0x40)}, f'{name} at {t}')

    def test_over_a_picture_and_in_a_box(self):
        """paper=None draws over what is there; a box keeps the style in it."""
        for name in STYLES:
            with self.subTest(style=name):
                p = vt.props(LINES, paper=None)
                clock = vt.get(name).clock(p)
                cv = vb.Canvas(480, 270)
                cv.fill('#3a6ff0')
                vt.draw(cv, name, p, (clock.hold + clock.exit) / 2)
                same = sum(_pixel(cv, x, y) == (0x3a, 0x6f, 0xf0) for x in range(0, 480, 12) for y in range(0, 270, 12))
                # (a board's flaps are the split-flap's own: it covers the most)
                self.assertGreater(same / (40 * 23), 0.2, 'the picture should still show round the letters')
                cv = vb.Canvas(480, 270)
                cv.fill('#ffffff')
                box = (0, 135, 480, 135)
                vt.draw(cv, name, LINES, (clock.hold + clock.exit) / 2, box=box)
                self.assertEqual(_pixel(cv, 240, 60), (255, 255, 255))     # above the box: untouched
                self.assertTrue(cv.marks)
                for mark, b in cv.marks:
                    self.assertTrue(vb.Box(*box).contains(b, tolerance=1), (mark, b))


class MotionFloor(unittest.TestCase):
    """Every style keeps moving through its hold: at least vt.FLOOR of the
    frame's tiles change, in every shape, at 6 s and late in an 18 s run."""

    def test_every_style_holds_moving(self):
        p = vt.props(LINES)
        for name in STYLES:
            clock = vt.get(name).clock(p)
            for fmt in SHAPES:
                with self.subTest(style=name, shape=fmt.name):
                    film = vt.film(name, p, formats=(fmt,))
                    score = vt.motion_floor(film, round(clock.hold * 30) + 1, round(clock.exit * 30) - 1)
                    self.assertGreaterEqual(score, vt.FLOOR, f'{name}: only {100 * score:.0f}% of the frame moves')

    def test_a_long_hold_never_comes_to_rest(self):
        p = vt.props(LINES, length=18)
        for name in STYLES:
            with self.subTest(style=name):
                film = vt.film(name, p, formats=(SHAPES[0],))
                clock = vt.get(name).clock(p)
                late = round((clock.exit - 3) * 30)
                self.assertGreaterEqual(vt.motion_floor(film, late, late + 60), vt.FLOOR)

    def test_a_still_title_fails_the_floor(self):
        film = vb.Film(draw=lambda n, cv: vb.text.draw(cv, ['Gate 14'], vb.Font('sans-serif', 60), 40, 200, '#fff'),
                       fps=30, frames=60, formats=(SHAPES[0],))
        self.assertLess(vt.motion_floor(film, 0, 59), vt.FLOOR)


class Film(unittest.TestCase):
    def test_a_style_as_a_film_of_its_own(self):
        film = vt.film('rubber', LINES, length=18, at=0.5)
        self.assertEqual((film.fps, film.frames), (30, 555))
        self.assertEqual([f.name for f in film.formats], ['9x16', '16x9', '1x1'])
        self.assertEqual(film.sounds, ())
        self.assertEqual(film.keyframes[0][1], 'hold')
        film.frame(film.keyframes[0][0], '1x1', scale=0.2)

    def test_relay_plays_each_in_turn(self):
        cv = vb.Canvas(200, 200)
        self.assertEqual(vt.relay(cv, ['rubber', 'editorial'], LINES, 1.0, each=3.0), 'rubber')
        self.assertEqual(vt.relay(cv, ['rubber', 'editorial'], LINES, 4.0, each=3.0), 'editorial')
        self.assertEqual(vt.relay(cv, ['rubber', 'editorial'], LINES, 7.0, each=3.0), 'rubber')


class Sound(unittest.TestCase):
    """The fixture pack (tests/__init__.py) stands in for the real one: a
    style takes its own sound where the pack has it, else the nearest role."""

    def test_off_by_default_and_none_for_a_silent_style(self):
        self.assertEqual(vt.sounds('split-flap', LINES), ())
        self.assertEqual(vt.sounds('editorial', vt.props(LINES, sound=True)), ())
        self.assertEqual(vt.sounds('rack-focus', vt.props(LINES, sound=True)), ())

    def test_each_sounding_style_places_its_sounds_in_its_run(self):
        roles = {'split-flap': {'tick'}, 'typewriter': {'click', 'ding'}, 'terminal': {'click'},
                 'rubber': {'tick', 'click'}}
        for name, want in roles.items():
            with self.subTest(style=name):
                p = vt.props(LINES, sound=True)
                placed = vt.sounds(name, p, at=30)
                self.assertTrue(placed)
                self.assertTrue(all(isinstance(s, sfx.Sfx) for s in placed))
                self.assertLessEqual({sfx.get(s.effect).role for s in placed}, want | {'tick', 'click'})
                self.assertTrue(all(30 <= s.mark <= 30 + p.length * 30 for s in placed))
                self.assertLessEqual(len(placed), 90)
                film = vt.film(name, p)
                self.assertEqual(len(film.sounds), len(vt.sounds(name, p)))
        keys = vt.sounds('typewriter', vt.props(LINES, sound=True))
        self.assertEqual(sum(1 for s in keys if sfx.get(s.effect).role == 'ding'), 1)   # the bell
        self.assertEqual(len(keys), sum(len(ln) for ln in LINES) + 1)

    def test_without_the_pack_the_style_draws_and_says_so_once(self):
        with mock.patch.dict(os.environ, {sfx.ENV: '/nonexistent/vb-sfx'}), \
                mock.patch.object(vt, '_noted', set()):
            with self.assertLogs('videobuilder.type', logging.WARNING) as logs:
                film = vt.film('split-flap', vt.props(LINES, sound=True), formats=(SHAPES[2],))
                vt.sounds('rubber', vt.props(LINES, sound=True))
            self.assertEqual(film.sounds, ())
            self.assertEqual(len(logs.output), 1)
            self.assertIn('sfx fetch', logs.output[0])
            film.frame(90, scale=0.2)


class Demos(unittest.TestCase):
    """The capability demos (examples/capabilities/type-*.py) load and draw."""

    def test_every_style_has_a_demo_that_holds_moving(self):
        for name in STYLES:
            with self.subTest(style=name):
                film = load(str(ROOT / 'examples' / 'capabilities' / f'type-{name}.py'))
                film.frame(film.frames // 2, scale=0.25)
        film = load(str(ROOT / 'examples' / 'capabilities' / 'type.py'))
        film.frame(film.frames // 2, scale=0.25)


if __name__ == '__main__':
    unittest.main()
