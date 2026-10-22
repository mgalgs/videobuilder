"""Highlight circle draw: a loose, hand-drawn ellipse strokes itself on around
a word, a little off-centre and tilted, overrunning its own start the way a
pen does when someone circles something on a page."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def circle_points(box, seed=0, pad=0.22, turns=1.15, tilt=-4.0, wobble=0.05, steps=160):
    """The stroke of a hand-drawn ring round `box` (x, y, w, h), as an open
    point list in drawing order. The ellipse clears the box by `pad` of its
    size, sits slightly off-centre, is tilted `tilt` degrees and runs `turns`
    times round (a bit over 1, so the tail overshoots the start). Its radius
    drifts by about `wobble` of itself and the second lap swings wider, so
    the ends don't meet. Deterministic for a given `seed`."""
    x, y, w, h = box
    rnd = random.Random(seed)
    cx = x + w / 2 + rnd.uniform(-0.03, 0.03) * w
    cy = y + h / 2 + rnd.uniform(0.0, 0.08) * h
    rx = w / 2 + (pad + 0.2) * h
    ry = h / 2 + pad * h * 0.4
    waves = [(rnd.uniform(1.5, 2.5), rnd.uniform(0, 2 * math.pi)),
             (rnd.uniform(3.0, 4.5), rnd.uniform(0, 2 * math.pi))]
    a0 = math.radians(rnd.uniform(-40, -20))  # start up and to the right, like a right-handed pen
    rot = math.radians(tilt)
    cr, sr = math.cos(rot), math.sin(rot)
    pts = []
    for i in range(steps + 1):
        u = i / steps
        a = a0 + 2 * math.pi * turns * u
        k = 1 + wobble * sum(math.sin(f * a + ph) for f, ph in waves) / 2 + 0.6 * max(0.0, u * turns - 0.9) ** 1.5
        ex, ey = rx * k * math.cos(a), ry * k * math.sin(a)
        pts.append((cx + ex * cr - ey * sr, cy + ex * sr + ey * cr))
    return pts


def draw_highlight_circle(cv, box, p, color=demo.ACCENT, width=6.0, seed=0, alpha=1.0, **shape):
    """Draw the hand-drawn ring round `box` (x, y, w, h) at progress `p`
    (0 -> 1): the stroke runs on with a quick start and a slowing finish, as
    one pen gesture, and its last few percent thin out like a lifting nib.
    `shape` goes to `circle_points` (`pad`, `turns`, `tilt`, `wobble`).
    Returns the Box the finished ring covers."""
    pts = circle_points(box, seed=seed, **shape)
    p = vb.clamp01(p)
    if p > 0:
        drawn = vb.paths.reveal(pts, 1 - (1 - p) ** 3)  # quick start, slowing finish
        cut = max(2, int(len(drawn) * 0.9))
        vb.paths.draw(cv, drawn[:cut + 1], color, width=width, alpha=alpha)
        tail = drawn[cut:]
        for i in range(len(tail) - 1):  # the lifting nib: the last stretch tapers off
            vb.paths.draw(cv, tail[i:i + 2], color, width=width * (1 - 0.6 * i / max(1, len(tail) - 1)),
                          alpha=alpha)
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    return vb.Box(min(xs) - width / 2, min(ys) - width / 2, max(xs) - min(xs) + width, max(ys) - min(ys) + width)


def draw(n, cv):
    demo.word(cv, 'The launch moves to', demo.W / 2, demo.H / 2 - 120, size=34, weight=600, color=demo.MUTED)
    key = demo.word(cv, 'Friday', demo.W / 2, demo.H / 2 + 16, size=104, weight=800)
    box = draw_highlight_circle(cv, key, demo.phase(n, 0.5, 1.6), seed=4, width=5)
    cv.mark('ring', *box)


TECHNIQUE = Technique(
    id='highlight-circle-draw',
    name='Highlight circle draw',
    family='broadcast',
    group='Annotation',
    aliases=('circle the word', 'ring highlight', 'hand-drawn circle', 'marker circle'),
    definition='A loose, slightly lopsided loop is sketched around a word or object in one quick '
               'pen stroke, its end running past where it began.',
    phrasings=('draw a scribbled circle round the important word',
               'circle that number like someone marked it with a pen',
               'have a hand-drawn ring loop around the thing I want people to look at'),
    related=('focus-ring-draw', 'circle-check-draw', 'progress-ring', 'callout-highlight',
             'rotating-circular-text', 'orbital-pulse'),
    api=('videobuilder.techniques.broadcast.highlight_circle_draw.draw_highlight_circle',
         'videobuilder.techniques.broadcast.highlight_circle_draw.circle_points'),
    demo=lambda: demo.film(draw),
)
