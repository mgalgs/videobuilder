"""Shape Assemble from Fragments: a shape is cut into angular shards that
start scattered and tumbling, then fly in, each spinning back to its own
place, until they lock together into the whole shape."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _area(poly):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))) / 2


def _centroid(poly):
    return sum(x for x, _ in poly) / len(poly), sum(y for _, y in poly) / len(poly)


def _cut(poly, px, py, angle):
    """A convex polygon split by the line through (px, py) at `angle`: the two
    sides (either may be empty)."""
    nx, ny = -math.sin(angle), math.cos(angle)
    side = [(x - px) * nx + (y - py) * ny for x, y in poly]
    left, right = [], []
    for i, (a, da) in enumerate(zip(poly, side)):
        b, db = poly[(i + 1) % len(poly)], side[(i + 1) % len(poly)]
        (left if da >= 0 else right).append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db)
            hit = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            left.append(hit)
            right.append(hit)
    return left, right


def shatter(polygons, pieces=24, seed=0):
    """Cut convex `polygons` (each a list of (x, y) points; pass several to
    build a non-convex shape) into about `pieces` angular shards, always
    splitting the largest shard across a random line near its middle. The
    same `seed` gives the same shards."""
    rng = random.Random(seed)
    shards = [list(p) for p in polygons]
    while len(shards) < pieces:
        shards.sort(key=_area)
        big = shards.pop()
        cx, cy = _centroid(big)
        r = math.sqrt(_area(big)) * 0.2
        a, b = _cut(big, cx + rng.uniform(-r, r), cy + rng.uniform(-r, r), rng.uniform(0, math.pi))
        shards += [s for s in (a, b) if len(s) >= 3]
    return shards


def scatter(shards, center, seed=0, spread=520.0, spin=2.5, stagger=0.45):
    """A start pose for each shard: `(dx, dy, turn, delay)`. Each starts pushed
    away from `center` along its own direction (by about `spread` px, jittered;
    an (x, y) pair spreads wider than tall),
    turned by up to `spin` radians, and waits `delay` (0 -> `stagger`, inner
    shards first) of the assembly before it moves."""
    rng = random.Random(seed)
    cx, cy = center
    ex, ey = spread if isinstance(spread, (tuple, list)) else (spread, spread)
    far = max(math.hypot(_centroid(s)[0] - cx, _centroid(s)[1] - cy) for s in shards) or 1.0
    poses = []
    for s in shards:
        sx, sy = _centroid(s)
        ang = math.atan2(sy - cy, sx - cx) + rng.uniform(-0.6, 0.6)
        dist = rng.uniform(0.7, 1.3)
        delay = stagger * (0.6 * math.hypot(sx - cx, sy - cy) / far + 0.4 * rng.random())
        poses.append((math.cos(ang) * dist * ex, math.sin(ang) * dist * ey, rng.uniform(-spin, spin), delay))
    return poses


def draw_assembly(cv, shards, poses, p, color, ease=vb.ease_out_quint, shade=0.18, seed=0, whole=()):
    """Draw `shards` assembling at progress `p` (0 scattered -> 1 whole): each
    flies from its `scatter` pose to its place over the part of `p` after its
    delay. Until they land, shards are shaded lighter or darker by up to
    `shade` so the cuts read. Pass the uncut polygons as `whole` to fade them
    in over the last few percent, so no hairline seams are left at 1."""
    rng = random.Random(seed)
    c = cv.ctx
    r, g, b, _ = vb.canvas.rgba(color)
    for s, (dx, dy, turn, delay) in zip(shards, poses):
        k = 1 - ease(vb.clamp01((p - delay) / (1 - delay)))   # 1 at the start pose, 0 in place
        tone = rng.uniform(-shade, shade) * min(1.0, k * 4 + (1 - vb.clamp01((p - 0.9) / 0.1)) * 0.6)
        mix = (lambda v: v + (1 - v) * tone) if tone > 0 else (lambda v: v * (1 + tone))
        cx, cy = _centroid(s)
        c.save()
        c.translate(cx + dx * k, cy + dy * k)
        c.rotate(turn * k)
        c.new_path()
        for i, (x, y) in enumerate(s):
            (c.line_to if i else c.move_to)(x - cx, y - cy)
        c.close_path()
        c.set_source_rgba(mix(r), mix(g), mix(b))
        c.fill_preserve()
        c.set_line_width(1.0)   # hairline in the same colour hides anti-aliasing seams once landed
        c.stroke()
        c.restore()
    seal = vb.clamp01((p - 0.94) / 0.06)
    for poly in whole if seal > 0 else ():
        c.new_path()
        for i, (x, y) in enumerate(poly):
            (c.line_to if i else c.move_to)(x, y)
        c.close_path()
        c.set_source_rgba(r, g, b, seal)
        c.fill()


def _hexagon(cx, cy, r):
    return [(cx + r * math.cos(math.pi / 6 + i * math.pi / 3), cy + r * math.sin(math.pi / 6 + i * math.pi / 3))
            for i in range(6)]


CENTER = (demo.W / 2, demo.H / 2)
SHAPE = [_hexagon(*CENTER, 170)]
SHARDS = shatter(SHAPE, pieces=26, seed=3)
POSES = scatter(SHARDS, CENTER, seed=3, spread=(330, 85))


def draw(n, cv):
    draw_assembly(cv, SHARDS, POSES, demo.phase(n, 0.35, 2.5), demo.ACCENT, seed=3, whole=SHAPE)
    cv.mark('shape', CENTER[0] - 170, CENTER[1] - 170, 340, 340)


CAPABILITY = Capability(
    id='shape-assemble-from-fragments',
    name='Shape assemble from fragments',
    family='shapes',
    group='Shape morphing',
    aliases=('shard assembly', 'fragment assemble', 'reverse shatter', 'pieces fly together'),
    definition='Broken shards of a shape start scattered and spinning, then fly inward and snap '
               'into place until the shape stands whole.',
    phrasings=('the logo builds itself out of flying broken pieces',
               'a reverse shatter where the shards come back together',
               'scattered fragments spin in and lock into one shape'),
    related=('geometric-loop', 'particle-swarm-assemble', 'isometric-assembly', 'polygon-subdivision',
             'voxel-build', 'exploded-view'),
    api=('videobuilder.capabilities.shapes.shape_assemble_from_fragments.draw_assembly',
         'videobuilder.capabilities.shapes.shape_assemble_from_fragments.shatter',
         'videobuilder.capabilities.shapes.shape_assemble_from_fragments.scatter'),
    demo=lambda: demo.film(draw),
)
