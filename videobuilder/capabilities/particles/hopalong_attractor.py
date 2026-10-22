"""Hopalong attractor: one point is pushed through Martin's square-root map
again and again, hopping across the plane; the trail of landings fills in
nested, symmetric loops of dots like a lace doily."""
import math
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


@lru_cache(maxsize=8)
def hopalong(count, a=-55.0, b=-1.0, c=-42.0, x=0.0, y=0.0):
    """The first `count` points of the Hopalong map
    x' = y - sign(x) sqrt(|b x - c|), y' = a - x, starting from (x, y), as a
    tuple of (x, y) in the map's own units. Cached, so a demo calls it every
    frame for free."""
    out = []
    for _ in range(count):
        out.append((x, y))
        x, y = y - math.copysign(math.sqrt(abs(b * x - c)), x), a - x
    return tuple(out)


def fit(points, cx, cy, w, h):
    """A function mapping map units to screen px that centres `points`' bounds
    on (cx, cy) inside a `w` x `h` box, keeping the aspect ratio."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    k = min(w / max(x1 - x0, 1e-9), h / max(y1 - y0, 1e-9))
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    return lambda x, y: (cx + (x - mx) * k, cy - (y - my) * k)


def draw_hopalong(cv, cx, cy, w, h, p, count=40000, a=-55.0, b=-1.0, c=-42.0,
                  colors=(demo.TEAL, demo.ACCENT, demo.INK), dot=2.2, trail=8, alpha=0.85):
    """Draw the Hopalong attractor built up to progress `p` (0 -> 1 of `count`
    points), fitted into the `w` x `h` box centred at (cx, cy). Dots cycle
    through `colors` in bands of iterations, so the loops read as layered
    rings. The last `trail` hops are drawn as fading lines with a head dot,
    showing the point leaping around the figure. Returns the head's (x, y)."""
    pts = hopalong(count, a, b, c)
    to = fit(pts, cx, cy, w, h)
    shown = max(1, round(count * vb.clamp01(p)))
    band = max(1, count // (len(colors) * 4))
    ctx = cv.ctx
    for ci, color in enumerate(colors):
        for start in range(ci * band, shown, band * len(colors)):
            for x, y in pts[start:min(shown, start + band)]:
                sx, sy = to(x, y)
                ctx.rectangle(sx - dot / 2, sy - dot / 2, dot, dot)
        ctx.set_source_rgba(*vb.rgba(color, alpha))
        ctx.fill()
    head = to(*pts[shown - 1])
    if 0 < p < 1 and trail:
        tail = [to(*q) for q in pts[max(0, shown - trail):shown]]
        for i in range(1, len(tail)):
            cv.line(*tail[i - 1], *tail[i], demo.ACCENT, width=2, alpha=0.15 + 0.6 * i / len(tail))
        demo.dot(cv, *head, r=12, color=demo.ACCENT, alpha=0.3)
        demo.dot(cv, *head, r=6, color=demo.ACCENT)
    return head


def draw(n, cv):
    p = demo.phase(n, 0.1, 2.6)
    draw_hopalong(cv, demo.W / 2, demo.H / 2, demo.W - 260, demo.H - 160, (1 - (1 - p) ** 1.6))


TECHNIQUE = Technique(
    id='hopalong-attractor',
    name='Hopalong attractor',
    family='particles',
    group='Strange attractors',
    aliases=('Martin attractor', 'Hopalong fractal', 'Hopalong orbit'),
    definition='A single point jumps again and again by a simple square-root rule, and the dots it leaves '
               'behind pile up into nested, mirrored loops like a lace doily.',
    phrasings=('a generative dot pattern that builds itself into a symmetric lace-like mandala',
               'show a strange attractor filling in with thousands of dots',
               'a point hopping around leaving a doily of dots behind'),
    related=('sierpinski-gasket', 'space-colonization', 'gravity-well-attraction', 'hop-cycle', 'wiggle-path',
             'circle-pop'),
    api=('videobuilder.techniques.particles.hopalong_attractor.draw_hopalong',
         'videobuilder.techniques.particles.hopalong_attractor.hopalong'),
    demo=lambda: demo.film(draw),
)
