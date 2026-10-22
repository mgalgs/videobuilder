"""Geometric loop: rings of simple polygons that turn, spin and pulse in a
travelling wave, timed so the last frame runs straight back into the first."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

TAU = 2 * math.pi
LOOP_FRAMES = round(demo.SECONDS * demo.FPS)  # the demo is one full loop, so it repeats cleanly


def polygon(cx, cy, r, sides, angle=0.0):
    """The corners of a regular polygon centred at (cx, cy), `r` from centre to
    corner, the first corner at `angle` radians (clockwise from +x)."""
    return [(cx + r * math.cos(angle + TAU * i / sides), cy + r * math.sin(angle + TAU * i / sides))
            for i in range(sides)]


def geometric_loop(cv, cx, cy, t, radius=300, rings=((6, 4), (12, 3), (18, 4)), size=None,
                   colors=(demo.ACCENT, demo.TEAL, demo.INK), core=6, alpha=1.0):
    """Draw one frame of a seamless geometric loop centred at (cx, cy) at loop
    phase `t` (only `t % 1` matters, so 0 and 1 are the same frame: drive it
    with `frame / frames_per_loop`). `rings` lists `(count, sides)` from the
    inside out, spread evenly out to `radius`; ring k carries `count` polygons
    of `sides` sides in `colors[k % len(colors)]`. Each loop every ring turns
    by exactly one slot (alternate rings the other way), every polygon spins
    by one symmetry step, and a size pulse travels once round each ring, so
    nothing jumps at the seam. `size` is the polygons' largest radius
    (default: fitted to the ring spacing); `core` draws a polygon outline of
    that many sides at the centre (0 for none). Returns the Box it covers."""
    t %= 1.0
    step = radius / max(1, len(rings))
    size = size or step * 0.42
    breathe = 0.5 - 0.5 * math.cos(TAU * t)  # 0 -> 1 -> 0 across the loop
    with cv.layer(opacity=alpha):
        if core:
            r = step * (0.35 + 0.15 * breathe)
            vb.paths.draw(cv, polygon(cx, cy, r, core, -TAU * t / core - math.pi / 2), colors[0], width=4,
                          closed=True)
        for k, (count, sides) in enumerate(rings):
            turn = (1 if k % 2 == 0 else -1) * TAU * t / count
            ring_r = step * (k + 1) * (0.94 + 0.06 * breathe)
            color = colors[k % len(colors)]
            for i in range(count):
                a = TAU * i / count + turn
                wave = 0.5 - 0.5 * math.cos(TAU * (t - i / count) * (1 if k % 2 == 0 else -1) - k * 0.9)
                spin = a + (1 if k % 2 == 0 else -1) * TAU * t / sides
                pts = polygon(cx + ring_r * math.cos(a), cy + ring_r * math.sin(a), size * (0.35 + 0.65 * wave),
                              sides, spin)
                vb.paths.draw(cv, pts, color, fill=True, alpha=0.55 + 0.45 * wave)
    outer = radius + size
    return vb.Box(cx - outer, cy - outer, 2 * outer, 2 * outer)


def draw(n, cv):
    box = geometric_loop(cv, demo.W / 2, demo.H / 2, n / LOOP_FRAMES, radius=demo.H * 0.4)
    cv.mark('loop', *box)


TECHNIQUE = Technique(
    id='geometric-loop',
    name='Geometric loop',
    family='shapes',
    group='Geometric motion',
    aliases=('looping geometric animation', 'seamless shape loop', 'geometric pattern loop'),
    definition='Simple shapes in a pattern turn, spin and pulse together in a cycle that ends exactly '
               'where it began, so it can repeat forever without a visible seam.',
    phrasings=('an endlessly repeating animation of shapes in a pattern',
               'rings of triangles and squares rotating in a perfect loop',
               'a hypnotic geometric background that loops seamlessly'),
    related=('rotating-polygon-loop', 'seamless-loop', 'shape-assemble-from-fragments', 'walk-cycle',
             'circle-packing', 'cycle-diagram-rotation'),
    api=('videobuilder.techniques.shapes.geometric_loop.geometric_loop',
         'videobuilder.techniques.shapes.geometric_loop.polygon'),
    demo=lambda: demo.film(draw),
)
