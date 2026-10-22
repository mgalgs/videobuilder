"""Particle morph: a solid shape made of hundreds of dots flows, dot by dot,
into a different solid shape, the cloud swirling as it goes.

Each silhouette is filled with the same number of evenly spread points
(`fill_points`); `match` pairs the two clouds ring by ring and angle by
angle, so neighbours stay neighbours and the cloud flows rather than
scrambles; `morph_points` moves every pair along a swirling path, each dot on
a slightly different clock."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Technique


def _inside(x, y, poly):
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def fill_points(poly, n, seed=0):
    """`n` points spread evenly over the inside of the closed polygon `poly`
    (a list of (x, y)), from a seeded low-discrepancy sequence across its
    bounding box, so the fill looks even with no clumps or grid lines."""
    poly = list(poly)
    xs, ys = [x for x, _ in poly], [y for _, y in poly]
    x0, y0, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    g = 1.32471795724474602596  # the plastic number: the R2 sequence
    a1, a2 = 1 / g, 1 / (g * g)
    off = random.Random(f'fill:{seed}').random()
    out, i = [], 0
    while len(out) < n and i < n * 400:
        i += 1
        x, y = x0 + ((off + a1 * i) % 1) * w, y0 + ((off + a2 * i) % 1) * h
        if _inside(x, y, poly):
            out.append((x, y))
    return out


def _polar(points, rings):
    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    far = max(math.hypot(x - cx, y - cy) for x, y in points) or 1
    keyed = [(min(int(math.hypot(x - cx, y - cy) / far * rings), rings - 1),
              math.atan2(y - cy, x - cx), (x, y)) for x, y in points]
    return [pt for *_, pt in sorted(keyed)]


def match(a, b, rings=12):
    """`a` and `b` (equal-length point lists) reordered so the i-th points
    pair up: both sorted by ring (distance from their own centre, in `rings`
    bands) and then by angle. Inner points go to inner points and the left
    side to the left side, so a morph between them flows as one cloud."""
    if len(a) != len(b):
        raise ValueError(f'match: point lists differ in length ({len(a)} vs {len(b)})')
    return _polar(a, rings), _polar(b, rings)


def morph_points(a, b, p, seed=0, stagger=0.3, swirl=1.4, scatter=16.0, ease=vb.ease_in_out_quart):
    """Where each dot is at progress `p` (0 -> 1) of a morph from points `a`
    to the paired points `b` (see `match`), as `(x, y, t)` triples where `t`
    is the dot's own eased progress. Each dot sets off at its own time within
    the first `stagger` of the move; mid-flight the cloud turns by up to
    `swirl` radians about the midpoint of the two centres and each dot strays
    up to `scatter` px, both gone again on landing. The same `seed` gives the
    same motion, frame for frame."""
    cx = (sum(x for x, _ in a) + sum(x for x, _ in b)) / (2 * len(a))
    cy = (sum(y for _, y in a) + sum(y for _, y in b)) / (2 * len(a))
    rnd = random.Random(f'morph:{seed}')
    out = []
    for (ax, ay), (bx, by) in zip(a, b):
        delay = rnd.random() * stagger
        ang, k = rnd.uniform(0, 2 * math.pi), rnd.random()
        t = ease(vb.clamp01((p - delay) / (1 - delay)))
        x, y = ax + (bx - ax) * t, ay + (by - ay) * t
        bell = 4 * t * (1 - t)  # 0 at both ends, 1 halfway
        turn = swirl * bell
        dx, dy = x - cx, y - cy
        x = cx + dx * math.cos(turn) - dy * math.sin(turn) + scatter * k * bell * math.cos(ang)
        y = cy + dx * math.sin(turn) + dy * math.cos(turn) + scatter * k * bell * math.sin(ang)
        out.append((x, y, t))
    return out


def draw_particle_morph(cv, a, b, p, color_a=demo.TEAL, color_b=None, r=2.2, seed=0, **kw):
    """Draw the cloud morphing from points `a` to points `b` (already paired
    with `match`) at progress `p`, each dot shading from `color_a` to
    `color_b` (default: no change) as it travels. `kw` goes to
    `morph_points`. Returns the Box around the dots."""
    pts = morph_points(a, b, p, seed=seed, **kw)
    for x, y, t in pts:
        c = kit.mix(color_a, color_b, t) if color_b else color_a
        cv.sector(x, y, r, 0, 2 * math.pi, c)
    xs, ys = [x for x, _, _ in pts], [y for _, y, _ in pts]
    return vb.Box(min(xs) - r, min(ys) - r, max(xs) - min(xs) + 2 * r, max(ys) - min(ys) + 2 * r)


def _circle(cx, cy, rad, k=96):
    return [(cx + rad * math.cos(2 * math.pi * i / k), cy + rad * math.sin(2 * math.pi * i / k)) for i in range(k)]


def _star(cx, cy, outer, inner, tips=5):
    return [(cx + (outer if i % 2 == 0 else inner) * math.cos(-math.pi / 2 + i * math.pi / tips),
             cy + (outer if i % 2 == 0 else inner) * math.sin(-math.pi / 2 + i * math.pi / tips))
            for i in range(tips * 2)]


def _heart(cx, cy, size, k=120):
    out = []
    for i in range(k):
        t = 2 * math.pi * i / k
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        out.append((cx + x * size / 16, cy - y * size / 16 - size * 0.1))
    return out


N = 1000
CX, CY = demo.W / 2, demo.H / 2
SHAPES = None


def _shapes():
    global SHAPES
    if SHAPES is None:
        circle = fill_points(_circle(CX, CY, 150), N, seed=1)
        star = fill_points(_star(CX, CY + 12, 195, 80), N, seed=2)
        heart = fill_points(_heart(CX, CY, 165), N, seed=3)
        c1, s1 = match(circle, star)
        s2, h2 = match(star, heart)
        SHAPES = (c1, s1, s2, h2)
    return SHAPES


def draw(n, cv):
    c1, s1, s2, h2 = _shapes()
    first = demo.phase(n, 0.3, 1.4)
    if first < 1:
        box = draw_particle_morph(cv, c1, s1, first, demo.TEAL, demo.ACCENT, seed=1)
    else:
        box = draw_particle_morph(cv, s2, h2, demo.phase(n, 1.75, 2.85), demo.ACCENT, demo.INK, seed=2)
    cv.mark('cloud', *box)


TECHNIQUE = Technique(
    id='particle-morph',
    name='Particle morph',
    family='particles',
    group='Particle text & images',
    aliases=('point cloud morph', 'shape morph particles', 'particle shape morph'),
    definition='A filled shape built from hundreds of small dots swirls apart and regathers, '
               'every dot travelling to its place in a new shape.',
    phrasings=('turn the circle of dots into a star made of the same dots',
               'the particles flow from one shape into the next',
               'a dotted logo melts and reforms as a different symbol'),
    related=('shape-morph', 'projection-morph', 'liquid-morph', 'text-to-shape-morph', 'point-cloud-reveal',
             'shape-morph-loader'),
    api=('videobuilder.techniques.particles.particle_morph.draw_particle_morph',
         'videobuilder.techniques.particles.particle_morph.morph_points',
         'videobuilder.techniques.particles.particle_morph.match',
         'videobuilder.techniques.particles.particle_morph.fill_points'),
    demo=lambda: demo.film(draw),
)
