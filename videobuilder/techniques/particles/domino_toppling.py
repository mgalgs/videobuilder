"""Domino Toppling: a row of upright tiles goes over one after another, each
falling tile tipping the next, until they lie as a leaning staircase."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _rest_angle(spacing, height, thickness, next_angle):
    """The tilt at which a tile's top front corner meets the back face of the
    next tile (pivot `spacing` further on, tilted `next_angle`), or a quarter
    turn when it clears it. Found by bisection: the corner only moves forward
    as the tilt grows."""
    sin_n, cos_n = math.sin(next_angle), math.cos(next_angle)
    bx, by = spacing - thickness * cos_n, thickness * sin_n  # the next tile's back-bottom corner

    def behind(a):  # > 0 while the corner is still behind the next tile's back face
        px, py = height * math.sin(a), height * math.cos(a)
        return (px - bx) * -cos_n + (py - by) * sin_n

    if behind(math.pi / 2) > 0:
        return math.pi / 2
    lo, hi = 0.0, math.pi / 2
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if behind(mid) > 0 else (lo, mid)
    return lo


def domino_angles(t, count, spacing, height, thickness, start=0.0, fall=0.4):
    """How far each of `count` dominoes has tipped at time `t` (seconds).

    The tiles stand in a row, pivots (front-bottom edges) `spacing` apart,
    each `height` tall and `thickness` deep, all falling forward (towards
    +x). Tile 0 is pushed at `start`; a free tile would swing from upright
    to flat in `fall` seconds, speeding up as it goes. Each tile starts
    moving the moment the one behind reaches it, and comes to rest leaning
    on it; the last one lies flat.

    Returns one angle in radians per tile, 0 upright and up to pi/2 flat. To
    draw tile `i`, rotate about its pivot `(x0 + i * spacing, ground)` by
    that angle (clockwise on screen) and fill the box from
    `(-thickness, -height)` to `(0, 0)`.
    """
    touch = _rest_angle(spacing, height, thickness, 0.0)
    every = fall * math.sqrt(touch / (math.pi / 2))  # time for a tile to swing into the next
    out = [0.0] * count
    nxt = None
    for i in reversed(range(count)):
        u = vb.clamp01((t - start - i * every) / fall)
        free = math.pi / 2 * u * u
        out[i] = free if nxt is None else min(free, _rest_angle(spacing, height, thickness, nxt))
        nxt = out[i]
    return out


COUNT = 11


def draw(n, cv):
    spacing, height, thick = 64, 150, 18
    ground = demo.H * 0.74
    x0 = (demo.W - (COUNT - 1) * spacing - height + thick) / 2  # centre the row as it lies at the end
    # A ball rolls in and taps the first tile over.
    r, hit = 16, 0.55
    roll = demo.phase(n, 0.1, hit)
    bx = -r + (x0 - thick) * roll  # in from off frame at a steady speed, so it arrives with some push
    cv.line(0, ground, demo.W, ground, demo.MUTED, width=3)  # full width: the ball rolls in along it
    angles = domino_angles(n / demo.FPS, COUNT, spacing, height, thick, start=hit, fall=0.34)
    for i, a in enumerate(angles):
        px = x0 + i * spacing
        corners = [(-thick, -height), (0, -height), (0, 0), (-thick, 0)]
        pts = [(px + x * math.cos(a) - y * math.sin(a), ground + x * math.sin(a) + y * math.cos(a))
               for x, y in corners]
        cv.shape_shadow(pts, dx=3, dy=3, blur=6, color=(0, 0, 0, 0.35))
        cv.ctx.save()
        cv.ctx.translate(px, ground)
        cv.ctx.rotate(a)
        cv.rect(-thick, -height, thick, height, demo.ACCENT if i == 0 else demo.TEAL, radius=3)
        cv.ctx.restore()
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        cv.mark(f'domino{i}', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    demo.dot(cv, bx, ground - r, r, color=demo.INK)


TECHNIQUE = Technique(
    id='domino-toppling',
    name='Domino toppling',
    family='particles',
    group='Rigid bodies',
    aliases=('domino chain', 'chain reaction toppling', 'domino effect'),
    definition='A line of standing tiles goes over in turn, each one tipping into its neighbour and '
               'knocking it down, until the whole row lies leaning in a slanted stack.',
    phrasings=('knock the first domino and let the rest fall down the line',
               'make the blocks tip over one after another like a chain reaction',
               'a row of tiles toppling in sequence'),
    related=('shape-stacking-drop', 'truchet-tiles', 'tessellation-triangle-flip', 'stacked-line-build',
             'tile-flip', 'pattern-tiling'),
    api=('videobuilder.techniques.particles.domino_toppling.domino_angles',),
    demo=lambda: demo.film(draw, seconds=3.2),
)
