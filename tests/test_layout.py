import unittest

from videobuilder import FORMATS, Canvas
from videobuilder.layout import Box, fr, per_format


def boxes(bs):
    return [tuple(round(v, 6) for v in b) for b in bs]


class BoxBasics(unittest.TestCase):
    def test_of_and_unpack(self):
        b = Box.of(Canvas(200, 100))
        self.assertEqual(tuple(b), (0, 0, 200, 100))
        self.assertEqual((b.right, b.bottom, b.cx, b.cy, b.aspect), (200, 100, 100, 50, 2))

    def test_pad_shorthand(self):
        b = Box(0, 0, 100, 100)
        self.assertEqual(tuple(b.pad(10)), (10, 10, 80, 80))
        self.assertEqual(tuple(b.pad(10, 20)), (20, 10, 60, 80))
        self.assertEqual(tuple(b.pad(1, 2, 3)), (2, 1, 96, 96))
        self.assertEqual(tuple(b.pad(1, 2, 3, 4)), (4, 1, 94, 96))
        self.assertEqual(tuple(b.pad((1, 2, 3, 4))), (4, 1, 94, 96))
        self.assertEqual(tuple(b.pad(80)), (80, 80, 0, 0))  # never negative
        with self.assertRaises(ValueError):
            b.pad(1, 2, 3, 4, 5)

    def test_center_and_anchor(self):
        b = Box(100, 100, 400, 200)
        self.assertEqual(tuple(b.center(100, 50)), (250, 175, 100, 50))
        self.assertEqual(tuple(b.anchor(100, 50, 'top-left')), (100, 100, 100, 50))
        self.assertEqual(tuple(b.anchor(100, 50, 'bottom-right')), (400, 250, 100, 50))
        self.assertEqual(tuple(b.anchor(100, 50, 'bottom', margin=10)), (250, 240, 100, 50))
        self.assertEqual(tuple(b.anchor(100, 50, 'right', margin=(0, 20))), (380, 175, 100, 50))
        with self.assertRaises(KeyError):
            b.anchor(1, 1, 'middle')

    def test_moved_and_scaled(self):
        b = Box(0, 0, 100, 50)
        self.assertEqual(tuple(b.moved(5, -5)), (5, -5, 100, 50))
        self.assertEqual(tuple(b.scaled(2)), (-50, -25, 200, 100))
        self.assertEqual(tuple(b.scaled(0.5, 'top-left')), (0, 0, 50, 25))


class Tracks(unittest.TestCase):
    def test_row_fixed_and_fr(self):
        b = Box(0, 0, 1020, 100)
        self.assertEqual(boxes(b.row(100, fr, 2 * fr, gap=10)),
                         [(0, 0, 100, 100), (110, 0, 300, 100), (420, 0, 600, 100)])

    def test_column(self):
        b = Box(10, 20, 100, 300)
        self.assertEqual(boxes(b.column(fr, fr, fr)), [(10, 20, 100, 100), (10, 120, 100, 100), (10, 220, 100, 100)])

    def test_justify(self):
        b = Box(0, 0, 1000, 10)
        self.assertEqual([x for x, *_ in b.row(100, 100, justify='start')], [0, 100])
        self.assertEqual([x for x, *_ in b.row(100, 100, justify='center')], [400, 500])
        self.assertEqual([x for x, *_ in b.row(100, 100, justify='end')], [800, 900])
        self.assertEqual([x for x, *_ in b.row(100, 100, 100, justify='space-between')], [0, 450, 900])
        with self.assertRaises(ValueError):
            b.row(100, justify='around')

    def test_fr_takes_slack_so_justify_is_moot(self):
        b = Box(0, 0, 1000, 10)
        self.assertEqual(boxes(b.row(100, fr, justify='center')), [(0, 0, 100, 10), (100, 0, 900, 10)])

    def test_overfull_fr_collapses_to_zero(self):
        self.assertEqual(Box(0, 0, 100, 10).row(80, 40, fr)[2].w, 0)

    def test_grid(self):
        cells = Box(0, 0, 210, 110).grid(3, 2, gap=10)
        self.assertEqual(len(cells), 6)
        self.assertEqual(boxes(cells[:2] + cells[3:4]), [(0, 0, 63.333333, 50), (73.333333, 0, 63.333333, 50),
                                                         (0, 60, 63.333333, 50)])


class Fit(unittest.TestCase):
    def setUp(self):
        self.b = Box(0, 0, 400, 200)

    def test_contain(self):
        self.assertEqual(tuple(self.b.contain(100, 100)), (100, 0, 200, 200))
        self.assertEqual(tuple(self.b.contain(100, 100, at='left')), (0, 0, 200, 200))

    def test_cover(self):
        self.assertEqual(tuple(self.b.cover(100, 100)), (0, -100, 400, 400))
        self.assertEqual(tuple(self.b.cover(100, 100, at='top')), (0, 0, 400, 400))

    def test_fill_none_scale_down(self):
        self.assertEqual(self.b.fit(1, 1, 'fill'), self.b)
        self.assertEqual(tuple(self.b.fit(50, 20, 'none')), (175, 90, 50, 20))
        self.assertEqual(tuple(self.b.fit(50, 20, 'scale-down')), (175, 90, 50, 20))  # never enlarged
        self.assertEqual(tuple(self.b.fit(800, 800, 'scale-down')), (100, 0, 200, 200))


class PerFormat(unittest.TestCase):
    TABLE = {'*': dict(cols=1, size=90), '16x9': dict(cols=2), '1x1': 'square'}

    def test_merge_and_fallback(self):
        self.assertEqual(per_format(self.TABLE, '16x9'), {'cols': 2, 'size': 90})
        self.assertEqual(per_format(self.TABLE, '9x16'), {'cols': 1, 'size': 90})
        self.assertEqual(per_format(self.TABLE, '1x1'), 'square')  # non-dicts are returned as they are

    def test_accepts_format_and_canvas(self):
        self.assertEqual(per_format(self.TABLE, FORMATS['16x9'])['cols'], 2)
        cv = Canvas(1920, 1080, format=FORMATS['16x9'])
        self.assertEqual(per_format(self.TABLE, cv)['cols'], 2)

    def test_missing_without_fallback(self):
        with self.assertRaises(KeyError):
            per_format({'16x9': 1}, '9x16')


if __name__ == '__main__':
    unittest.main()
