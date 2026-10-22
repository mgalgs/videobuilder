"""Highlighter Swipe: a translucent marker band sweeps across a phrase from
left to right, the way a highlighter pen is dragged over printed text."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

YELLOW = '#ffe14d'


def _edge(seed, amount):
    """A seeded wobble `x -> px`, smooth along the stroke, the same every frame."""
    rnd = random.Random(seed)
    waves = [(rnd.uniform(40, 90), rnd.uniform(0, 2 * math.pi), 0.6),
             (rnd.uniform(12, 24), rnd.uniform(0, 2 * math.pi), 0.3),
             (rnd.uniform(4, 7), rnd.uniform(0, 2 * math.pi), 0.1)]
    return lambda x: amount * sum(k * math.sin(x / wl + ph) for wl, ph, k in waves)


def highlighter_swipe(cv, x, y, w, h, p, color=YELLOW, alpha=0.85, slant=0.35, rise=-3.0, wobble=1.4,
                      seed=0, multiply=False):
    """Draw a highlighter band over the box (x, y, w, h), swiped to progress
    `p` (0 -> 1, left to right; ease it yourself, e.g. `vb.ease_in_out_quart`
    for a stroke that gets going, sweeps, then lifts off). Its ends are cut at the
    chisel angle `slant` (x offset per px of height), it drifts `rise` px over
    its length and its long edges wobble by about `wobble` px, seeded by `seed`.

    Draw it before the text so the ink sits on top, or after the text with
    `multiply=True` on a light ground so it tints the ink like a real marker.
    Returns the Box the band covers so far."""
    p = vb.clamp01(p)
    if p <= 0 or w <= 0:
        return vb.Box(x, y, 0, h)
    top, bottom = _edge(seed, wobble), _edge(seed + 1, wobble)
    lean = slant * h / 2
    x0, x1 = x - lean, x - lean + (w + 2 * lean) * p
    n = max(2, int((x1 - x0) / 4))
    xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    drift = lambda px: rise * (px - x) / max(w, 1)  # noqa: E731
    upper = [(px + lean, y + drift(px) + top(px)) for px in xs]
    lower = [(px - lean, y + h + drift(px) + bottom(px)) for px in reversed(xs)]
    c = cv.ctx
    c.save()
    if multiply:
        c.set_operator(cairo.OPERATOR_MULTIPLY)
    vb.paths.draw(cv, upper + lower, color, fill=True, alpha=alpha)
    c.restore()
    return vb.Box(x0, y, x1 - x0 + lean, h)


PAPER, PRINT = '#f3efe4', '#2b2a28'


def draw(n, cv):
    cw, ch = 760, 300
    cx, cy = (demo.W - cw) / 2, (demo.H - ch) / 2
    cv.shadow(cx, cy, cw, ch, radius=14, dy=12, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(cx, cy, cw, ch, PAPER, radius=14)
    small, big = demo.font(30, 500), demo.font(64, 800)
    vb.text.draw(cv, ['The one thing to remember:'], small, cx + 60, cy + 60, '#6d6a63')
    lead, key = 'Always ', 'ship small.'
    tx, ty = cx + 60, cy + 130
    kx = tx + vb.text.measure(lead, big)
    kw, kh = vb.text.block_size([key], big)
    vb.text.draw(cv, [lead + key], big, tx, ty, PRINT)
    p = vb.ease_in_out_quart(demo.phase(n, 0.6, 1.5))
    box = highlighter_swipe(cv, kx + 6, ty + kh * 0.12, kw + 4, kh * 0.8, p, seed=3, multiply=True)
    cv.mark('highlight', *box)


TECHNIQUE = Technique(
    id='highlighter-swipe',
    name='Highlighter swipe',
    family='ui',
    group='Text & type',
    aliases=('marker highlight', 'highlight sweep', 'text highlight reveal', 'highlighter pen effect'),
    definition='A see-through band of marker colour is dragged across a word or phrase from left to right, '
               'leaving it highlighted as if with a felt-tip pen.',
    phrasings=('swipe a yellow highlighter over the key phrase',
               'mark the important words like someone ran a highlighter across them',
               'have a highlight colour sweep in behind that line of text'),
    related=('underline-swash-draw', 'spotlight-hover', 'callout-highlight', 'whiteboard-marker-drawing',
             'stroke-draw-on', 'underline-wipe'),
    api=('videobuilder.techniques.ui.highlighter_swipe.highlighter_swipe',),
    demo=lambda: demo.film(draw),
)
