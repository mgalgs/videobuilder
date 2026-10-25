import unittest
from unittest import mock

import videobuilder as vb
from videobuilder.capabilities.typography import text_diff_morph as tdm

FONT = vb.Font('monospace', 24)


def by_kind(ops, kind):
    return [o for o in ops if o[0] == kind]


class TestDiffOps(unittest.TestCase):
    """Ported from git-video's worddiff tests: the diff is plain data, no
    pane or canvas involved."""

    def test_modified_line(self):
        ops = tdm.ops(['    return x + 1'], ['    return x * 2'])
        self.assertEqual(by_kind(ops, 'equal'), [['equal', 0, 4, 0, 4, 'return'], ['equal', 0, 11, 0, 11, 'x']])
        self.assertEqual([o[5] for o in by_kind(ops, 'delete')], ['+', '1'])
        self.assertEqual([o[5] for o in by_kind(ops, 'insert')], ['*', '2'])
        self.assertEqual(by_kind(ops, 'delete')[0][1:5], [0, 13, -1, -1])
        self.assertEqual(by_kind(ops, 'insert')[0][1:5], [-1, -1, 0, 13])

    def test_kept_words_move(self):
        ops = tdm.ops(['for a in argv:'], ['i = 0', 'while a in argv:'])
        (argv,) = [o for o in by_kind(ops, 'equal') if o[5] == 'argv']
        self.assertEqual(argv[1:5], [0, 9, 1, 11])

    def test_pure_delete(self):
        ops = tdm.ops(['def f():', '    pass'], [])
        self.assertEqual({o[0] for o in ops}, {'delete'})
        self.assertEqual([o[5] for o in ops], ['def', 'f', '(', ')', ':', 'pass'])

    def test_pure_add(self):
        ops = tdm.ops([], ['x = 1'])
        self.assertEqual({o[0] for o in ops}, {'insert'})

    def test_whitespace_only_change_has_no_ops_but_equals(self):
        ops = tdm.ops(['a  =  1'], ['a = 1'])
        self.assertEqual({o[0] for o in ops}, {'equal'})

    def test_words_match_only_within_an_edited_line(self):
        # line 0 is edited (most words kept); line 1 has nothing to do with the old
        # line 1 but shares `=` and `(`: those must not fly between the two
        ops = tdm.ops(['x = foo(a, b)', 'y = 2'], ['x = bar(a, b)', 'total = compute(q)'])
        self.assertTrue(all(o[1] == o[3] == 0 for o in by_kind(ops, 'equal')))
        self.assertEqual([o[5] for o in by_kind(ops, 'insert') if o[3] == 1], ['total', '=', 'compute', '(', 'q', ')'])
        self.assertEqual([o[5] for o in by_kind(ops, 'delete') if o[1] == 1], ['y', '=', '2'])
        self.assertEqual(tdm.pair_rows(['x = foo(a, b)', 'y = 2'], ['x = bar(a, b)', 'total = compute(q)']),
                         [(0, 0)])

    def test_too_many_tokens(self):
        self.assertIsNone(tdm.ops(['x ' * tdm.MAX_TOKENS], ['y']))

    def test_line_edits_reproduce_the_new_line(self):
        old, new = '    return x + 1', '    return x * 2'
        edits = tdm.line_edits(old, new)
        out = old
        for col, delete, insert in reversed(edits):
            out = out[:col] + insert + out[col + delete:]
        self.assertEqual(out, new)


def words_drawn(fn):
    """[text, ...] of every non-empty vbtext.draw call `fn()` makes, in call order."""
    calls = []
    real = tdm.vbtext.draw

    def record(cv, lines, font, x, y, *a, **kw):
        if lines and lines[0].strip():
            calls.append(lines[0])
        return real(cv, lines, font, x, y, *a, **kw)

    with mock.patch.object(tdm.vbtext, 'draw', record):
        fn()
    return calls


class TestDrawSegment(unittest.TestCase):
    """draw_segment needs no pane: a canvas, a font and two lists of lines."""

    def draw(self, old, new, p):
        cv = vb.Canvas(900, 300, '#000')
        box = tdm.draw_segment(cv, 20, 20, FONT, old, new, p, '#ffffff')
        return cv, box

    def test_exactly_old_text_at_zero(self):
        old, new = ['x = foo(a, b)'], ['x = bar(a, b)']
        drawn = words_drawn(lambda: self.draw(old, new, 0.0))
        want = [t for _, _, t in tdm.tokens(old) if t.strip()]
        self.assertEqual(sorted(drawn), sorted(want))

    def test_exactly_new_text_at_one(self):
        old, new = ['x = foo(a, b)'], ['x = bar(a, b)']
        drawn = words_drawn(lambda: self.draw(old, new, 1.0))
        want = [t for _, _, t in tdm.tokens(new) if t.strip()]
        self.assertEqual(sorted(drawn), sorted(want))

    def test_kept_tokens_drawn_once_mid_morph(self):
        old, new = ['x = foo(a, b)'], ['x = bar(a, b)']
        for p in (0.0, 0.3, 0.5, 0.7, 1.0):
            drawn = words_drawn(lambda p=p: self.draw(old, new, p))
            self.assertEqual(drawn.count('a'), 1, p)
            self.assertEqual(drawn.count('b'), 1, p)

    def test_new_lines_appear_only_once_the_morph_has_mostly_run(self):
        old, new = ['x = foo(a, b)'], ['x = bar(a, b)', 'total = compute(q)']
        self.assertNotIn('total', words_drawn(lambda: self.draw(old, new, 0.0)))
        self.assertIn('total', words_drawn(lambda: self.draw(old, new, 1.0)))

    def test_box_covers_the_wider_of_old_and_new(self):
        old, new = ['short'], ['a much longer replacement line']
        _, box = self.draw(old, new, 1.0)
        self.assertGreater(box.w, tdm.vbtext.measure('short', FONT))

    def plain(self, lines, font):
        cv = vb.Canvas(900, 300, '#000')
        for row, line in enumerate(lines):
            tdm.vbtext.draw(cv, [line], font, 20, 20 + row * tdm.vbtext.line_height(font), '#ffffff')
        return bytes(cv.surface.get_data())

    def test_p0_is_pixel_for_pixel_the_plain_old_text(self):
        # no strike-through yet: a film can cut from the plain line to the morph without a pop
        old, new = ['x = foo(a, b)'], ['x = bar(a, b)']
        cv, _ = self.draw(old, new, 0.0)
        self.assertEqual(bytes(cv.surface.get_data()), self.plain(old, FONT))

    def test_words_sit_where_a_plain_draw_puts_them_in_a_proportional_font(self):
        sans = vb.Font('sans', 24)
        old = ['Water lily ToWards AVAil fWy offers ttT yay WAV TeVa attack every Tuesday']
        cv = vb.Canvas(900, 300, '#000')
        tdm.draw_segment(cv, 20, 20, sans, old, ['different'], 0.0, '#ffffff')
        got, want = bytes(cv.surface.get_data()), self.plain(old, sans)
        # a few antialiased edge pixels where words meet; summed per-letter widths
        # (kerning lost) put the line's tail several px off and differ by thousands
        self.assertLess(sum(a != b for a, b in zip(got, want)), 100)

    def test_too_many_tokens_crossfades_instead_of_raising(self):
        old = [' '.join('abcdefghijklmnopqrstuvwxyz')] * 80
        new = [line.upper() for line in old]
        self.assertIsNone(tdm.ops(old, new))
        for p in (0.0, 0.5, 1.0):
            drawn = words_drawn(lambda p=p: self.draw(old, new, p))
            self.assertTrue(drawn, p)

    def test_works_with_no_pane_involved(self):
        # just videobuilder + this module: no editor, no buffer, no git
        cv = vb.Canvas(400, 100, '#000')
        for p in (0.0, 0.25, 0.5, 0.75, 1.0):
            box = tdm.draw_segment(cv, 10, 10, FONT, ['old line'], ['new line'], p, '#eeeeee')
            self.assertGreater(box.w, 0)
            self.assertGreater(box.h, 0)


if __name__ == '__main__':
    unittest.main()
