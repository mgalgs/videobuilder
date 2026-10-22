"""Koch snowflake: a triangle whose every edge sprouts a pointed bump in its
middle third, again and again, until the outline is a fine, spiky snowflake.
`level` may be fractional, so the newest bumps can push out smoothly."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def koch_step(points, bump=1.0):
    """One round of the Koch rule on the closed point list `points`: each
    edge becomes four, its middle third raised into a spike pointing out of
    a clockwise (on screen) outline. `bump` 0 -> 1 grows the spike from flat
    to a full equilateral tooth."""
    h = bump * math.sqrt(3) / 6
    out = []
    for i, (x0, y0) in enumerate(points):
        x1, y1 = points[(i + 1) % len(points)]
        dx, dy = x1 - x0, y1 - y0
        out += [(x0, y0), (x0 + dx / 3, y0 + dy / 3),
                (x0 + dx / 2 + dy * h, y0 + dy / 2 - dx * h),
                (x0 + 2 * dx / 3, y0 + 2 * dy / 3)]
    return out


def koch_snowflake(cx, cy, r, level, rotation=0.0):
    """The closed point list of a Koch snowflake centred at (cx, cy), its
    starting triangle inscribed in radius `r`, one corner pointing up (turned
    by `rotation` radians). `level` 0 is the triangle; each whole step adds
    a round of bumps, and a fractional part grows the next round part way."""
    level = max(0.0, level)
    pts = [(cx + r * math.sin(rotation + k * 2 * math.pi / 3),
            cy - r * math.cos(rotation + k * 2 * math.pi / 3)) for k in range(3)]
    whole = math.floor(level)
    for _ in range(whole):
        pts = koch_step(pts)
    if level > whole:
        pts = koch_step(pts, level - whole)
    return pts


LEVELS = 4
START, STEP = 0.4, 0.5  # level k grows in during [START + (k-1)*STEP, START + k*STEP - 0.05]


def draw(n, cv):
    level = sum(vb.ease_in_out_quart(demo.phase(n, START + k * STEP, START + (k + 1) * STEP - 0.05))
                for k in range(LEVELS))
    r = demo.H * 0.36
    cx, cy = demo.W / 2, demo.H / 2 + r * 0.08
    pts = koch_snowflake(cx, cy, r, level)
    vb.paths.draw(cv, pts, demo.ACCENT, fill=True, alpha=0.12)
    vb.paths.draw(cv, pts, demo.ACCENT, width=3, closed=True)
    demo.word(cv, f'level {min(LEVELS, math.ceil(level - 1e-6))}', demo.W / 2, demo.H - 60, size=34,
              color=demo.MUTED, font=demo.mono(34))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cv.mark('snowflake', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


TECHNIQUE = Technique(
    id='koch-snowflake',
    name='Koch snowflake',
    family='particles',
    group='Fractals',
    aliases=('Koch curve', 'Koch island', 'Koch star'),
    definition='A triangle outline that keeps pushing a small pointed tooth out of the middle of every '
               'edge, round after round, until it becomes an intricately spiky snowflake.',
    phrasings=('a triangle that grows into a snowflake fractal',
               'spikes keep sprouting out of every edge until it looks like a snowflake',
               'a fractal outline that gets more and more jagged with each step'),
    related=('superformula-morph', 'polygon-subdivision', 'marching-squares-contour', 'bend-deformer',
             'differential-growth', 'taper-deformer'),
    api=('videobuilder.techniques.particles.koch_snowflake.koch_snowflake',
         'videobuilder.techniques.particles.koch_snowflake.koch_step',
         'videobuilder.paths.draw'),
    demo=lambda: demo.film(draw),
)
