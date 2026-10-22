"""Spiral Wipe: the incoming scene is revealed along a band that winds out
from the centre like a coil, each turn sitting snug against the last, until
it has swallowed the whole frame."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _arm(cv, turns, cx, cy):
    """The spiral's centre and its outer edge as a function of angle: the
    radius grows one band-width per turn and reaches the farthest corner
    after `turns` turns."""
    w, h = cv.width, cv.height
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    reach = max(math.hypot(x - cx, y - cy) for x in (0, w) for y in (0, h))
    gap = reach / turns
    return cx, cy, lambda a: max(0.0, gap * a / (2 * math.pi))


def _trace(c, cx, cy, r, a0, a1, steps):
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        c.line_to(cx + r(a) * math.cos(a), cy + r(a) * math.sin(a))


def spiral_region(cv, p, turns=4, cx=None, cy=None, steps=180):
    """Trace on `cv.ctx` the area a spiral arm has swept at progress `p`
    (0 -> 1): an Archimedean band, coiling out from (cx, cy) (default the
    frame centre), each turn snug against the last, covering the whole frame
    at 1. Leaves the path set for `clip` or `fill`; returns the angle the
    arm's tip has reached."""
    cx, cy, r = _arm(cv, turns, cx, cy)
    tip = vb.clamp01(p) * 2 * math.pi * (turns + 1)
    c = cv.ctx
    c.new_path()
    _trace(c, cx, cy, r, tip - 2 * math.pi, tip, steps)  # the last turn bounds everything swept before it
    c.close_path()                                        # the radial edge from the tip in to the turn below
    return tip


def spiral_wipe(cv, a, b, p, turns=4, cx=None, cy=None, edge=demo.ACCENT, edge_width=8, ease=None):
    """Draw the spiral wipe at progress `p` (0 -> 1): `a(cv)`, with `b(cv)`
    showing inside a band that coils out from (cx, cy) over `turns` turns.
    `edge` strokes the coil so far, brightest at the tip and fading on the
    inner turns (None for a clean cut). `ease`, if given, reshapes `p`; without
    one the arm turns at a steady rate.

    In a film, call it while two shots are live in an overlap, e.g.
    `spiral_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    p = vb.clamp01(ease(p) if ease else p)
    a(cv)
    if p <= 0:
        return
    c = cv.ctx
    c.save()
    tip = spiral_region(cv, p, turns, cx, cy)
    c.clip()
    b(cv)
    c.restore()
    if not edge or p >= 1:
        return
    ox, oy, r = _arm(cv, turns, cx, cy)
    c.save()
    c.set_line_width(edge_width)
    c.set_line_join(1)  # round
    seg = math.pi / 6
    a1 = tip
    while a1 > 0:
        a0 = max(0.0, a1 - seg)
        c.new_path()
        _trace(c, ox, oy, r, a0, a1, 12)
        c.set_source_rgba(*vb.rgba(edge, 0.25 ** ((tip - a1) / (2 * math.pi))))
        c.stroke()
        a1 = a0
    c.restore()


TECHNIQUE = Technique(
    id='spiral-wipe',
    name='Spiral wipe',
    family='transitions',
    group='Wipes',
    aliases=('spiral transition', 'swirl wipe', 'coil wipe'),
    definition='The next scene unwinds into view along a widening coil that starts at the centre '
               'and spirals outward until it fills the frame.',
    phrasings=('reveal the next shot in a spiral from the middle',
               'wipe to the new scene with a curling, snail-shell shape',
               'spin the second scene in from the centre like a coil'),
    related=('paint-brush-wipe', 'roll-up', 'swirl', 'wipe-reveal', 'uncover', 'circular-clip-reveal'),
    api=('videobuilder.techniques.transitions.spiral_wipe.spiral_wipe',
         'videobuilder.techniques.transitions.spiral_wipe.spiral_region'),
    demo=lambda: demo.two_scenes(spiral_wipe, start=0.6, length=1.8),
)
