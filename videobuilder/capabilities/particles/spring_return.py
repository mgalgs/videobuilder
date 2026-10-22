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
HIT, SPEED = 0.4, 700.0  # the shock leaves the centre at HIT seconds and travels SPEED px/s


def draw(n, cv):
    t = n / demo.FPS
    cx, cy = demo.W / 2, demo.H / 2
    x0, y0 = cx - (COLS - 1) * GAP / 2, cy - (ROWS - 1) * GAP / 2
    ring = (t - HIT) * SPEED
    if 0 < ring < demo.W:
        cv.arc(cx, cy, ring, 0, 2 * math.pi, demo.ACCENT, width=4, alpha=max(0.0, 0.6 * (1 - ring / 450)))
    for j in range(ROWS):
        for i in range(COLS):
            home = (x0 + i * GAP, y0 + j * GAP)
            off = push(home, (cx, cy), strength=70, radius=230)
            age = t - HIT - math.hypot(home[0] - cx, home[1] - cy) / SPEED
            x, y = spring_return(home, off, age, hz=1.2)
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
