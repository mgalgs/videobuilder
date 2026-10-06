import unittest
from pathlib import Path

from videobuilder import Box, Canvas, Font, text

FONT_FILE = Path(__file__).resolve().parent.parent / 'examples' / 'assets' / 'Cantarell-VF.otf'
text.register(FONT_FILE)


def rounded(box):
    return tuple(round(v, 6) for v in box)


class Marks(unittest.TestCase):
    def test_mark_lands_where_the_layer_puts_it(self):
        cv = Canvas(400, 300)
        cv.mark('plain', 10, 20, 30, 40)
        with cv.layer(dx=100, dy=50):
            with cv.layer(scale=2):
                cv.mark('moved', 10, 20, 30, 40)
        self.assertEqual([(n, rounded(b)) for n, b in cv.marks],
                         [('plain', (10, 20, 30, 40)), ('moved', (120, 90, 60, 80))])

    def test_mark_in_film_px_on_a_scaled_canvas(self):
        cv = Canvas(400, 300, scale=0.25)  # a preview: quarter-size pixels, same coordinates
        with cv.layer(dx=8):
            box = cv.mark('a', 10, 20, 30, 40)
        self.assertEqual(rounded(box), (18, 20, 30, 40))

    def test_unseen_marks_are_skipped(self):
        cv = Canvas(400, 300)
        with cv.layer(opacity=0, dx=100):
            self.assertIsNone(cv.mark('hidden', 0, 0, 10, 10))
        with cv.layer(opacity=0.5):
            self.assertIsNotNone(cv.mark('faint', 0, 0, 10, 10))
        self.assertEqual([n for n, _ in cv.marks], ['faint'])

    def test_text_draw_returns_its_box(self):
        cv = Canvas(800, 400)
        font = Font('Cantarell', 40, line_height=1.5)
        lines = ['wide line of text', 'short']
        w, h = text.block_size(lines, font)
        box = text.draw(cv, lines, font, 100, 50, '#ffffff')
        self.assertEqual(rounded(box), rounded((100, 50, w, 120)))
        self.assertEqual(h, 120)
        right = text.draw(cv, 'short', font, 100, 50, '#ffffff', align='right', width=500)
        self.assertAlmostEqual(right.right, 600)
        self.assertAlmostEqual(right.w, text.measure('short', font))


class Containment(unittest.TestCase):
    def test_contains(self):
        safe = Box(60, 220, 880, 1320)
        self.assertTrue(safe.contains(Box(60, 220, 880, 1320)))
        self.assertTrue(safe.contains(Box(59.6, 300, 100, 100)))  # within half a pixel
        self.assertFalse(safe.contains(Box(59, 300, 100, 100)))
        self.assertFalse(safe.contains(Box(900, 300, 100, 100)))
        self.assertTrue(safe.contains(Box(59, 300, 100, 100), tolerance=1))

    def test_intersects(self):
        a = Box(0, 0, 100, 100)
        self.assertTrue(a.intersects(Box(50, 50, 100, 100)))
        self.assertFalse(a.intersects(Box(100, 0, 50, 50)))  # touching edges
        self.assertFalse(a.intersects(Box(0, 100.3, 50, 50)))
        self.assertFalse(a.intersects(Box(99.7, 0, 50, 50)))  # anti-aliasing slop
        self.assertTrue(a.intersects(Box(99, 0, 50, 50)))


if __name__ == '__main__':
    unittest.main()
