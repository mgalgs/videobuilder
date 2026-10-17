"""vb.impact: seeded speed lines, a two-tone silhouette, a shake that settles, and the Hit that strings them."""
import unittest

import videobuilder as vb
from videobuilder import impact


def pixels(cv):
    cv.surface.flush()
    return bytes(cv.surface.get_data())


def at(cv, x, y):
    cv.surface.flush()
    stride = cv.surface.get_stride()
    b, g, r, _ = cv.surface.get_data()[y * stride + x * 4:y * stride + x * 4 + 4]
    return r, g, b


class Pieces(unittest.TestCase):
    def test_speed_lines_are_seeded(self):
        a, b, c = (vb.Canvas(200, 200, background='#000') for _ in range(3))
        impact.speed_lines(a, 100, 100, 7, 40, colour='#fff')
        impact.speed_lines(b, 100, 100, 7, 40, colour='#fff')
        impact.speed_lines(c, 100, 100, 8, 40, colour='#fff')
        self.assertEqual(pixels(a), pixels(b))
        self.assertNotEqual(pixels(a), pixels(c))
        self.assertEqual(at(a, 100, 100), (0, 0, 0))           # the middle is left clear

    def test_a_silhouette_is_one_flat_colour_in_the_subjects_shape(self):
        cv = vb.Canvas(100, 100, background='#ffffff')

        def subject(c):
            c.rect(20, 20, 30, 30, '#ff8800')
            c.rect(30, 30, 10, 10, '#0000ff')
            c.mark('thing', 20, 20, 30, 30)
        impact.silhouette(cv, subject, '#101010')
        self.assertEqual(at(cv, 25, 25), (16, 16, 16))
        self.assertEqual(at(cv, 35, 35), (16, 16, 16))
        self.assertEqual(at(cv, 70, 70), (255, 255, 255))
        self.assertEqual([n for n, _ in cv.marks], ['thing'])

    def test_a_shake_settles_and_repeats(self):
        self.assertEqual(impact.shake(9, 10), (0.0, 0.0))
        self.assertEqual(impact.shake(22, 10, frames=12), (0.0, 0.0))
        first = impact.shake(10, 10, amount=20)
        self.assertGreater(abs(first[0]), 10)
        self.assertLess(abs(impact.shake(20, 10, amount=20)[0]), 1)
        self.assertEqual(impact.shake(13, 10, seed=2), impact.shake(13, 10, seed=2))


class Hit(unittest.TestCase):
    def test_holds_one_to_three_frames(self):
        with self.assertRaises(ValueError):
            impact.Hit(at=10, hold=4)
        with self.assertRaises(ValueError):
            impact.Hit(at=10, settle=-1)

    def test_push_settle_flash_and_linger_can_each_be_left_out(self):
        for part in ('push', 'settle', 'flash', 'linger'):
            hit = impact.Hit(at=10, **{part: 0})
            first, end = hit.span
            for n in range(first - 1, end + 1):
                hit.draw(vb.Canvas(60, 60), n, lambda c: c.fill('#336699'), lambda c: c.rect(25, 25, 10, 10, '#f00'))
        self.assertEqual(impact.Hit(at=10, settle=0).zoom_at(12), 1)

    def test_outside_its_span_it_is_just_the_scene_and_held_frames_are_two_tone(self):
        hit = impact.Hit(at=30, push=6, hold=2, ink='#000000', paper='#ffffff')
        first, end = hit.span
        self.assertEqual(first, 24)

        def scene(c):
            c.fill('#336699')

        def subject(c):
            c.rect(90, 90, 20, 20, '#ff0000')
        for n, expect in ((first - 1, (0x33, 0x66, 0x99)), (end, (0x33, 0x66, 0x99))):
            cv = vb.Canvas(200, 200)
            hit.draw(cv, n, scene, subject)
            self.assertEqual(at(cv, 5, 100), expect)
        for n in (30, 31):
            cv = vb.Canvas(200, 200)
            hit.draw(cv, n, scene, subject)
            self.assertEqual(at(cv, 100, 100), (0, 0, 0))      # the subject, in ink
            self.assertEqual(at(cv, 100, 60), (255, 255, 255))   # paper, inside the clear middle
        self.assertTrue(hit.held(31) and not hit.held(32))
        self.assertGreater(hit.zoom_at(30), hit.zoom_at(27) > 1)
        self.assertAlmostEqual(hit.zoom_at(32 + hit.settle), 1)
