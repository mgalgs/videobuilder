"""Word-timed captions: VTT (YouTube rolling and plain) and SRT parsing,
shift and slice, Pango-measured line grouping, and the draw call."""
import re
import unittest
from pathlib import Path

import videobuilder as vb
from videobuilder import Box, Canvas, Font, captions, text

FONT_FILE = Path(__file__).resolve().parent.parent / 'examples' / 'assets' / 'Cantarell-VF.otf'
text.register(FONT_FILE)

FIXTURE = Path('/attachments/JOSJE6hQbdE.en.vtt')

# The structure of YouTube's auto-captions: each cue shows the previous line
# again above the new one, whose words carry inline times; a 10 ms cue between
# them holds the finished line alone. A short last line has no time tags.
ROLLING = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:02.990 align:start position:0%
 
It's<00:00:00.240><c> July</c><00:00:00.960><c> again.</c><00:00:02.360><c> A</c><00:00:02.440><c> man</c>

00:00:02.990 --> 00:00:03.000 align:start position:0%
It's July again. A man
 

00:00:03.000 --> 00:00:05.430 align:start position:0%
It's July again. A man
asks<00:00:03.440><c> if</c><00:00:03.760><c> he's</c><00:00:04.280><c> seen</c><00:00:04.680><c> any</c>

00:00:05.430 --> 00:00:05.440 align:start position:0%
asks if he's seen any
 

00:00:05.440 --> 00:00:06.000 align:start position:0%
asks if he's seen any
bodies.

00:00:06.000 --> 00:00:06.010 align:start position:0%
bodies.
 

00:00:06.010 --> 00:00:08.000 align:start position:0%
bodies.
&gt;&gt; No<00:00:06.400><c> I</c><00:00:06.600><c> I</c><00:00:06.900><c> haven't.</c>
"""


class Rolling(unittest.TestCase):
    def test_every_word_once_in_order_with_its_time(self):
        tr = captions.parse(ROLLING)
        self.assertEqual(tr.text, "It's July again. A man asks if he's seen any bodies. No I I haven't.")
        got = [(w.text, w.start) for w in tr]
        self.assertEqual(got[:7], [("It's", 0.0), ('July', 0.24), ('again.', 0.96), ('A', 2.36), ('man', 2.44),
                                   ('asks', 3.0), ('if', 3.44)])
        self.assertEqual(got[-4:], [('No', 6.01), ('I', 6.4), ('I', 6.6), ("haven't.", 6.9)])
        self.assertTrue(all(w.exact for w in tr))
        # a word ends when the next starts; a line's last word at its cue's end
        self.assertEqual((tr[0].end, tr[4].end, tr[-1].end), (0.24, 2.99, 8.0))
        self.assertEqual([w.text for w in tr if w.turn], ['No'])

    def test_untagged_short_line_counts_once(self):
        tr = captions.parse(ROLLING)
        bodies = [w for w in tr if w.text == 'bodies.']
        self.assertEqual(len(bodies), 1)
        self.assertEqual((bodies[0].start, bodies[0].end), (5.44, 6.0))


class Plain(unittest.TestCase):
    def test_plain_vtt_spreads_like_srt(self):
        tr = captions.parse_vtt('WEBVTT\n\nNOTE a comment\n\nintro\n00:01.000 --> 00:03.000 line:90%\n'
                                '<v Ann>Hello <i>there</i></v>\n\n00:00:04.000 --> 00:00:05.000\nBye\n')
        self.assertEqual([w.text for w in tr], ['Hello', 'there', 'Bye'])
        self.assertAlmostEqual(tr[0].start, 1.0)
        self.assertAlmostEqual(tr[1].end, 3.0)
        self.assertAlmostEqual(tr[0].end, 1.0 + 2.0 * 5 / 10)  # by length: 5 of 10 letters
        self.assertFalse(any(w.exact for w in tr))

    def test_srt_interpolates_inside_the_cue(self):
        tr = captions.parse_srt('1\n00:00:01,000 --> 00:00:04,000\nThe quick brown\nfox jumps\n\n'
                                '2\n00:00:05,500 --> 00:00:06,000\nover.\n')
        self.assertEqual(tr.text, 'The quick brown fox jumps over.')
        first = tr.words[:5]
        self.assertAlmostEqual(first[0].start, 1.0)
        self.assertAlmostEqual(first[-1].end, 4.0)
        for a, b in zip(first, first[1:]):
            self.assertAlmostEqual(a.end, b.start)
            self.assertGreater(a.end, a.start)
        self.assertTrue(all(1.0 <= w.start < w.end <= 4.0 + 1e-9 for w in first))
        self.assertGreater(first[1].end - first[1].start, first[0].end - first[0].start)  # quick > The
        self.assertEqual((tr[-1].start, tr[-1].end), (5.5, 6.0))
        self.assertFalse(any(w.exact for w in tr))
        self.assertIs(type(captions.parse('﻿1\r\n00:00:01,000 --> 00:00:02,000\r\nHi\r\n')), captions.Track)

    def test_markup_entities_and_sound_labels_stripped(self):
        tr = captions.parse_srt('1\n00:00:00,000 --> 00:00:03,000\n[Music]\n<b>Tom</b> &amp; <font color="red">Jerry</font>'
                                ' &quot;ran&quot;\n\n2\n00:00:03,000 --> 00:00:04,000\n&gt;&gt; Yes ♪ [Applause]\n')
        self.assertEqual(tr.text, 'Tom & Jerry "ran" Yes')
        self.assertEqual([w.text for w in tr if w.turn], ['Yes'])

    def test_malformed_raises_naming_the_line(self):
        cases = [
            ('1\n00:00:01,000 --> 00:00:02,000\nok\n\n2\nno timing here\n', r'line 6'),
            ('1\n00:00:01,000 -> 00:00:02,000\nok\n', r'line 2'),
            ('WEBVTT\n\n00:00:01.000 --> 00:00:xx.000\nhi\n', r'line 3: bad cue timing'),
            ('WEBVTT\n\n00:00:03.000 --> 00:00:01.000\nhi\n', r'line 3: cue ends before'),
            ('not a vtt\n', r'line 1'),
            ('WEBVTT\n', r'no cues'),
            ('', r'no cues'),
            ('WEBVTT\n\n00:00:01.000 --> 00:00:04.000\na<00:00:03.000><c> b</c><00:00:02.000><c> c</c>\n', r'line 3'),
        ]
        for src, msg in cases:
            with self.subTest(src=src):
                parse = captions.parse_vtt if src.startswith(('WEBVTT', 'not')) else captions.parse
                with self.assertRaisesRegex(ValueError, msg):
                    parse(src)


class ShiftSlice(unittest.TestCase):
    def test_clip_from_source_lands_on_the_film_clock(self):
        tr = captions.parse(ROLLING)
        # a clip of the source from 3 s to 6 s, placed at 10 s in the film
        clip = tr.slice(3.0, 6.0).shift(10.0 - 3.0)
        self.assertEqual(clip.text, "asks if he's seen any bodies.")
        self.assertAlmostEqual(clip[0].start, 10.0)
        self.assertLessEqual(clip[-1].end, 13.0 + 1e-9)
        self.assertEqual(len(tr), len(captions.parse(ROLLING)))  # the original is untouched
        self.assertEqual(len(tr.slice(100, 200)), 0)


@unittest.skipUnless(FIXTURE.exists(), 'real YouTube caption fixture not attached')
class RealFixture(unittest.TestCase):
    def test_youtube_auto_captions(self):
        tr = captions.load(FIXTURE)
        ws = [w.text.casefold() for w in tr]
        self.assertGreater(len(ws), 1500)
        starts = [w.start for w in tr]
        self.assertEqual(starts, sorted(starts))
        # The rolling repeats would double every line; the text's own
        # repeats ("I've I've") are rare.
        repeats = sum(a == b for a, b in zip(ws, ws[1:]))
        self.assertLess(repeats, len(ws) * 0.01)
        grams = [tuple(ws[i:i + 4]) for i in range(len(ws) - 3)]
        self.assertFalse([g for i, g in enumerate(grams[:-4]) if g == grams[i + 4]])
        self.assertFalse(any('<' in w or '&' in w or '>' in w for w in ws))
        self.assertTrue(all(w.end >= w.start for w in tr))


def _track(*cues):
    """A track from (start, end, 'words ...') with each word given an equal slice."""
    words = []
    for a, b, s in cues:
        ws = s.split()
        d = (b - a) / len(ws)
        words += [captions.Word(w, a + i * d, a + (i + 1) * d) for i, w in enumerate(ws)]
    return captions.Track(words)


class Grouping(unittest.TestCase):
    font = Font('Cantarell', 48, weight=700)

    def assert_lines_ok(self, tr, lines, width):
        self.assertEqual([w for ln in lines for w in ln.words], list(tr.words))  # every word, whole, once
        for ln in lines:
            self.assertLessEqual(text.measure(ln.text, self.font), width, ln.text)
        for a, b in zip(lines, lines[1:]):
            self.assertLessEqual(a.end, b.start)  # one line at a time

    def test_lines_fit_the_measured_width(self):
        tr = _track((0, 9, 'the quick brown fox jumps over the lazy dog while seven foot tall plus sort of '
                           'gorilla looking creatures watch from somewhere behind the extraordinarily tall hedge'))
        for width in (400, 550, 700):
            lines = tr.lines(self.font, width)
            self.assertGreater(len(lines), 1)
            self.assert_lines_ok(tr, lines, width)
        # balanced: no straggler line much shorter than the rest
        lines = tr.lines(self.font, 700)
        ws = [text.measure(ln.text, self.font) for ln in lines]
        self.assertGreater(min(ws[:-1]), 0.6 * max(ws))

    def test_breaks_at_sentence_ends_pauses_and_speakers(self):
        tr = _track((0, 1, 'Yes. No.'), (1, 2, 'one two'), (3.5, 4, 'three'))
        words = list(tr.words)
        words[-1] = captions.Word('Four', 4.0, 4.5, turn=True)
        tr = captions.Track(words[:-1] + [captions.Word('three', 3.5, 3.8), words[-1]])
        self.assertEqual([ln.text for ln in tr.lines(self.font, 2000)], ['Yes.', 'No.', 'one two', 'three', 'Four'])
        lines = tr.lines(self.font, 2000)
        self.assertAlmostEqual(lines[2].end, 2.0)  # gone in the pause: nothing on screen at 3 s
        self.assertIsNone(tr.line_at(3.0, self.font, 2000))
        self.assertIs(tr.line_at(1.2, self.font, 2000), lines[2])

    def test_linger_ends_a_line_whose_last_word_runs_on(self):
        tr = captions.Track([captions.Word('Wait.', 0.0, 5.0), captions.Word('Then', 5.0, 5.5)])
        lines = tr.lines(self.font, 2000)
        self.assertEqual(lines[0].end, 1.0)
        self.assertIsNone(tr.line_at(2.0, self.font, 2000))

    @unittest.skipUnless(FIXTURE.exists(), 'real YouTube caption fixture not attached')
    def test_real_fixture_in_a_phone_frame(self):
        tr = captions.load(FIXTURE)
        width = 1080 * 0.75
        lines = tr.lines(self.font, width)
        self.assert_lines_ok(tr, lines, width)
        self.assertLess(sum(len(ln.words) for ln in lines) / len(lines), 8)


def _share(cv, box, colour, tol=40):
    """The fraction of pixels in `box` within `tol` of `colour` ('#rrggbb')."""
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    data, stride = cv.surface.get_data(), cv.surface.get_stride()
    hits = total = 0
    for y in range(int(box.y), int(box.bottom)):
        row = y * stride
        for x in range(int(box.x), int(box.right)):
            pb, pg, pr = data[row + 4 * x], data[row + 4 * x + 1], data[row + 4 * x + 2]
            total += 1
            hits += abs(pr - r) <= tol and abs(pg - g) <= tol and abs(pb - b) <= tol
    return hits / max(1, total)


TALK = _track((0.0, 2.0, 'seven foot tall plus sort of gorilla looking.'), (4.0, 5.0, 'Then more.'))


class Draw(unittest.TestCase):
    def test_inside_the_safe_area_in_every_format(self):
        for name, f in vb.FORMATS.items():
            for t in (0.1, 1.9, 4.5):
                with self.subTest(format=name, t=t):
                    cv = Canvas(f.width, f.height, '#ffffff', format=f)
                    drawn = captions.draw(cv, TALK, t)
                    self.assertEqual([n for n, _ in cv.marks], ['caption'])
                    box = cv.marks[0][1]
                    safe = captions.safe_area(cv)
                    self.assertTrue(safe.contains(box), (box, safe))
                    self.assertAlmostEqual(box.bottom, safe.bottom)  # at the bottom by default
                    self.assertGreater(box.cy, f.height * 0.6)
                    for _, wb, _ in drawn.words:
                        self.assertTrue(box.contains(wb))
            cv = Canvas(f.width, f.height, format=f)
            self.assertGreaterEqual(captions.default_font(cv).size, 60)  # phone-readable at 1080 wide

    def test_own_safe_area_and_position(self):
        cv = Canvas(1080, 1920)
        safe = Box(100, 300, 880, 1000)
        captions.draw(cv, TALK, 0.5, safe=safe, position='top', mark='sub')
        (name, box), = cv.marks
        self.assertEqual(name, 'sub')
        self.assertAlmostEqual(box.y, 300)
        self.assertTrue(safe.contains(box))

    def test_spoken_word_and_keywords_take_their_colours(self):
        cv = Canvas(1920, 1080, '#ffffff')
        t = 0.9  # 'sort', 5th of 8 words over 0-2 s, is spoken from 1.0; 'plus' (0.75-1.0) now
        drawn = captions.draw(cv, TALK, t, keywords={'SORT', 'gorilla'},
                              color='#ffffff', spoken='#ffd23f', accent='#3ddc97', box='#000000', box_alpha=1)
        colours = {w.text: c for w, _, c in drawn.words}
        self.assertEqual(colours['plus'], '#ffd23f')
        self.assertEqual(colours['sort'], '#3ddc97')
        self.assertEqual(colours['gorilla'], '#3ddc97')
        self.assertEqual(colours['seven'], '#ffffff')
        boxes = {w.text: b for w, b, _ in drawn.words}
        self.assertGreater(_share(cv, boxes['plus'], '#ffd23f'), 0.05)
        self.assertGreater(_share(cv, boxes['sort'], '#3ddc97'), 0.05)
        self.assertGreater(_share(cv, boxes['looking.'], '#ffffff'), 0.05)
        for word in ('seven', 'looking.'):
            self.assertEqual(_share(cv, boxes[word], '#ffd23f'), 0)
            self.assertEqual(_share(cv, boxes[word], '#3ddc97'), 0)
        self.assertEqual(_share(cv, boxes['plus'], '#3ddc97'), 0)
        self.assertGreater(_share(cv, drawn.box.pad(1), '#000000', tol=10), 0.5)  # a solid dark box

    def test_highlight_never_moves_the_layout(self):
        boxes = []
        for t in (0.1, 0.9, 1.6):
            cv = Canvas(1920, 1080)
            d = captions.draw(cv, TALK, t, keywords={'sort'})
            boxes.append((d.box, [b for _, b, _ in d.words]))
        self.assertEqual(boxes[0], boxes[1])
        self.assertEqual(boxes[1], boxes[2])

    def test_a_word_too_wide_alone_shrinks_to_fit(self):
        cv = Canvas(1080, 1920)
        tr = captions.Track([captions.Word('Pneumonoultramicroscopicsilicovolcanoconiosis', 0, 2)])
        d = captions.draw(cv, tr, 0.5)
        self.assertTrue(captions.safe_area(cv).contains(d.box))

    def test_nothing_drawn_in_a_gap(self):
        for t in (-1.0, 3.0, 9.0):
            cv = Canvas(1080, 1920, '#336699')
            before = bytes(cv.surface.get_data())
            self.assertIsNone(captions.draw(cv, TALK, t))
            self.assertEqual(cv.marks, [])
            self.assertEqual(bytes(cv.surface.get_data()), before)


class DocExample(unittest.TestCase):
    DOC = Path(__file__).resolve().parent.parent / 'skill' / 'make-a-video' / 'reference' / 'captions.md'

    def test_the_reference_example_runs(self):
        blocks = re.findall(r'```python\n(.*?)```', self.DOC.read_text(), re.S)
        example = next(b for b in blocks if 'vb.Film(' in b)
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'film.py'
            path.write_text(example)
            film = vb.load(str(path))
        self.assertEqual(film.frames, 150)
        for f in film.formats:
            self.assertEqual(film.frame(15, f).marks, [])  # before the clip starts
            cv = film.frame(round(2.6 * 30), f)  # film 2.6 s = source 2.1 s, 'sort of gorilla looking.'
            (name, box), = cv.marks
            self.assertEqual(name, 'caption')
            self.assertTrue(vb.captions.safe_area(cv).contains(box))
        # in the film's clock, 'gorilla' starts 0.5 s later than in the source
        line = film.draw.__globals__['TRACK'].line_at(2.7, vb.captions.default_font(cv), 900)
        self.assertIn('gorilla', line.text)
