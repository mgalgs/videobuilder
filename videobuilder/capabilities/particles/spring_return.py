"""Spring return: particles knocked out of place by a force are tied to their
home positions by springs, so each one flies off, swings back past home and
wobbles to rest exactly where it started."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def push(home, center, strength=120.0, radius=420.0):
    """The offset `(dx, dy)` a radial push from `center` gives a particle at
    `home`: straight away from the centre, `strength` px at the centre and
    fading smoothly to nothing about `radius` px out."""
    dx, dy = home[0] - center[0], home[1] - center[1]
    d = math.hypot(dx, dy)
    if d < 1e-6:
        return 0.0, 0.0
    k = strength * math.exp(-(d / radius) ** 2)
    return dx / d * k, dy / d * k


def spring_return(home, offset, t, kick=0.12, ratio=0.3, hz=1.6):
    """Where a particle is `t` seconds after it was knocked by `offset`: at
    `home` before the hit, out to `home + offset` over `kick` seconds, then
    pulled back by a spring at damping `ratio` and `hz` (see `vb.damped`),
    overshooting home and settling on it. Closed form, so any frame stands
    alone; stagger `t` per particle to make a hit travel through a field."""
    if t <= 0:
        return home
    if t < kick:
        k = vb.ease_out_expo(t / kick)
    else:
        k = 1 - vb.spring(t - kick, **vb.damped(ratio, hz=hz))
    return home[0] + offset[0] * k, home[1] + offset[1] * k


COLS, ROWS, GAP = 23, 13, 38
SPEED = 700.0  # each shock ring travels SPEED px/s from its centre
# (seconds, centre offset from the middle, strength): a hit in the middle, then a
# second one right of centre while the field is at rest, so the wobble is still
# going at the poster frame and has settled again before the clip ends
HITS = ((0.35, (0, 0), 70), (1.5, (220, -40), 60))


def draw(n, cv):
    t = n / demo.FPS
    cx, cy = demo.W / 2, demo.H / 2
    x0, y0 = cx - (COLS - 1) * GAP / 2, cy - (ROWS - 1) * GAP / 2
    centres = [(cx + ox, cy + oy) for _, (ox, oy), _ in HITS]
    for (hit, _, _), (hx, hy) in zip(HITS, centres):
        ring = (t - hit) * SPEED
        if 0 < ring < 450:
            cv.arc(hx, hy, ring, 0, 2 * math.pi, demo.ACCENT, width=4, alpha=0.6 * (1 - ring / 450))
    for j in range(ROWS):
        for i in range(COLS):
            home = (x0 + i * GAP, y0 + j * GAP)
            x, y = home
            # springs are linear, so the two hits' displacements simply add
            for (hit, _, strength), c in zip(HITS, centres):
                off = push(home, c, strength=strength, radius=230)
                age = t - hit - math.hypot(home[0] - c[0], home[1] - c[1]) / SPEED
                px, py = spring_return(home, off, age, ratio=0.35, hz=1.4)
                x, y = x + px - home[0], y + py - home[1]
            far = vb.clamp01(math.hypot(x - home[0], y - home[1]) / 30)
            demo.dot(cv, *home, r=2, color=demo.LINE)
            demo.dot(cv, x, y, r=5 + 2 * far, color=demo.ACCENT if far > 0.25 else demo.TEAL)
    cv.mark('field', x0, y0, (COLS - 1) * GAP, (ROWS - 1) * GAP)


CAPABILITY = Capability(
    id='spring-return',
    name='Spring return',
    family='particles',
    group='Forces',
    aliases=('elastic return', 'spring back', 'return to origin', 'rubber band particles'),
    definition='Particles shoved out of position by a force swing back toward where they started, '
               'overshoot it and wobble to a stop as if each were tethered to its spot by a spring.',
    phrasings=('the dots get blown apart and then snap back into place',
               'a grid that ripples out from a hit and wobbles back to rest',
               'particles that bounce back home elastically after being pushed'),
    related=('spring-motion', 'recoil', 'overdamped-spring', 'springs-network', 'spring-drag-letters',
             'underdamped-spring'),
    api=('videobuilder.capabilities.particles.spring_return.spring_return',
         'videobuilder.capabilities.particles.spring_return.push',
         'videobuilder.spring'),
    demo=lambda: demo.film(draw),
)
