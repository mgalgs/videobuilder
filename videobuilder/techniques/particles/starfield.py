"""Starfield: points of light scattered through depth stream outward from a
vanishing point, as if the camera flies forward through space; the faster the
flight, the longer each star's streak."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

NEAR, FAR = 0.05, 1.0


def stars(count=320, seed=0):
    """`count` seeded stars as `(x, y, z)`: x and y in -1..1 across the frame,
    z in 0..1 their starting place in the depth loop."""
    rnd = random.Random(seed)
    return [(rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.random()) for _ in range(count)]


def draw_starfield(cv, travel, field=None, streak=0.0, cx=None, cy=None, color='#ffffff', size=2.2,
                   focal=None):
    """Draw a forward-flying starfield on `cv` after flying `travel` depths
    (each star loops from far to near once per unit of travel, so feed it a
    running total -- e.g. the integral of an eased speed -- to speed up or
    slow down smoothly). `streak` is how far back along its path each star
    trails, in the same units: 0 gives dots, ~0.05 gives warp-speed lines.
    `field` comes from `stars()`; (cx, cy) is the vanishing point (default the
    centre); `size` is a near star's radius in pixels at scale 1. Nearer stars
    are brighter and bigger; far ones fade in so nothing pops."""
    field = stars() if field is None else field
    w, h = cv.width, cv.height
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    focal = focal or max(w, h) * 0.5
    span = FAR - NEAR
    for x, y, z0 in field:
        z = NEAR + span * ((z0 - travel) % 1.0)
        near = 1 - (z - NEAR) / span                      # 0 far .. 1 near
        alpha = vb.clamp01(near * 4) * (0.5 + 0.5 * near)
        hx, hy = cx + x / z * focal, cy + y / z * focal
        if not (-50 < hx < w + 50 and -50 < hy < h + 50):
            continue
        r = max(0.6, size * (0.3 + 1.2 * near * near))
        if streak > 0:
            zt = min(FAR, z + streak)
            tx, ty = cx + x / zt * focal, cy + y / zt * focal
            cv.line(tx, ty, hx, hy, color, width=r * 1.4, alpha=alpha)
        cv.sector(hx, hy, r, 0, 2 * math.pi, color, alpha=alpha)


# Demo: cruise past drifting dots, then punch up to warp speed and streak.
FIELD = stars(900, seed=11)


def _speed(t):
    """Depths per second at time t: a slow cruise, then a ramp into warp."""
    return 0.18 + 1.4 * vb.ease_in_out_quart(vb.clamp01((t - 0.9) / 1.3))


def _travel(t, steps=60):
    dt = t / steps
    return sum(_speed((i + 0.5) * dt) for i in range(steps)) * dt


def draw(n, cv):
    t = n / demo.FPS
    v = _speed(t)
    draw_starfield(cv, _travel(t), FIELD, streak=0.08 * (v - 0.18) / 1.4 + 0.004, color=demo.INK)


TECHNIQUE = Technique(
    id='starfield',
    name='Starfield',
    family='particles',
    group='Space',
    aliases=('warp speed', 'hyperspace', 'star tunnel', 'flying through stars'),
    definition='Stars spread through depth rush out from a central point toward the edges of the frame, '
               'growing brighter as they near and stretching into streaks as the speed rises.',
    phrasings=('make it look like we are flying through space past the stars',
               'stars zooming toward the camera like jumping to light speed',
               'a space background where the stars streak outward from the middle'),
    related=('diffraction-spikes', 'flow-field', 'shape-burst', 'star-rating-fill', 'dot-grid-displacement',
             'turbulence-displacement'),
    api=('videobuilder.techniques.particles.starfield.draw_starfield',
         'videobuilder.techniques.particles.starfield.stars'),
    demo=lambda: demo.film(draw),
)
