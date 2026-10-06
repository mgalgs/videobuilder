import os
import unittest

from videobuilder import Box, Canvas, Font, text

FONT_FILE = os.path.join(os.path.dirname(__file__), '..', 'examples', 'assets', 'Cantarell-VF.otf')
text.register(FONT_FILE)


def pixels(cv):
    return cv.bgra()


class TextBox(unittest.TestCase):
    def test_chip_box_model(self):
        # A chip as a film writes it by hand: padding 0.14 / 0.3 / 0.18 em, line-height 1.08.
        size = 92
        font = Font('Cantarell', size, 850, -0.02, 1.08, css_tracking=True)
        pad = (size * 0.14, size * 0.3, size * 0.18)
        bx = text.box('Apple Orchard', font, pad, x=60, y=1400)
        self.assertEqual(bx.w, text.measure('Apple Orchard', font) + size * 0.6)
        self.assertAlmostEqual(bx.h, size * 1.08 + size * 0.32, places=9)
        self.assertEqual((bx.x, bx.y), (60, 1400))

    def test_button_box_model(self):
        size = 60
        font = Font('Cantarell', size, 850)  # the font's normal line height
        pad = (size * 0.36, size * 0.7)
        bx = text.box('Get Started', font, pad)
        self.assertEqual(bx, Box(0, 0, text.measure('Get Started', font) + size * 1.4,
                                 text.line_height(font) + size * 0.72))

    def test_lines_and_no_padding(self):
        font = Font('Cantarell', 40, line_height=1.5)
        self.assertEqual(text.box(['ab', 'abcd'], font), Box(0, 0, *text.block_size(['ab', 'abcd'], font)))
        self.assertEqual(text.box('', font, 10).h, 60 + 20)  # height is known with no text: for layout tables
        self.assertEqual(text.box([], font, (1, 2, 3, 4)), Box(0, 0, 6, 4))

    def test_draw_in_matches_draw_at_the_padding_offset(self):
        font = Font('Cantarell', 50, 700, -0.02, 1.08, css_tracking=True)
        pad = (7, 15, 9)
        bx = text.box('Chip', font, pad, x=33.5, y=20.25)
        a, b = Canvas(400, 200, '#000000'), Canvas(400, 200, '#000000')
        got = text.draw_in(a, bx, 'Chip', font, '#ffffff', pad)
        want = text.draw(b, 'Chip', font, 33.5 + 15, 20.25 + 7, '#ffffff')
        self.assertEqual(pixels(a), pixels(b))
        self.assertEqual(got, want)
        self.assertEqual((got.right + 15, got.bottom + 9), (bx.right, bx.bottom))

    def test_draw_in_aligns_within_the_padded_width(self):
        font = Font('Cantarell', 30)
        bx = Box(0, 0, 300, 60)
        got = text.draw_in(Canvas(300, 60), bx, 'hi', font, '#ffffff', (5, 10), align='right')
        self.assertAlmostEqual(got.right, 290)
        got = text.draw_in(Canvas(300, 60), bx, 'hi', font, '#ffffff', (5, 10), align='center')
        self.assertAlmostEqual(got.cx, 150)


if __name__ == '__main__':
    unittest.main()
