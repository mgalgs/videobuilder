"""Lyric Line Crossfade: one sung line at a time sits in the same place, and
at each change the old line dissolves away while the next one dissolves in
over it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _smooth(x):
    x = vb.clamp01(x)
    return x * x * (3 - 2 * x)


def lyric_alphas(lines, t, fade=0.4):
    """The opacity of each timed line at time `t`, as `(text, alpha)` pairs
    for the lines that show at all. `lines` is `(text, start, end)` in
    seconds, in order. Each line fades in across `fade` seconds centred on
    its `start` and out across `fade` centred on its `end`, so where one line
    ends as the next starts the two overlap and cross. The first line is
    already up at its start and the last stays up after its end."""
    out = []
    half = fade / 2
    for i, (text, start, end) in enumerate(lines):
        a_in = 1.0 if i == 0 else _smooth((t - start + half) / fade)
        a_out = 1.0 if i == len(lines) - 1 else 1 - _smooth((t - end + half) / fade)
        a = min(a_in, a_out)
        if a > 0:
            out.append((text, a))
    return out


def draw_lyric_crossfade(cv, lines, t, font, cx, cy, color, fade=0.4):
    """Draw the lyric for time `t` centred at (cx, cy): the current line, or
    two lines crossing mid-change, each centred on the same point. `lines`
    and `fade` go to `lyric_alphas`. Returns the Box of the lines drawn, or
    None when nothing shows."""
    box = None
    for text, a in lyric_alphas(lines, t, fade):
        w, h = vb.text.block_size([text], font)
        b = vb.text.draw(cv, [text], font, cx - w / 2, cy - h / 2, color, alpha=a)
        if box is not None:
            x, y = min(box.x, b.x), min(box.y, b.y)
            b = vb.Box(x, y, max(box.right, b.right) - x, max(box.bottom, b.bottom) - y)
        box = b
    return box


LYRICS = (('City lights are calling', 0.0, 1.0),
          ('we keep on running', 1.0, 2.0),
          ('until the morning', 2.0, 3.0))


def draw(n, cv):
    box = draw_lyric_crossfade(cv, LYRICS, n / demo.FPS, demo.font(84, 700), demo.W / 2, demo.H / 2,
                               demo.INK, fade=0.5)
    if box is not None:
        cv.mark('text', *box)


TECHNIQUE = Technique(
    id='lyric-line-crossfade',
    name='Lyric line crossfade',
    family='typography',
    group='Lyrics and captions',
    aliases=('lyric dissolve', 'line-by-line lyric fade', 'karaoke line crossfade'),
    definition='Song lines appear one at a time in the same spot, and at each change the current line '
               'melts away while the next one fades up through it.',
    phrasings=('show the lyrics one line at a time, fading from each line into the next',
               'each lyric line dissolves into the following one in the middle of the screen',
               'smooth fades between the lines of the song text'),
    related=('theme-swap-crossfade', 'cross-dissolve', 'typeface-crossfade', 'per-line-fade-in',
             'cross-zoom', 'image-crossfade-slideshow'),
    api=('videobuilder.techniques.typography.lyric_line_crossfade.draw_lyric_crossfade',
         'videobuilder.techniques.typography.lyric_line_crossfade.lyric_alphas'),
    demo=lambda: demo.film(draw),
)
