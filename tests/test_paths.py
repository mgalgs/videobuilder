import math
import unittest

from videobuilder import paths


def square(x, y, s):
    """A closed square, clockwise from the top-left, each edge split in two
    (8 points) so resampling has more than just the 4 corners to work with."""
    return [
        (x, y), (x + s / 2, y),
        (x + s, y), (x + s, y + s / 2),
        (x + s, y + s), (x + s / 2, y + s),
        (x, y + s), (x, y + s / 2),
    ]


class Length(unittest.TestCase):
    def test_open_and_closed(self):
        self.assertAlmostEqual(paths.length([(0, 0), (3, 4)]), 5.0)
        self.assertAlmostEqual(paths.length([(0, 0), (10, 0), (10, 10)]), 20.0)
        self.assertAlmostEqual(paths.length([(0, 0), (10, 0), (10, 10)], closed=True),
                               20.0 + math.hypot(10, 10))


class Reveal(unittest.TestCase):
    LINE = [(0, 0), (10, 0), (10, 10)]  # total length 20

    def test_zero_is_empty(self):
        self.assertEqual(paths.reveal(self.LINE, 0), [])
        self.assertEqual(paths.reveal(self.LINE, -1), [])

    def test_half_stops_at_half_the_length(self):
        out = paths.reveal(self.LINE, 0.5)
        self.assertAlmostEqual(paths.length(out), 10.0)
        self.assertEqual(out[-1], (10, 0))  # exactly the corner, at half length

    def test_one_is_the_whole_path(self):
        self.assertEqual(paths.reveal(self.LINE, 1), self.LINE)
        self.assertEqual(paths.reveal(self.LINE, 2), self.LINE)  # clamped

    def test_closed_appends_the_start(self):
        tri = [(0, 0), (10, 0), (0, 10)]
        self.assertEqual(paths.reveal(tri, 1, closed=True), tri + [tri[0]])

    def test_quarter_length_is_quarter_of_total(self):
        out = paths.reveal(self.LINE, 0.25)
        self.assertAlmostEqual(paths.length(out), 5.0)


class Resample(unittest.TestCase):
    def test_keeps_open_endpoints(self):
        line = [(0, 0), (4, 0), (10, 0)]
        out = paths.resample(line, 5)
        self.assertEqual(out[0], (0, 0))
        self.assertEqual(out[-1], (10, 0))
        self.assertEqual(len(out), 5)

    def test_even_spacing(self):
        line = [(0, 0), (4, 0), (10, 0)]
        out = paths.resample(line, 6)
        gaps = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(out, out[1:])]
        for g in gaps[1:]:
            self.assertAlmostEqual(g, gaps[0], places=6)

    def test_closed_wraps_from_the_start_point(self):
        sq = square(0, 0, 10)
        out = paths.resample(sq, 8, closed=True)
        self.assertEqual(out[0], sq[0])

    def test_rejects_too_few_points(self):
        with self.assertRaises(ValueError):
            paths.resample([(0, 0), (1, 1)], 1)

    def test_degenerate_path_repeats_the_point(self):
        self.assertEqual(paths.resample([(5, 5), (5, 5)], 3), [(5, 5), (5, 5), (5, 5)])


class Morph(unittest.TestCase):
    def test_t0_and_t1_are_the_inputs(self):
        a = [(0, 0), (10, 0), (10, 10), (0, 10)]  # a closed square, same point count both sides
        b = [(20, 0), (30, 0), (30, 10), (20, 10)]
        self.assertEqual(paths.morph(a, b, 0, closed=True), a)
        self.assertEqual(paths.morph(a, b, 1, closed=True), b)

    def test_open_path_morph_is_a_lerp(self):
        a = [(0, 0), (10, 0)]
        b = [(0, 10), (10, 10)]
        self.assertEqual(paths.morph(a, b, 0.5), [(0, 5), (10, 5)])

    def test_clamped(self):
        a = [(0, 0), (10, 0)]
        b = [(0, 10), (10, 10)]
        self.assertEqual(paths.morph(a, b, -1), a)
        self.assertEqual(paths.morph(a, b, 2), b)

    def test_does_not_twist_different_start_and_winding(self):
        """The same square traced two ways -- clockwise from its top-left, and
        counter-clockwise from its bottom-right -- is the same shape. Without
        start-point/orientation alignment the morph would visibly rotate or
        cross itself even though nothing should move."""
        a = square(0, 0, 10)
        b = list(reversed(a))
        b = b[3:] + b[:3]  # start somewhere else, and wound the other way
        mid = paths.morph(a, b, 0.5, closed=True)
        for (x0, y0), (x1, y1) in zip(mid, a):
            self.assertAlmostEqual(x0, x1, places=6)
            self.assertAlmostEqual(y0, y1, places=6)

    def test_resamples_mismatched_counts(self):
        a = [(0, 0), (10, 0), (10, 10), (0, 10)]
        b = [(0, 0), (5, 0), (10, 0), (10, 10), (0, 10)]
        out = paths.morph(a, b, 0, closed=True, n=5)
        self.assertEqual(len(out), 5)


class Jitter(unittest.TestCase):
    LINE = [(x, 0) for x in range(10)]

    def test_deterministic_per_seed(self):
        self.assertEqual(paths.jitter(self.LINE, 42), paths.jitter(self.LINE, 42))

    def test_different_seeds_differ(self):
        self.assertNotEqual(paths.jitter(self.LINE, 1), paths.jitter(self.LINE, 2))

    def test_amount_zero_is_the_input(self):
        out = paths.jitter(self.LINE, 1, amount=0)
        for (x0, y0), (x1, y1) in zip(out, self.LINE):
            self.assertAlmostEqual(x0, x1)
            self.assertAlmostEqual(y0, y1)


if __name__ == '__main__':
    unittest.main()
