import hashlib
import unittest

import videobuilder as vb
from videobuilder import Canvas, halftone_pattern, paper_grain, rgba
from videobuilder.canvas import _grain_surface, _shape_shadow_mask


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


class ShapeShadow(unittest.TestCase):
    TRIANGLE = [(10, 10), (90, 10), (10, 90)]

    def test_follows_the_shape_not_its_box(self):
        cv = Canvas(100, 100, '#fff')
        cv.shape_shadow(self.TRIANGLE, color=(0, 0, 0, 1.0))
        self.assertEqual(px(cv, 25, 25), (0, 0, 0, 255))        # inside the triangle
        self.assertEqual(px(cv, 80, 80), (255, 255, 255, 255))  # inside its box, outside the shape

    def test_offset_and_blur(self):
        cv = Canvas(100, 100, '#fff')
        cv.shape_shadow(self.TRIANGLE, dx=5, dy=5, blur=10, color=(0, 0, 0, 1.0))
        self.assertLess(px(cv, 30, 30)[0], 40)                   # deep inside: near full
        edge = px(cv, 10, 40)[0]                                 # the shape's own edge, now 5px inside
        self.assertTrue(40 < edge < 255, edge)                   # soft, not a hard step
        self.assertEqual(px(cv, 95, 95), (255, 255, 255, 255))

    def test_moves_with_the_transform_and_reuses_its_mask(self):
        _shape_shadow_mask.cache_clear()
        cv = Canvas(200, 100, '#fff')
        cv.ctx.translate(100, 0)
        cv.shape_shadow(self.TRIANGLE, blur=4, color=(0, 0, 0, 1.0))
        cv.shape_shadow(self.TRIANGLE, blur=4, color=(0, 0, 0, 1.0))
        self.assertEqual(px(cv, 125, 25), (0, 0, 0, 255))
        self.assertEqual(px(cv, 25, 25), (255, 255, 255, 255))
        info = _shape_shadow_mask.cache_info()
        self.assertEqual((info.misses, info.hits), (1, 1))

    def test_box_shadow_is_unchanged(self):
        """`shadow` now shares its A8 conversion with `shape_shadow`; pinned against
        a hash taken before that change."""
        cv = Canvas(120, 100, '#fff')
        cv.shadow(20, 20, 60, 40, radius=10, dx=4, dy=8, blur=12, spread=2, color=(0, 0, 0, 0.6))
        cv.rect(20, 20, 60, 40, '#36c', radius=10)
        digest = hashlib.sha256(cv.bgra()).hexdigest()
        self.assertEqual(digest, 'c3761fc627c9f63b9be503d34ee1161e17f4ce738d4f6c54bdbffc6787e60bc6')


class PaperGrain(unittest.TestCase):
    def grey(self, seed, size=(64, 48)):
        surf = _grain_surface(*size, seed)
        surf.flush()
        data = bytes(surf.get_data())
        return [data[i] for i in range(0, len(data), 4)]   # blue channel; the texture is grey

    def test_deterministic_per_seed_and_cached(self):
        self.assertEqual(self.grey(1), self.grey(1))
        self.assertNotEqual(self.grey(1), self.grey(2))
        self.assertIs(_grain_surface(64, 48, 1), _grain_surface(64, 48, 1))

    def test_centred_on_mid_grey_with_texture(self):
        g = self.grey(3, (256, 256))
        mean = sum(g) / len(g)
        self.assertLess(abs(mean - 128), 6)
        self.assertGreater(max(g) - min(g), 60)

    def test_soft_light_keeps_the_colour_on_average(self):
        import cairo
        cv = Canvas(64, 48, '#808080')
        cv.ctx.set_source(paper_grain(64, 48, seed=4))
        cv.ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
        cv.ctx.paint()
        data = cv.bgra()
        reds = [data[i + 2] for i in range(0, len(data), 4)]
        self.assertLess(abs(sum(reds) / len(reds) - 128), 8)
        self.assertGreater(len(set(reds)), 10)


if __name__ == '__main__':
    unittest.main()
