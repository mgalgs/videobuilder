"""Particle swarm assemble: a field of small dots scattered over the frame
drifts in, each on its own slightly curved path and its own clock, and settles
onto the outline of a shape."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def outline_targets(points, n, seed=0, spread=6.0, closed=True):
    """`n` resting places for a swarm along the outline `points`: evenly spaced
    by arc length (`vb.paths.resample`), each nudged up to `spread` px off the
    line so the outline reads as a band of dots, not a drawn stroke."""
    rnd = random.Random(f'targets:{seed}')
    out = []
    for x, y in vb.paths.resample(points, n, closed=closed):
        a, r = rnd.uniform(0, 2 * math.pi), spread * math.sqrt(rnd.random())
        out.append((x + r * math.cos(a), y + r * math.sin(a)))
    return out


def swarm(targets, p, bounds, seed=0, stagger=0.45, curve=0.35, ease=vb.ease_out_quint):
    """Where each dot of a swarm is at progress `p` (0 -> 1), as `(x, y, arrived)`
    triples, one per target. At 0 each dot sits at a seeded random spot inside
    `bounds` (x, y, w, h); it sets off at its own time within the first
    `stagger` of the move and lands on its target by 1, along a path bowed
    sideways by up to `curve` of its length. `arrived` runs 0 -> 1 with the
    dot's own eased progress. The same `seed` gives the same swarm, frame for frame."""
    bx, by, bw, bh = bounds
    rnd = random.Random(f'swarm:{seed}')
    out = []
    for tx, ty in targets:
        sx, sy = bx + rnd.random() * bw, by + rnd.random() * bh
        delay = rnd.random() * stagger
        bow = rnd.uniform(-curve, curve)
        q = ease(vb.clamp01((p - delay) / (1 - delay)))
        dx, dy = tx - sx, ty - sy
        side = bow * q * (1 - q) * 4  # 0 at both ends, widest halfway
        out.append((sx + dx * q - dy * side, sy + dy * q + dx * side, q))
    return out


def draw_swarm(cv, targets, p, bounds, colors=(demo.ACCENT,), r=2.2, seed=0, **kw):
    """Draw the swarm at progress `p`: each dot in one of `colors` (picked by
    seed), dim while it is drifting and full strength once it lands. `kw` goes
    to `swarm`. Returns the Box around the targets."""
    rnd = random.Random(f'colors:{seed}')
    for x, y, q in swarm(targets, p, bounds, seed=seed, **kw):
        demo.dot(cv, x, y, r, color=rnd.choice(colors), alpha=0.45 + 0.55 * q)
    xs, ys = [x for x, _ in targets], [y for _, y in targets]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def star(cx, cy, outer, inner, points=5):
    """The outline of a `points`-pointed star centred at (cx, cy), tip up."""
    out = []
    for k in range(points * 2):
        a = -math.pi / 2 + k * math.pi / points
        rad = outer if k % 2 == 0 else inner
        out.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return out


TARGETS = outline_targets(star(demo.W / 2, demo.H / 2 + 14, 220, 92), 420, seed=3, spread=3.5)


def draw(n, cv):
    box = draw_swarm(cv, TARGETS, demo.phase(n, 0.25, 2.5), (0, 0, demo.W, demo.H),
                     colors=(demo.ACCENT, demo.ACCENT, demo.TEAL, demo.INK), seed=3)
    cv.mark('shape', *box)


CAPABILITY = Capability(
    id='particle-swarm-assemble',
    name='Particle swarm assemble',
    family='shapes',
    group='Bursts & particles',
    aliases=('particles form shape', 'particle logo build', 'particle logo reveal', 'scattered dots converge',
             'dot matrix form'),
    definition='Many tiny dots spread across the frame drift together, each arriving in its own time, '
               'until they settle along the outline of a shape or logo.',
    phrasings=('scattered dots fly in and gather into the logo',
               'a cloud of particles comes together to form the shape',
               'the outline builds itself out of hundreds of little dots'),
    related=('particle-text-formation', 'shape-assemble-from-fragments', 'image-to-particles', 'particle-morph',
             'animated-sprite-particles', 'dot-density-map'),
    api=('videobuilder.capabilities.shapes.particle_swarm_assemble.swarm',
         'videobuilder.capabilities.shapes.particle_swarm_assemble.draw_swarm',
         'videobuilder.capabilities.shapes.particle_swarm_assemble.outline_targets'),
    demo=lambda: demo.film(draw),
)
