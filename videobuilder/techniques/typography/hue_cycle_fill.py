"""Hue cycle fill: the letters' fill colour rotates round the colour wheel
over time, each letter a step behind its neighbour, so a rainbow rolls
through the word while it stands still."""
import colorsys

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def hue_color(hue, saturation=0.8, lightness=0.6):
    """The colour at `hue` turns round the wheel (0 red, 1/3 green, 2/3 blue;
    wraps) as an '#rrggbb' string, at the given HSL `saturation` and `lightness`."""
    r, g, b = colorsys.hls_to_rgb(hue % 1.0, lightness, saturation)
    return '#%02x%02x%02x' % (round(r * 255), round(g * 255), round(b * 255))


def hue_cycle(text, t, speed=0.5, spread=0.08, start=0.0, **kw):
    """`text` at time `t` seconds as `(char, colour)` pairs. Each hue turns
    `speed` times round the wheel per second from `start`; letter `i` lags
    by `i * spread` turns, so the colours travel left to right (a negative
    `spread` sends them the other way, 0 cycles the word as one colour).
    `kw` goes to `hue_color`."""
    return [(ch, hue_color(start + speed * t - i * spread, **kw)) for i, ch in enumerate(text)]


def draw_hue_cycle(cv, text, font, x, y, t, alpha=1.0, **kw):
    """Draw `text` from its top-left (x, y) with its fill cycling hue at
    time `t` seconds, letter by letter, kerned as the whole line. `kw` goes
    to `hue_cycle`. Returns the Box of the line."""
    for i, (ch, colour) in enumerate(hue_cycle(text, t, **kw)):
        if not ch.isspace():
            vb.text.draw(cv, [ch], font, x + vb.text.measure(text[:i], font), y, colour, alpha=alpha)
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(150, 900)
    text = 'SPECTRUM'
    w, h = vb.text.block_size([text], f)
    box = draw_hue_cycle(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, n / demo.FPS,
                         speed=0.6, spread=0.07, saturation=0.85, lightness=0.6)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='hue-cycle-fill',
    name='Hue cycle fill',
    family='typography',
    group='Surface and light',
    aliases=('rainbow text', 'colour cycling text', 'hue rotate', 'rainbow fill'),
    definition='The fill colour of the lettering keeps turning round the colour wheel, '
               'each letter slightly behind the last, so a rainbow drifts through the word.',
    phrasings=('make the title shimmer through all the colours of the rainbow',
               'the words keep changing colour, cycling through the hues',
               'rainbow text where the colours flow across the letters'),
    related=('color-cycling', 'color-fill-rise', 'choropleth-fill', 'shape-fill-sweep',
             'karaoke-highlight-sweep', 'glyph-cycling'),
    api=('videobuilder.techniques.typography.hue_cycle_fill.draw_hue_cycle',
         'videobuilder.techniques.typography.hue_cycle_fill.hue_cycle',
         'videobuilder.techniques.typography.hue_cycle_fill.hue_color'),
    demo=lambda: demo.film(draw),
)
