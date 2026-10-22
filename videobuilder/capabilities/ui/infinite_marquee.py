"""Infinite Marquee: a band of items slides steadily sideways forever, each
one that leaves at one edge already coming round again at the other."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def marquee_offset(t, speed, cycle):
    """How far the strip has moved at time `t` (s), in [0, cycle): `speed`
    px/s (negative runs it the other way), wrapped to one `cycle`, the width
    of one full set of items. For a film that loops, pick `speed` so the
    film's length times it is a whole number of cycles."""
    return (t * speed) % cycle


def marquee(cv, items, x, y, w, h, offset, pitch, fade=0.0, background=None):
    """Draw a marquee band at (x, y, w, h): `items`, a list of `draw(cv, cx, cy)`
    callables, laid out every `pitch` px and repeated end to end, shifted
    left by `offset` (from `marquee_offset`) and clipped to the band. `fade`
    px at each end melt into `background` (default the kit's), so items
    slide in and out rather than being cut. Returns the band's Box."""
    cycle = pitch * len(items)
    start = x - (offset % cycle) - pitch  # one item off the left edge, so nothing pops in
    cy = y + h / 2
    with cv.clip(x, y, w, h):
        i, left = 0, start
        while left < x + w + pitch:
            items[i % len(items)](cv, left + pitch / 2, cy)
            i, left = i + 1, left + pitch
        if fade > 0:
            steps = max(1, round(fade / 6))
            for k in range(steps):
                a = (1 - k / steps) ** 1.5
                s = fade / steps
                cv.rect(x + k * s, y, s + 0.5, h, background or demo.BG, alpha=a)
                cv.rect(x + w - (k + 1) * s - 0.5, y, s + 0.5, h, background or demo.BG, alpha=a)
    return vb.Box(x, y, w, h)


# ---- the demo: a row of icon tiles, like a logo strip ----

TILE = 132


def _tile(glyph, color):
    def draw(cv, cx, cy):
        x, y = cx - TILE / 2, cy - TILE / 2
        cv.rect(x, y, TILE, TILE, '#1e2028', radius=22)
        cv.outline(x, y, TILE, TILE, demo.LINE, width=2, radius=22)
        glyph(cv, cx, cy, color)
    return draw


def _ring(cv, cx, cy, c):
    cv.arc(cx, cy, 30, 0, 2 * math.pi, c, width=8)
    demo.dot(cv, cx, cy, 10, color=demo.ACCENT)


def _bars(cv, cx, cy, c):
    for i, hh in enumerate((56, 44, 32)):
        cv.rect(cx - 30 + i * 22, cy - 28, 14, hh, c, radius=7)


def _diamond(cv, cx, cy, c):
    with cv.layer(dx=cx, dy=cy):
        cv.ctx.rotate(math.pi / 4)
        cv.outline(-24, -24, 48, 48, c, width=6, radius=6)
        cv.rect(-9, -9, 18, 18, demo.ACCENT, radius=3)


def _zig(cv, cx, cy, c):
    pts = [(-30, 26), (-10, -26), (10, 26), (30, -26)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(cx + x0, cy + y0, cx + x1, cy + y1, c, width=9)


def _plus(cv, cx, cy, c):
    cv.rect(cx - 9, cy - 32, 18, 64, c, radius=9)
    cv.rect(cx - 32, cy - 9, 64, 18, c, radius=9)


def _dots(cv, cx, cy, c):
    for dx, dy in ((-18, -18), (18, -18), (-18, 18), (18, 18)):
        demo.dot(cv, cx + dx, cy + dy, 12, color=c)


def _word(cv, cx, cy, c):
    demo.word(cv, 'Aa', cx, cy, size=58, color=c)


ITEMS = [_tile(g, c) for g, c in ((_ring, demo.INK), (_bars, demo.TEAL), (_diamond, demo.INK),
                                  (_zig, demo.TEAL), (_plus, demo.INK), (_dots, demo.ACCENT),
                                  (_word, demo.TEAL), (_bars, demo.ACCENT))]
PITCH = 170


def draw(n, cv):
    band_h = 210
    y = (demo.H - band_h) / 2
    cv.line(0, y, demo.W, y, demo.LINE, width=2)
    cv.line(0, y + band_h, demo.W, y + band_h, demo.LINE, width=2)
    speed = PITCH * len(ITEMS) / demo.SECONDS  # one whole set per film: the end frame meets the start
    off = marquee_offset(n / demo.FPS, speed, PITCH * len(ITEMS))
    box = marquee(cv, ITEMS, 0, y + 2, demo.W, band_h - 4, off, PITCH, fade=260)
    cv.mark('marquee', *box)


TECHNIQUE = Technique(
    id='infinite-marquee',
    name='Infinite marquee',
    family='ui',
    group='Scroll',
    aliases=('logo ticker', 'ticker loop', 'endless ticker', 'looping scroll', 'scrolling banner'),
    definition='A strip of logos, words or tiles glides sideways at an even pace without end, '
               'the set repeating so the row never runs out or shows a gap.',
    phrasings=('a row of logos that keeps sliding across the screen on a loop',
               'an endless scrolling strip of our partners',
               'a banner of words that scrolls by forever'),
    related=('news-ticker-crawl', 'parallax-marquee-rows', 'scrolling-led-marquee-text',
             'infinite-scroll-append', 'seamless-loop', 'timeline-scroll'),
    api=('videobuilder.techniques.ui.infinite_marquee.marquee',
         'videobuilder.techniques.ui.infinite_marquee.marquee_offset'),
    demo=lambda: demo.film(draw),
)
