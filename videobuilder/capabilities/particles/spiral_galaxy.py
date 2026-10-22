"""Spiral Galaxy: a swarm of star particles laid out along curved arms around
a bright core, the whole disk turning, the inner stars faster than the outer
ones."""
import math
import random

from .. import _demo as demo
from ..schema import Technique


def galaxy_stars(count, t, arms=2, wind=3.4, spin=0.45, shear=0.7, spread=0.3, haze=0.25, seed=7):
    """`count` stars of a spiral galaxy at time `t` seconds, as `(x, y, f,
    glow)` tuples: `(x, y)` an offset inside the unit disk, `f` the star's
    distance from the centre (0 core -> 1 rim) and `glow` its brightness
    0 -> 1. Most stars sit on `arms` arms, each winding `wind` radians from
    core to rim, scattered across it by `spread` (wider near the core); a
    `haze` share are loose disk stars. Every star orbits at `spin` rad/s,
    plus up to `shear` times that again towards the core, so the arms turn
    and slowly wind tighter. The same `seed` gives the same galaxy each frame."""
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        f = rng.random() ** 1.6  # crowd the centre
        if rng.random() < haze:
            a0 = rng.uniform(0, 2 * math.pi)
            glow = rng.uniform(0.15, 0.45)
        else:
            arm = rng.randrange(arms)
            a0 = 2 * math.pi * arm / arms + wind * f + rng.gauss(0, spread * (1.1 - 0.6 * f))
            f = min(1.0, max(0.0, f + rng.gauss(0, 0.03)))
            glow = rng.uniform(0.5, 1.0)
        a = a0 + spin * (1 + shear * (1 - f)) * t
        out.append((f * math.cos(a), f * math.sin(a), f, glow))
    return out


def _mix(c0, c1, k):
    a = [int(c0[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    return tuple(round(x + (y - x) * k) for x, y in zip(a, b))


def draw_spiral_galaxy(cv, cx, cy, t, radius=240, count=1400, tilt=0.8, angle=-0.35, star=2.2,
                       core='#ffd36b', rim='#b9cbff', **kw):
    """Draw a spiral galaxy of `count` stars centred at (cx, cy) at time `t`
    seconds: a soft glowing core, then the stars, coloured from `core` at
    the centre to `rim` at the edge and up to `star` px across. The disk is
    `radius` px from centre to rim, seen at a `tilt` (1 face-on, smaller flatter),
    its long axis turned `angle` radians. `kw` goes to `galaxy_stars`."""
    ctx = cv.ctx
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(angle)
    ctx.scale(1.0, tilt)
    for i in range(24):  # core glow: stacked faint discs, widest first
        k = 1 - i / 24
        demo.dot(cv, 0, 0, radius * (0.04 + 0.42 * k * k), color=core, alpha=0.016 + 0.01 * (1 - k))
    for x, y, f, glow in galaxy_stars(count, t, **kw):
        size = star * (0.55 + 0.9 * glow) * (1.25 - 0.45 * f)
        demo.dot(cv, x * radius, y * radius, size, color=_mix(core, rim, min(1.0, f * 2.2)),
                 alpha=min(1.0, glow * (1.1 - 0.4 * f)))
    demo.dot(cv, 0, 0, radius * 0.035, color='#fff6dc')
    ctx.restore()


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    draw_spiral_galaxy(cv, cx, cy, n / demo.FPS, radius=250)
    cv.mark('galaxy', cx - 250, cy - 210, 500, 420)


TECHNIQUE = Technique(
    id='spiral-galaxy',
    name='Spiral galaxy',
    family='particles',
    group='Space',
    aliases=('galaxy spiral', 'rotating disk', 'galaxy swirl'),
    definition='Thousands of tiny star dots trace curved arms out from a glowing centre, and the whole '
               'disk slowly turns, its inner stars circling faster than the outer ones.',
    phrasings=('a rotating galaxy made of particles',
               'stars swirling around a bright middle in spiral arms',
               'a slowly turning spiral of stars like the Milky Way'),
    related=('spiral-bloom', 'orbit', 'swirl', 'spiral-wipe', 'phyllotaxis', 'rotating-rings'),
    api=('videobuilder.techniques.particles.spiral_galaxy.draw_spiral_galaxy',
         'videobuilder.techniques.particles.spiral_galaxy.galaxy_stars'),
    demo=lambda: demo.film(draw),
)
