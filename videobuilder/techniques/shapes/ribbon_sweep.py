"""Ribbon Sweep: a stack of wide, gently waving ribbons streaks across the
frame one after another until they cover it, the cut happens underneath,
then their tails pull through and off the far side to uncover the next scene."""
import math

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Technique

COLORS = (demo.ACCENT, demo.TEAL, '#f2b84b', demo.INK, '#6c7bd9')


def _ribbons(w, h, count, angle, wave):
    """The centre lines of `count` parallel ribbons tilted `angle` radians,
    spaced to cover a `w` x `h` frame, each running well past both edges.
    Returns (point lists, stroke width)."""
    dx, dy = math.cos(angle), math.sin(angle)
    nx, ny = -dy, dx
    reach = abs(w * nx) + abs(h * ny)       # the frame's extent across the ribbons
    spacing = reach / count
    width = spacing * 1.25 + 2 * wave       # overlap so neighbours leave no gaps
    run = abs(w * dx) + abs(h * dy) + 2 * width  # along the ribbons, past both edges
    cx, cy = w / 2, h / 2
    out = []
    for i in range(count):
        off = (i + 0.5) * spacing - reach / 2
        pts = []
        for k in range(61):
            s = -run / 2 + run * k / 60
            bend = wave * math.sin(s / run * 2 * math.pi * 1.5 + i * 1.3)
            pts.append((cx + dx * s + nx * (off + bend), cy + dy * s + ny * (off + bend)))
        out.append(pts)
    return out, width


def _span(points, t0, t1):
    """The part of `points` between arc-length fractions `t0` and `t1`."""
    head = paths.reveal(points, t1)
    if t0 <= 0 or len(head) < 2:
        return head
    tail = paths.reveal(list(reversed(head)), 1 - t0 / t1)
    return list(reversed(tail))


def ribbon_sweep(cv, a, b, p, count=5, angle=-0.3, wave=24, stagger=0.12, colors=COLORS, ease=vb.ease_in_out_quart):
    """Draw the sweep at progress `p` (0 -> 1). For the first half the
    ribbons' heads race across in turn (staggered by `stagger`) over `a(cv)`
    until the frame is covered; for the second half their tails follow them
    off over `b(cv)`. `angle` tilts the ribbons (radians, 0 = left to right),
    `wave` is how far they undulate in px; `colors` cycle across the ribbons.

    In a film, call it while two shots are live in an overlap, e.g.
    `ribbon_sweep(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    lines, width = _ribbons(cv.width, cv.height, count, angle, wave)
    first = p < 0.5
    (a if first else b)(cv)
    q = p / 0.5 if first else (p - 0.5) / 0.5
    span = 1 - stagger * (count - 1)
    for i, pts in enumerate(lines):
        t = ease(vb.clamp01((q - stagger * i) / span))
        t0, t1 = (0.0, t) if first else (t, 1.0)
        if t1 - t0 <= 1e-4:
            continue
        seg = _span(pts, t0, t1)
        paths.draw(cv, [(x, y + 10) for x, y in seg], '#000000', width=width, alpha=0.25)
        paths.draw(cv, seg, colors[i % len(colors)], width=width)


TECHNIQUE = Technique(
    id='ribbon-sweep',
    name='Ribbon sweep',
    family='shapes',
    group='Lines & strokes',
    aliases=('ribbon wipe', 'stroke wipe', 'band sweep', 'swoosh transition'),
    definition='Thick coloured ribbons streak across the screen one after another until they cover it, '
               'then trail off the far side to leave the next scene behind.',
    phrasings=('sweep some colourful bands across to switch scenes',
               'a swoosh of stripes wipes the shot away',
               'ribbons fly across the screen and reveal the next shot'),
    related=('diagonal-wipe', 'spiral-wipe', 'linear-wipe', 'paint-brush-wipe', 'zigzag-wipe', 'pinwheel-wipe'),
    api=('videobuilder.techniques.shapes.ribbon_sweep.ribbon_sweep',),
    demo=lambda: demo.two_scenes(ribbon_sweep),
)
