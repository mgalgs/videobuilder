import unittest

from videobuilder.timeline import Grid, Segment, Timeline, round_half_up


class RoundHalfUp(unittest.TestCase):
    def test_halves_go_up_like_js_math_round(self):
        self.assertEqual(round_half_up(487.5), 488)
        self.assertEqual(round_half_up(502.5), 503)
        self.assertEqual(round_half_up(0.5), 1)
        self.assertEqual(round_half_up(1.5), 2)
        self.assertEqual(round_half_up(2.5), 3)
        self.assertEqual(round_half_up(-0.5), 0)  # Math.round(-0.5) is -0
        self.assertEqual(round_half_up(-1.5), -1)

    def test_python_round_would_move_the_cut(self):
        # The trap: banker's rounding sends 502.5 down and 487.5 up.
        self.assertEqual(round(487.5), 488)
        self.assertEqual(round(502.5), 502)
        self.assertNotEqual(round(502.5), round_half_up(502.5))

    def test_non_halves(self):
        self.assertEqual(round_half_up(10.49), 10)
        self.assertEqual(round_half_up(10.51), 11)
        self.assertEqual(round_half_up(7), 7)
        self.assertIsInstance(round_half_up(7.2), int)


class GridFrames(unittest.TestCase):
    def test_half_beat_cuts(self):
        g = Grid(fps=30, bpm=120)  # 15 frames a beat
        self.assertEqual(g.frames_per_beat, 15)
        self.assertEqual(g.b(32.5), 488)  # 487.5
        self.assertEqual(g.b(33.5), 503)  # 502.5: round() would say 502
        self.assertEqual(g.b(4), 60)

    def test_fractional_frames_per_beat(self):
        g = Grid(fps=30, bpm=128)  # 14.0625 frames a beat
        self.assertEqual(g.b(1), 14)
        self.assertEqual(g.b(8), 113)  # 112.5 -> 113
        self.assertEqual(g.b(24), 338)  # 337.5 -> 338
        self.assertEqual(g.seconds(45), 1.5)


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.grid = Grid(fps=30, bpm=120)
        self.tl = Timeline(self.grid, [Segment('b', 2, 4.5), Segment('a', 0, 2), Segment('c', 4.5, 8)], end=8)

    def test_sorted_and_frames(self):
        self.assertEqual([s.name for s in self.tl.segments], ['a', 'b', 'c'])
        self.assertEqual(self.tl.frames, 120)
        self.assertEqual(self.tl.cut_frames(), [0, 30, 68])  # 4.5 beats = 67.5 -> 68

    def test_at(self):
        self.assertEqual(self.tl.at(0)[0].name, 'a')
        self.assertEqual(self.tl.at(29), (self.tl.segments[0], 29))
        self.assertEqual(self.tl.at(30), (self.tl.segments[1], 0))
        self.assertEqual(self.tl.at(67)[0].name, 'b')
        self.assertEqual(self.tl.at(68), (self.tl.segments[2], 0))
        self.assertEqual(self.tl.at(119)[0].name, 'c')
        with self.assertRaises(IndexError):
            self.tl.at(120)

    def test_gaps_rejected(self):
        with self.assertRaises(ValueError):
            Timeline(self.grid, [Segment('a', 0, 2), Segment('b', 3, 4)], end=4)
        with self.assertRaises(ValueError):
            Timeline(self.grid, [Segment('a', 0, 2)], end=4)

    def test_off_grid_start_rejected(self):
        with self.assertRaises(ValueError):
            Timeline(self.grid, [Segment('a', 0, 1.25), Segment('b', 1.25, 2)], end=2)


if __name__ == '__main__':
    unittest.main()
