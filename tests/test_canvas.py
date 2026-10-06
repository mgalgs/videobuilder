import unittest

import videobuilder as vb
from videobuilder import Canvas, rgba


def px(cv, x, y):
    """(r, g, b, a) of a pixel, 0-255 (premultiplied, as cairo stores it)."""
    i = (y * cv.surface.get_stride() // 4 + x) * 4
    b, g, r, a = cv.bgra()[i:i + 4]
    return r, g, b, a


class Colours(unittest.TestCase):
    def test_hex_forms(self):
        self.assertEqual(rgba('#ffffff'), (1, 1, 1, 1))
        self.assertEqual(rgba('#fff'), (1, 1, 1, 1))
        self.assertEqual(rgba('#f00'), rgba('#ff0000'))
        self.assertEqual(rgba('#ff000080'), (1, 0, 0, 128 / 255))
        self.assertEqual(rgba('#f008'), (1, 0, 0, 0x88 / 255))
        self.assertEqual(rgba('1D2327'), rgba('#1D2327'))
        self.assertEqual(rgba('#ff000080', alpha=0.5), (1, 0, 0, 64 / 255))

    def test_tuples(self):
        self.assertEqual(rgba((255, 0, 0)), (1, 0, 0, 1))
        self.assertEqual(rgba((0, 0, 255, 0.25)), (0, 0, 1, 0.25))

    def test_bad_colour_names_the_value(self):
        for bad in ('#ffff0', '#gggggg', 'red', '', '#', (1, 2), (1, 2, 3, 4, 5), 7):
            with self.assertRaises(ValueError) as e:
                rgba(bad)
            self.assertIn(repr(bad), str(e.exception))

    def test_exported(self):
        self.assertIs(vb.rgba, rgba)


class Strokes(unittest.TestCase):
    def test_outline_is_centred_on_the_edge(self):
        cv = Canvas(100, 100, '#000')
        cv.outline(20, 20, 60, 60, '#fff', width=4)
        self.assertEqual(px(cv, 19, 50), (255, 255, 255, 255))  # 18-22: half out,
        self.assertEqual(px(cv, 21, 50), (255, 255, 255, 255))  # half in
        self.assertEqual(px(cv, 17, 50), (0, 0, 0, 255))
        self.assertEqual(px(cv, 23, 50), (0, 0, 0, 255))
        self.assertEqual(px(cv, 50, 50), (0, 0, 0, 255))  # not filled

    def test_outline_alpha_and_line(self):
        cv = Canvas(100, 100)
        cv.outline(10, 10, 80, 80, '#ff000080', width=2)
        self.assertEqual(px(cv, 10, 50), (128, 0, 0, 128))
        cv.line(0, 50.5, 100, 50.5, (0, 255, 0), width=1)
        self.assertEqual(px(cv, 50, 50), (0, 255, 0, 255))
        self.assertEqual(px(cv, 50, 49), (0, 0, 0, 0))


if __name__ == '__main__':
    unittest.main()
