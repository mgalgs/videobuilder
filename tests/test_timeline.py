import unittest

from videobuilder.timeline import Grid, Segment, Shot, Timeline, round_half_up, sequence


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



class Structure(unittest.TestCase):
    """Groups (a segment holding children) and overlaps (a segment entering over the last)."""

    def setUp(self):
        self.grid = Grid(fps=30, bpm=120)  # 15 frames a beat
        self.cuts = Segment('cuts', 2, 4, children=sequence(2, [('c1', 1), ('c2', 0.5, dict(k=2)), ('c3', 0.5)]))
        self.tl = Timeline(self.grid, [
            Segment('intro', 0, 2), self.cuts, Segment('wall', 4, 6), Segment('close', 6, 8, overlap=1),
        ], end=8)

    def test_sequence(self):
        self.assertEqual([(s.name, s.at, s.until, s.data) for s in self.cuts.children],
                         [('c1', 2, 3, {}), ('c2', 3, 3.5, {'k': 2}), ('c3', 3.5, 4, {})])

    def test_child_sees_its_frame_and_its_groups(self):
        (shot,) = self.tl.live(50)  # 5 frames into c2, 20 into the group
        self.assertIsInstance(shot, Shot)
        self.assertEqual((shot.name, shot.f, shot.length, shot.data), ('c2', 5, 8, {'k': 2}))
        self.assertIs(shot.group, self.cuts)
        self.assertEqual(shot.group_f, 20)
        self.assertIsNone(shot.exit)
        self.assertEqual(self.tl.at(50), (self.cuts.children[1], 5))
        (top,) = self.tl.live(10)
        self.assertEqual((top.name, top.group, top.group_f), ('intro', None, None))

    def test_overlap_draws_both_back_to_front(self):
        # close starts at beat 6 (frame 90); the wall keeps drawing under it for one beat
        wall, close = self.tl.live(90)
        self.assertEqual((wall.name, wall.f, wall.length, wall.exit), ('wall', 30, 30, 0))
        self.assertEqual((close.name, close.f, close.exit), ('close', 0, None))
        self.assertEqual([(s.name, s.exit) for s in self.tl.live(104)], [('wall', 14), ('close', None)])
        self.assertEqual([s.name for s in self.tl.live(105)], ['close'])  # overlap over
        self.assertEqual([s.name for s in self.tl.live(89)], ['wall'])
        self.assertEqual(self.tl.at(95)[0].name, 'close')  # the frontmost
        self.assertEqual(self.tl.label(95), 'wall > close')
        self.assertEqual(self.tl.label(50), 'cuts / c2')

    def test_overlapping_a_group_continues_its_last_child(self):
        tl = Timeline(self.grid, [self.cuts, Segment('next', 4, 6, overlap=0.5)], end=6)
        last, nxt = tl.live(62)
        self.assertEqual((last.name, last.f, last.group_f, last.exit), ('c3', 9, 32, 2))
        self.assertEqual(nxt.name, 'next')

    def test_cut_frames(self):
        # every start at any level, deduplicated; the overlapping close is not a cut
        self.assertEqual(self.tl.cut_frames(), [0, 30, 45, 53, 60])
        self.assertEqual(self.tl.frames, 120)
        self.assertEqual(self.tl.span('close'), (90, 120))
        self.assertEqual(self.tl.start('c3'), 53)  # 52.5 rounds up

    def test_walk_and_leaves(self):
        self.assertEqual([(s.name, [p.name for p in ps]) for s, ps in self.tl.walk()][:3],
                         [('intro', []), ('cuts', []), ('c1', ['cuts'])])
        self.assertEqual([s.name for s in self.tl.leaves()], ['intro', 'c1', 'c2', 'c3', 'wall', 'close'])
        with self.assertRaises(KeyError):
            self.tl.find('nope')

    def test_bad_structure_rejected(self):
        g = self.grid
        with self.assertRaises(ValueError):  # children leave a gap
            Timeline(g, [Segment('a', 0, 4, children=[Segment('x', 0, 1), Segment('y', 2, 4)])], end=4)
        with self.assertRaises(ValueError):  # children don't start with the group
            Timeline(g, [Segment('a', 0, 4, children=[Segment('x', 1, 4)])], end=4)
        with self.assertRaises(ValueError):  # nothing to overlap
            Timeline(g, [Segment('a', 0, 4, overlap=1)], end=4)
        with self.assertRaises(ValueError):  # overlap longer than the segment
            Timeline(g, [Segment('a', 0, 2), Segment('b', 2, 3, overlap=2)], end=3)
        with self.assertRaises(ValueError):  # a child off the half-beat grid
            Timeline(g, [Segment('a', 0, 2, children=sequence(0, [('x', 0.25), ('y', 1.75)]))], end=2)

    def test_flat_timeline_unchanged(self):
        tl = Timeline(self.grid, [Segment('a', 0, 2), Segment('b', 2, 4)], end=4)
        self.assertEqual(tl.at(30), (tl.segments[1], 0))
        self.assertEqual([(s.name, s.f, s.parents) for s in tl.live(31)], [('b', 1, ())])
        with self.assertRaises(IndexError):
            tl.live(60)


if __name__ == '__main__':
    unittest.main()
