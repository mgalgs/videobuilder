# Captions timed to each word

For commentary cuts (a podcast, a hearing) where the speaker's words run
along the bottom of the frame one short line at a time, the spoken word lit
up and chosen keywords in an accent colour. The input is a subtitle file;
`vb.captions` doesn't transcribe audio. For a generated voiceover,
`python -m videobuilder say` writes the subtitle file with the voice (one cue
per phrase): see `narration.md`.

## Reading a subtitle file

```python
track = vb.captions.load(HERE / 'assets' / 'talk.en.vtt')   # .vtt or .srt, sniffed from the content
track = vb.captions.parse(text)        # the same, from a string
```

- **YouTube auto-captions** (`yt-dlp --write-auto-subs --sub-format vtt`)
  carry a time for every word. Their cues roll: each line shows again in the
  next cue, under the new one. The parser gives every spoken word once, in
  order, with its own start time (`word.exact` is True).
- **SRT, and VTT without per-word times**, time whole lines only. Each cue's
  words are spread across it by length and marked `word.exact = False`, so
  the highlight is a good guess, not a measurement.
- Markup (`<c>`, `<i>`, `<v Name>`), HTML entities and sound labels
  (`[Music]`, `♪`) are stripped. A `>>` speaker mark is stripped too, and its
  word gets `word.turn = True`, so a caption line never mixes two speakers.
- A malformed file raises `ValueError` naming the line. It never returns an
  empty track.

A `Track` is a tuple of `Word(text, start, end, exact, turn)` in seconds:
`len(track)`, `track[i]`, `for w in track`, `track.text`.

## A clip from a longer source

A caption file covers the whole source video, but the film uses a clip cut
from it. `slice` keeps the clip's words and `shift` moves them onto the film's
clock. For a clip from source time `a` to `b`, placed `at` seconds into the
film:

```python
clip = track.slice(a, b).shift(at - a)
```

Both return new tracks; the original is unchanged.

## Drawing

```python
drawn = vb.captions.draw(cv, clip, t, keywords={'gorilla', 'sort'})
```

This draws the line on screen at `t` (seconds, on the track's clock) and
returns what it drew: `drawn.box`, `drawn.line`, and `drawn.words`, a tuple of
(word, Box, colour) entries. Between lines and in silences it draws nothing
and returns None.

- **Lines** are grouped from the words and measured with Pango in the real
  font, so they fit on the render machine too, whose fonts may be wider. A
  line breaks after a sentence end, at a pause (`pause=0.7` s), at a new
  speaker, and wherever the width forces. A long phrase is split into lines
  of even length. A line doesn't change while it's on screen; the next line
  replaces it. A word counts as spoken for at most `linger=1.0` s, so a line
  leaves the screen in a long silence.
- **Placement**: centred at the bottom of `safe` (`position='top'` or
  `'middle'` also work). By default `safe` is
  `vb.captions.safe_area(cv)`, a placeholder with the template's margins as
  fractions of the frame. Pass the film's own safe area: `safe=L['safe']`.
- **Size**: `font=` defaults to `vb.captions.default_font(cv)`, a bold sans
  at 5.8% of the frame's short side (63 px in 1080x1920), which reads on a
  phone. Pass the film's font at a size relative to the canvas, e.g.
  `vb.Font(FAMILY, cv.width * 0.06, weight=800)`. `max_width=` caps the
  line's text width; it defaults to the safe width less the box padding. A
  single word wider than that is drawn smaller, on that line only.
- **Colours**: `color='#ffffff'` for the line, `spoken='#ffd23f'` for the
  word being spoken, and `accent='#3ddc97'` for `keywords`. Keywords match
  case-insensitively and ignore punctuation (`'Sort,'` matches `'sort'`). A
  keyword keeps its accent while it is spoken. Only the colour changes, so
  the line never reflows.
- **Box**: `box='#000000'` at `box_alpha=0.72` reads over any footage. Use
  `box_alpha=1` for a solid box, or `box=None` to draw none.
- **Mark**: the box is marked `'caption'` (`mark=` renames it; None turns it
  off), so `check.py` checks it against the safe area and the other marks.
  If footage is meant to sit behind it, list the pair in `OVERLAP_OK`.

## A complete example

```python
import videobuilder as vb

SUBS = """WEBVTT

00:00:00.500 --> 00:00:02.000
<00:00:00.500>Seven<00:00:00.800> foot<00:00:01.000> tall,<00:00:01.400> plus

00:00:02.000 --> 00:00:03.600
sort<00:00:02.400> of<00:00:02.600> gorilla<00:00:03.100> looking.
"""
# The source clip runs from 0.5 s to 3.6 s and starts 1 s into the film.
TRACK = vb.captions.parse(SUBS).slice(0.5, 3.6).shift(1.0 - 0.5)
FPS = 30


def draw(f, cv):
    cv.fill('#2b3a4a')  # the footage would go here
    font = vb.Font('sans-serif', min(cv.width, cv.height) * 0.06, weight=800)
    vb.captions.draw(cv, TRACK, f / FPS, keywords={'gorilla'}, font=font)


FILM = vb.Film(draw, fps=FPS, frames=5 * FPS, formats=('9x16', '16x9', '1x1'))

if __name__ == '__main__':
    vb.main(__file__)
```

The words in this VTT carry their own time tags, so the track is exact. With
the same words as an SRT, the timing within each cue would be interpolated.
