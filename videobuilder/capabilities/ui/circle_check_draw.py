"""Circle Check Draw: the success mark. A ring strokes itself on around a
point, then a check mark draws inside it in one quick stroke, and the whole
badge gives a small pop as the stroke finishes."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ring_points(cx, cy, r, start=-math.pi / 2, steps=96):
    """A closed circle of radius `r` about (cx, cy) as an open point list,
    beginning at angle `start` (default: twelve o'clock) and running
    clockwise, so `vb.paths.reveal` draws it on from there."""
    return [(cx + r * math.cos(start + 2 * math.pi * i / steps),
             cy + r * math.sin(start + 2 * math.pi * i / steps)) for i in range(steps + 1)]


def check_points(cx, cy, r):
    """A check mark sized to sit inside a ring of radius `r` at (cx, cy):
    a short down stroke into the elbow, then the long stroke up and right."""
    return [(cx - 0.42 * r, cy + 0.02 * r), (cx - 0.12 * r, cy + 0.32 * r), (cx + 0.45 * r, cy - 0.30 * r)]


def draw_circle_check(cv, cx, cy, r, p, color, width=None, ring_end=0.55, check_start=0.5, pop=0.08,
                      fill=None, fill_alpha=0.18):
    """Draw the circle-check badge at progress `p` (0 -> 1), centred at
    (cx, cy) with radius `r`. The ring draws on clockwise from the top over
    `[0, ring_end]`; the check draws over `[check_start, 1]` (overlap them for
    one continuous gesture). As the check lands the badge swells by `pop` and
    settles back. `fill` tints the inside once the ring closes, at
    `fill_alpha`. Stroke `width` defaults to r / 7. Returns the badge's Box."""
    p = vb.clamp01(p)
    width = width or r / 7
    ring = vb.ease_in_out_quart(vb.clamp01(p / ring_end))
    tick = vb.ease_out_quint(vb.clamp01((p - check_start) / (1 - check_start)))
    s = 1 + pop * math.sin(math.pi * vb.clamp01((p - 0.82) / 0.18))  # one swell over the last stretch
    with cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s):  # scaled about the centre
        if fill and ring >= 1:
            demo.dot(cv, cx, cy, r, color=fill, alpha=fill_alpha * vb.clamp01((p - ring_end) / 0.15))
        if ring > 0:
            vb.paths.draw(cv, vb.paths.reveal(ring_points(cx, cy, r), ring), color, width=width)
        if tick > 0:
            vb.paths.draw(cv, vb.paths.reveal(check_points(cx, cy, r), tick), color, width=width * 1.15)
    half = (r + width / 2) * s
    return vb.Box(cx - half, cy - half, 2 * half, 2 * half)


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H / 2 - 40, 150
    box = draw_circle_check(cv, cx, cy, r, demo.phase(n, 0.3, 1.9), demo.TEAL, fill=demo.TEAL)
    cv.mark('badge', *box)
    a = demo.phase(n, 1.8, 2.3)
    if a > 0:
        demo.word(cv, 'Done', cx, cy + r + 90, size=64, alpha=a)


TECHNIQUE = Technique(
    id='circle-check-draw',
    name='Circle check draw',
    family='ui',
    group='Feedback & status',
    aliases=('success checkmark', 'animated check', 'check in circle', 'success tick'),
    definition='A ring traces itself around a point and a check mark then strokes in inside it, '
               'confirming that something finished.',
    phrasings=('a circle draws itself and then a tick appears inside to show it worked',
               'the success check animation when a payment or upload goes through',
               'draw a checkmark inside a circle to say done'),
    related=('checkbox-check-draw', 'highlight-circle-draw', 'circle-pop', 'bouncing-dots',
             'callout-highlight', 'border-draw-button'),
    api=('videobuilder.techniques.ui.circle_check_draw.draw_circle_check',
         'videobuilder.paths.reveal',
         'videobuilder.paths.draw'),
    demo=lambda: demo.film(draw),
)
