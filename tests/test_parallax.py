"""vb.parallax: layers slide at their depth, wrap to one tile, and repeat across the frame."""
import unittest

import videobuilder as vb
from videobuilder import parallax


class Parallax(unittest.TestCase):
    def test_a_layer_moves_its_depth_per_px_of_pan_wrapped_to_one_tile(self):
        far, near = parallax.Layer(0.25, 200, None), parallax.Layer(1.5, 200, None)
        self.assertAlmostEqual(parallax.offset(far, 0), 0)
        self.assertAlmostEqual(parallax.offset(far, 100), -25)
        self.assertAlmostEqual(parallax.offset(near, 100), -150)
        self.assertAlmostEqual(parallax.offset(near, 200), -100)        # 300 px, wrapped
        self.assertAlmostEqual(parallax.offset(far, 800), parallax.offset(far, 0))   # a whole tile: no seam

    def test_tiles_cover_the_frame_back_to_front(self):
        calls = []
        layers = (parallax.Layer(0.5, 300, lambda cv, x: calls.append(('far', x))),
                  parallax.Layer(1.0, 250, lambda cv, x: calls.append(('near', x))))
        parallax.draw(vb.Canvas(640, 100), layers, 100)
        self.assertEqual(calls, [('far', -50), ('far', 250), ('far', 550), ('near', -100), ('near', 150),
                                 ('near', 400)])

    def test_a_ridge_spans_its_tile_and_its_ends_meet(self):
        pts = parallax.ridge(360, 80, seed=4)
        self.assertEqual(pts[0][0], 0)
        self.assertEqual(pts[-1][0], 360)
        self.assertAlmostEqual(pts[0][1], pts[-1][1])
        self.assertAlmostEqual(min(y for _, y in pts), 0)
        self.assertAlmostEqual(max(y for _, y in pts), 80)
        self.assertEqual(pts, parallax.ridge(360, 80, seed=4))
