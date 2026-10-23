"""Drip Wipe: the incoming scene runs down over the outgoing one from the top
edge like wet paint, its leading edge hanging in uneven, rounded drips that
stretch ahead of the rest until the whole frame is covered."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def drip_edge(w, h, p, drips=11, length=0.28, seed=0, steps=640):
    """The drip front at progress `p` (0 -> 1) across a `w` x `h` frame, as
    `[(x, y), ...]` from left to right. The covered region is everything
    above it. A level line falls from above the frame to its bottom while
    `drips` tongues, each up to `length` x `h` long and starting at its own
    moment, hang below it; at `p` 1 the whole edge is at or past the bottom.
    The same `seed` gives the same drips, frame for frame.

    Each tongue is a capsule: a straight-sided stem with a round end, joined
    to the line by a small curved shoulder, and narrow next to the spacing so
    the level line shows between drips. A few of them are long and early and
    run well ahead of the rest."""
    rnd = random.Random(seed)
    gap = w / drips
    leaders = set(rnd.sample(range(drips), min(drips, 3)))
    tongues = []
    for i in range(drips):
        x = gap * (i + 0.3 + 0.4 * rnd.random())
        half = gap * (0.15 + 0.1 * rnd.random())
        if i in leaders:
            size, delay = length * h * (0.8 + 0.2 * rnd.random()), 0.05 * rnd.random()
        else:
            size, delay = length * h * (0.15 + 0.3 * rnd.random()), 0.1 + 0.25 * rnd.random()
        tongues.append((x, half, size, delay))
    reach = length * h
    e = p * p * (3 - 2 * p)
    level = -reach + (h + reach + 0.02 * h) * e  # ends past the bottom, ripple and all
    pts = []
    for k in range(steps + 1):
        x = w * k / steps
        line = level + 0.01 * h * math.sin(x / w * 9 + seed)  # the wet line itself ripples a little
        y = line
        for tx, half, size, delay in tongues:
            drop = size * vb.ease_in_out_quart(vb.clamp01((p - delay) / 0.55))
            if drop <= 0:
                continue
            r = half * min(1.0, 0.5 + drop / (2 * half))  # a short drip is a shallow round bead
            neck = 0.6 * r  # the shoulder where the stem meets the line
            d = abs(x - tx)
            if d < r:
                y = max(y, line + drop - r + math.sqrt(r * r - d * d))
            elif d < r + neck and drop > neck:
                u = d - r - neck
                y = max(y, line + neck - math.sqrt(max(0.0, neck * neck - u * u)))
        pts.append((x, y))
    return pts


def drip_wipe(cv, a, b, p, drips=11, length=0.28, seed=0, edge=None):
    """Draw the drip wipe at progress `p` (0 -> 1): `a(cv)` underneath, and
    `b(cv)` showing through a region that pours down from the top edge in
    drips (see `drip_edge`). `edge`: an optional colour for a thin wet rim
    along the front.

    In a film, call it while two shots are live in an overlap, e.g.
    `drip_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    a(cv)
    w, h = cv.width, cv.height
    pts = drip_edge(w, h, p, drips=drips, length=length, seed=seed)
    c = cv.ctx
    c.save()
    c.move_to(0, -1)
    c.line_to(w, -1)
    for x, y in reversed(pts):
        c.line_to(x, y)
    c.close_path()
    c.clip()
    b(cv)
    c.restore()
    if edge is not None:
        vb.paths.draw(cv, pts, edge, width=4, alpha=0.9)


def _paint(cv):
    """Scene B for the demo: a flat coat of the accent with a word on it, so
    the drips read as paint."""
    cv.fill(demo.ACCENT)
    demo.word(cv, 'B', demo.W / 2, demo.H / 2, size=260, color=demo.BG)


CAPABILITY = Capability(
    id='drip-wipe',
    name='Drip wipe',
    family='transitions',
    group='Wipes',
    aliases=('melt wipe', 'paint drip wipe', 'dripping paint transition'),
    definition='The next scene pours down from the top of the frame like wet paint, '
               'its lower edge hanging in uneven drips that run ahead until the screen is covered.',
    phrasings=('have the new scene drip down over the old one like paint',
               'melt into the next shot from the top, with drips',
               'a gooey paint-drip transition'),
    related=('paint-brush-wipe', 'smoke-dissolve', 'ink-bleed', 'fill-sweep-button', 'wipe-reveal',
             'area-fill-sweep'),
    api=('videobuilder.capabilities.transitions.drip_wipe.drip_wipe',
         'videobuilder.capabilities.transitions.drip_wipe.drip_edge'),
    demo=lambda: demo.two_scenes(drip_wipe, start=1.1, length=1.6, b=_paint),
)
