import hashlib
import unittest

import videobuilder as vb
from videobuilder import Canvas, halftone_pattern, rgba


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
    def test_arc_strokes_only_the_requested_quadrant(self):
        import math
        cv = Canvas(100, 100, '#000')
        cv.arc(50, 50, 30, 0, math.pi / 2, '#fff', 6)
        self.assertEqual(px(cv, 71, 71), (255, 255, 255, 255))
        for x, y in ((50, 50), (29, 71), (71, 29), (76, 76)):
            self.assertEqual(px(cv, x, y), (0, 0, 0, 255))

    def test_sector_obeys_layers_clips_and_alpha(self):
        import math
        cv = Canvas(100, 100, '#000')
        with cv.layer(dx=10, dy=10), cv.clip(20, 20, 15, 30):
            cv.sector(20, 20, 30, 0, math.pi / 2, '#f00', alpha=0.5)
        self.assertEqual(px(cv, 35, 35), (128, 0, 0, 255))
        self.assertEqual(px(cv, 50, 35), (0, 0, 0, 255))
        self.assertEqual(px(cv, 25, 25), (0, 0, 0, 255))

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


class Pixelated(unittest.TestCase):
    def test_output_is_blocky(self):
        """A shape with a boundary that doesn't land on a block edge still
        comes out with every factor x factor block a single flat colour:
        the body draws at a reduced resolution, then nearest-neighbour
        upscales, instead of drawing smooth vector edges at full size."""
        cv = Canvas(80, 80, '#000')
        factor = 8
        with cv.pixelated(factor) as sub:
            sub.fill('#000')
            sub.rect(0, 0, 37, 80, '#fff')   # a boundary mid-block, not on an 8px line
        for by in range(80 // factor):
            for bx in range(80 // factor):
                colors = {px(cv, bx * factor + dx, by * factor + dy)
                          for dx in range(factor) for dy in range(factor)}
                self.assertEqual(len(colors), 1, f'block ({bx},{by}) is not flat: {colors}')

    def test_body_draws_in_the_outer_coordinate_space(self):
        cv = Canvas(80, 80, '#000')
        with cv.pixelated(8) as sub:
            self.assertEqual((sub.width, sub.height), (80, 80))

    def test_a_film_not_using_it_is_unchanged(self):
        """Pinned against a hash taken before `pixelated` existed, not just
        against a second canvas drawn with the identical calls -- that would
        pass even if both outputs had drifted together."""
        cv = Canvas(100, 100, '#000')
        cv.rect(10, 10, 40, 40, '#fff')
        cv.outline(5, 5, 90, 90, '#0f0', width=3)
        cv.line(0, 50, 100, 50, '#f00', width=2)
        digest = hashlib.sha256(cv.bgra()).hexdigest()
        self.assertEqual(digest, 'afa7d22efb28ca5e390dd0c7f0ebe08cc51237ef7fcaafdccb061d924fc78412')


class Halftone(unittest.TestCase):
    def test_fills_with_dots_at_the_pitch(self):
        cv = Canvas(100, 100, '#000')
        pitch, radius = 20, 7
        cv.ctx.set_source(halftone_pattern(pitch, radius, color='#fff'))
        cv.ctx.paint()
        # Dot centres sit at (pitch/2, pitch/2) plus whole multiples of pitch.
        for k in (0, 1, 2):
            x = y = pitch // 2 + k * pitch
            self.assertEqual(px(cv, x, y), (255, 255, 255, 255))
        # Exactly between two dot centres (a tile corner) is background.
        self.assertEqual(px(cv, 0, 0), (0, 0, 0, 255))
        self.assertEqual(px(cv, pitch, 0), (0, 0, 0, 255))


if __name__ == '__main__':
    unittest.main()
