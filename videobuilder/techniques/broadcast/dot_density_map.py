"""Dot density map: a map whose regions fill with small dots, one dot for every
fixed number of something (people, homes, votes), scattered at random inside
the region they count. Busy places come out dense and dark with dots, empty
ones stay sparse, and two colours of dot show a mix at a glance."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def inside(poly, x, y):
    """Whether (x, y) lies inside the polygon `poly` (a list of (x, y)), by
    the even-odd rule."""
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def scatter(poly, count, seed=0):
    """`count` points spread uniformly at random inside the polygon `poly`,
    by rejection from its bounding box. The same `seed` gives the same points."""
    rng = random.Random(seed)
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    out, tries = [], 0
    while len(out) < count and tries < count * 200:
        tries += 1
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if inside(poly, x, y):
            out.append((x, y))
    return out


def dot_density(regions, unit, seed=0):
    """The dots of a dot density map. `regions` is a list of `(poly, counts)`,
    `counts` a dict `{category: amount}`; each region gets `round(amount / unit)`
    dots per category, scattered inside its polygon. Returns a list of
    `(x, y, category, order)`, `order` a random 0 -> 1 rank across all dots
    (use it to stagger their appearance), the categories shuffled together."""
    dots = []
    for i, (poly, counts) in enumerate(regions):
        for cat, amount in sorted(counts.items()):
            dots += [(x, y, cat) for x, y in scatter(poly, round(amount / unit), seed=f'{seed}:{i}:{cat}')]
    rng = random.Random(seed)
    rng.shuffle(dots)
    n = max(1, len(dots) - 1)
    return [(x, y, cat, k / n) for k, (x, y, cat) in enumerate(dots)]


def draw_dot_density_map(cv, regions, dots, p, colors, r=3.0, border=demo.LINE, land=None,
                         spread=0.8, ease=vb.ease_out_back, alpha=0.9):
    """Draw a dot density map at progress `p` (0 -> 1): the region outlines
    from `regions` (as given to `dot_density`), filled with `land` if given,
    then `dots` (from `dot_density`) popping in, each in `colors[category]`
    at radius `r`. Dot `order` k starts at `k * spread` of the way through and
    grows to full size by `k * spread + (1 - spread)`, so all are in at `p = 1`."""
    c = cv.ctx
    for poly, _ in regions:
        c.new_path()
        c.move_to(*poly[0])
        for pt in poly[1:]:
            c.line_to(*pt)
        c.close_path()
        if land is not None:
            c.set_source_rgba(*vb.rgba(land))
            c.fill_preserve()
        c.set_source_rgba(*vb.rgba(border))
        c.set_line_width(2)
        c.stroke()
    grow = max(1e-6, 1 - spread)
    by_cat = {}
    for x, y, cat, k in dots:
        q = vb.clamp01((p - k * spread) / grow)
        if q > 0:
            by_cat.setdefault(cat, []).append((x, y, r * max(0.0, ease(q))))
    # One path per colour: thousands of dots stay cheap to fill.
    for cat, pts in by_cat.items():
        c.new_path()
        for x, y, rr in pts:
            c.new_sub_path()
            c.arc(x, y, rr, 0, 2 * math.pi)
        c.set_source_rgba(*vb.rgba(colors[cat], alpha))
        c.fill()


def _provinces(cols=6, rows=3, x=170, y=50, w=620, h=370, seed=4):
    """A made-up country: a jittered lattice cut into quad provinces sharing
    borders, a few corners dropped for an uneven coastline. Each province's
    counts fall off from a 'city' at the lattice's upper middle."""
    rng = random.Random(seed)
    pts = [[(x + w * i / cols + (rng.uniform(-20, 20) if 0 < i < cols else 0),
             y + h * j / rows + (rng.uniform(-20, 20) if 0 < j < rows else 0))
            for i in range(cols + 1)] for j in range(rows + 1)]
    drop = {(0, 0), (cols - 1, rows - 1), (0, rows - 1)}
    city = (x + w * 0.58, y + h * 0.4)
    out = []
    for j in range(rows):
        for i in range(cols):
            if (i, j) in drop:
                continue
            poly = [pts[j][i], pts[j][i + 1], pts[j + 1][i + 1], pts[j + 1][i]]
            cx, cy = sum(p[0] for p in poly) / 4, sum(p[1] for p in poly) / 4
            d = math.hypot(cx - city[0], cy - city[1]) / 140
            total = 2500 + 42000 * math.exp(-d * d)
            share = 0.25 + 0.5 * rng.random()
            out.append((poly, {'a': total * share, 'b': total * (1 - share)}))
    return out


_REGIONS = _provinces()
_DOTS = dot_density(_REGIONS, unit=100, seed=9)


def draw(n, cv):
    draw_dot_density_map(cv, _REGIONS, _DOTS, demo.phase(n, 0.3, 2.5),
                         {'a': demo.ACCENT, 'b': demo.TEAL}, r=1.8, land='#1b1d23')
    f = demo.font(15, 600)
    y = demo.H - 50
    demo.dot(cv, 186, y, r=4, color=demo.ACCENT)
    vb.text.draw(cv, ['Group A'], f, 196, y - 10, demo.INK)
    demo.dot(cv, 286, y, r=4, color=demo.TEAL)
    vb.text.draw(cv, ['Group B'], f, 296, y - 10, demo.INK)
    vb.text.draw(cv, ['1 dot = 100 people'], f, 390, y - 10, demo.MUTED)
    cv.mark('map', 170, 50, 620, 370)


TECHNIQUE = Technique(
    id='dot-density-map',
    name='Dot density map',
    family='broadcast',
    group='Maps',
    aliases=('dot distribution map', 'dot map', 'population dot map'),
    definition='A map where each small dot stands for a fixed number of things and is dropped at random '
               'inside its region, so crowded areas fill up thickly while empty ones stay sparse.',
    phrasings=('a map that fills with tiny dots, one per hundred people, so you can see where everyone lives',
               'show the population as dots scattered over the regions, two colours for the two groups',
               'dots pepper the map, thick around the city and thin in the countryside'),
    related=('halftone-dot-scaling', 'dot-grid-displacement', 'radio-dot-scale', 'bouncing-dots',
             'scatter-plot-point-appear', 'dot-matrix-text'),
    api=('videobuilder.techniques.broadcast.dot_density_map.draw_dot_density_map',
         'videobuilder.techniques.broadcast.dot_density_map.dot_density',
         'videobuilder.techniques.broadcast.dot_density_map.scatter'),
    demo=lambda: demo.film(draw),
)
