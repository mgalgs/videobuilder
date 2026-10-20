"""vb.TerminalLog: lines wrap to the box, the log scrolls once full, every
frame is a function of t alone, each kind keeps its font and colour, typed
lines keep the typewriter styles' cadence, and the keys land on the frames
their letters show (on the fixture pack)."""
import math
import unittest

import videobuilder as vb
from videobuilder import text
from videobuilder.type.typewriter import schedule

FPS = 30
RED, BLUE, GREEN = '#ff0000', '#0000ff', '#00ff00'
KINDS = {'think': vb.terminal.Kind(vb.Font('monospace', 20, style='italic'), RED),
         'cmd': vb.terminal.Kind(vb.Font('monospace', 20, weight=700), BLUE, prefix='$ ', prefix_color=GREEN,
                                 typed=True),
         'out': vb.terminal.Kind(vb.Font('monospace', 30), GREEN)}
BOX = (10, 10, 300, 200)


def colours(cv, box=BOX):
    """{(r, g, b): count} of the pure red, green and blue pixels in `box`."""
    cv.surface.flush()
    data, stride = bytes(cv.surface.get_data()), cv.surface.get_stride()
    x0, y0, w, h = box
    out = {}
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            b, g, r = data[y * stride + 4 * x: y * stride + 4 * x + 3]
            if (r, g, b) in ((255, 0, 0), (0, 0, 255), (0, 255, 0)):
                out[r, g, b] = out.get((r, g, b), 0) + 1
    return out


def frame(log, t):
    cv = vb.Canvas(320, 220, '#000000')
    log.draw(cv, t, BOX)
    return cv


class Layout(unittest.TestCase):
    def test_a_long_line_wraps_to_the_box_past_its_prefix(self):
        line = 'git commit -m "' + 'a word ' * 30 + '"'
        log = vb.TerminalLog([(0, 'cmd', line)], KINDS)
        rows, _ = log._layout(300, 200)
        self.assertGreater(len(rows), 3)
        prefix = text.measure('$ ', KINDS['cmd'].font)
        for row in rows:
            self.assertEqual(row.x, prefix)
            self.assertLessEqual(text.measure(row.text, KINDS['cmd'].font), 300 - prefix + 0.5)
            self.assertEqual(line[row.first:row.first + len(row.text)], row.text)

    def test_each_kind_keeps_its_line_height(self):
        log = vb.TerminalLog([(0, 'think', 'a'), (1, 'out', 'b')], KINDS)
        rows, _ = log._layout(300, 200)
        self.assertEqual([r.h for r in rows], [text.line_height(KINDS['think'].font),
                                               text.line_height(KINDS['out'].font)])

    def test_an_unknown_kind_or_overlapping_typing_is_refused(self):
        with self.assertRaisesRegex(ValueError, "no kind 'shout'"):
            vb.TerminalLog([(0, 'shout', 'hi')], KINDS)
        with self.assertRaisesRegex(ValueError, 'still typing'):
            vb.TerminalLog([(0, 'cmd', 'a long command typed slowly'), (0.2, 'out', 'ok')], KINDS)

    def test_paced_events_start_after_the_last_has_typed(self):
        events = vb.terminal.paced([('cmd', 'ls -la'), ('out', 'total 0', 0.1), ('cmd', 'pwd')], KINDS, start=1.0)
        log = vb.TerminalLog(events, KINDS)
        self.assertEqual(events[0][0], 1.0)
        self.assertAlmostEqual(events[1][0], log.finish(0) + 0.1)
        self.assertAlmostEqual(events[2][0], log.finish(1) + 0.4)


class Drawing(unittest.TestCase):
    def setUp(self):
        self.events = vb.terminal.paced([('think', 'First, look around.')] +
                                        [('cmd', f'echo {i}') if i % 2 else ('out', f'line {i}') for i in range(12)],
                                        KINDS, start=0.2, gap=0.3)
        self.log = vb.TerminalLog(self.events, KINDS)

    def test_each_kind_draws_in_its_colour(self):
        seen = colours(frame(self.log, self.events[3][0] + 0.05))
        self.assertGreater(seen.get((255, 0, 0), 0), 20)    # the thinking
        self.assertGreater(seen.get((0, 0, 255), 0), 20)    # a command
        self.assertGreater(seen.get((0, 255, 0), 0), 20)    # its prompt and an output line

    def test_nothing_before_the_first_line(self):
        self.assertEqual(colours(frame(self.log, 0.1)), {})

    def test_the_first_line_leaves_the_top_once_enough_lines_arrive(self):
        rows, steps = self.log._layout(300, 200)
        self.assertTrue(steps)
        early = frame(self.log, self.events[1][0])
        self.assertGreater(colours(early).get((255, 0, 0), 0), 0)
        end = self.log.end + 1
        self.assertGreater(self.log.offset(end, 300, 200), rows[0].y + rows[0].h)
        self.assertNotIn((255, 0, 0), colours(frame(self.log, end)))   # only the thinking was red

    def test_a_scroll_eases_over_a_few_frames(self):
        when, d = self.log._layout(300, 200)[1][-1]
        before = self.log.offset(when, 300, 200)
        mid = self.log.offset(when + self.log.scroll / 3, 300, 200)
        after = self.log.offset(when + self.log.scroll, 300, 200)
        self.assertAlmostEqual(after - before, d)
        self.assertLess(before, mid)
        self.assertLess(mid, after)

    def test_a_frame_is_the_same_drawn_twice_or_out_of_order(self):
        times = [n / FPS for n in range(0, math.ceil(self.log.end * FPS) + 10, 7)]
        in_order = [frame(self.log, t).bgra() for t in times]
        fresh = vb.TerminalLog(self.events, KINDS)
        shuffled = {t: frame(fresh, t).bgra() for t in reversed(times)}
        self.assertEqual(in_order, [shuffled[t] for t in times])
        self.assertEqual(frame(fresh, times[5]).bgra(), in_order[5])

    def test_the_cursor_blinks_once_typed(self):
        log = vb.TerminalLog([(0, 'cmd', 'ls')], {**KINDS, 'cmd': vb.terminal.Kind(KINDS['cmd'].font, BLUE,
                                                                                  typed=True, prefix_color=GREEN)})
        lit = [colours(frame(log, log.finish(0) + 0.4 + k * 0.1)).get((0, 255, 0), 0) > 0 for k in range(10)]
        self.assertIn(True, lit)
        self.assertIn(False, lit)


class Typing(unittest.TestCase):
    def test_the_cadence_is_the_typewriter_styles(self):
        line = 'pytest -q, then git push'
        log = vb.TerminalLog([(0.4, 'out', 'x'), (1.0, 'cmd', line)], KINDS)
        keys, span = schedule(line, line, KINDS['cmd'].per_char)
        self.assertEqual(log.keys[1], [1.0 + k for k in keys])
        self.assertAlmostEqual(log.finish(1), 1.0 + span)
        gaps = [b - a for a, b in zip(log.keys[1], log.keys[1][1:])]
        self.assertGreater(max(gaps) / min(gaps), 1.5)    # uneven, as a hand types

    def test_paced_events_keep_their_cadence_behind_a_hand_written_one(self):
        for j in range(20):
            paced = vb.terminal.paced([('cmd', f'command number {j} with args'), ('out', 'ok', 0.05)],
                                      KINDS, start=1.0)
            log = vb.TerminalLog([(0.2, 'out', 'welcome')] + paced, KINDS)
            self.assertAlmostEqual(log.finish(1) + 0.05, paced[1][0])

    def test_letters_appear_one_keystroke_at_a_time(self):
        log = vb.TerminalLog([(0, 'cmd', 'make')], KINDS)
        self.assertEqual([log.typed(0, k + 1e-6) for k in log.keys[0]], [1, 2, 3, 4])
        self.assertEqual(log.typed(0, log.keys[0][1] - 1e-3), 1)


class Sounds(unittest.TestCase):
    def test_a_key_on_the_frame_each_letter_shows_and_a_tick_per_output_line(self):
        events = vb.terminal.paced([('cmd', 'git status'), ('out', 'clean'), ('think', 'Good.')], KINDS, start=0.5)
        log = vb.TerminalLog(events, KINDS)
        sounds = log.sounds(at=12, fps=FPS)
        keys, ticks = sounds[:len('git status')], sounds[len('git status'):]
        self.assertEqual(len(ticks), 2)
        for s, k in zip(keys, log.keys[0]):
            n = s.mark - 12
            self.assertGreater(log.typed(0, n / FPS), log.typed(0, (n - 1) / FPS))   # the letter's first frame
            self.assertLessEqual(k, n / FPS + 1e-9)
        self.assertEqual([s.mark for s in ticks], [12 + math.ceil(events[1][0] * FPS - 1e-9),
                                                   12 + math.ceil(events[2][0] * FPS - 1e-9)])
        self.assertEqual({s.align for s in sounds}, {'onset'})

    def test_the_terminal_styles_key_sound(self):
        log = vb.TerminalLog([(0, 'cmd', 'ls')], KINDS)
        from videobuilder.type import _pick, typewriter
        ids, roles, gain = typewriter.TERMINAL.sound['key']
        want = _pick(vb.sfx.bank(), ids, roles)
        self.assertEqual({(s.effect, s.gain_db) for s in log.sounds()}, {(want, gain)})

    def test_a_quiet_kind_makes_no_sound(self):
        quiet = {**KINDS, 'cmd': vb.terminal.Kind(KINDS['cmd'].font, BLUE, typed=True, sound=False)}
        self.assertEqual(vb.TerminalLog([(0, 'cmd', 'ls')], quiet).sounds(), ())


if __name__ == '__main__':
    unittest.main()
