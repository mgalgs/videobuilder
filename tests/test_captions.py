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
