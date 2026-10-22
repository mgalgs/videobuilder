"""Recoil: something fires or is struck, jerks backwards in a few frames, then
eases home to where it stood, with a small forward overshoot as it lands."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def recoil(t, kick=0.08, ratio=0.55, hz=2.2):
    """Displacement 0 -> 1 -> 0 at `t` seconds since the shot or hit: 1 is the
    furthest point back. The kick reaches it in `kick` seconds, decelerating;
    from there a damped spring (`ratio`, `hz`, as in `vb.damped`) pulls it
    home, dipping a little below 0 (a forward overshoot) when `ratio` < 1.
    0 before the hit. Multiply by the distance and the direction it is pushed:
    `x = rest_x - 40 * recoil((n - shot_frame) / fps)`."""
    if t <= 0:
        return 0.0
    if t < kick:
        return 1 - (1 - t / kick) ** 3
    return 1 - vb.spring(t - kick, **vb.damped(ratio, hz))


SHOTS = (0.6, 1.8)            # seconds the gun fires
BACK = 110                    # px it is pushed back at the furthest
REST_X, Y, GROUND = demo.W / 2 - 260, demo.H / 2, demo.H / 2 + 95


def gun(cv, x):
    """A squat body with a barrel pointing right, its body centred at x."""
    cv.rect(x - 90, Y - 60, 180, 120, demo.ACCENT, radius=22)
    cv.rect(x + 60, Y - 20, 110, 40, demo.ACCENT, radius=8)
    cv.rect(x - 70, Y - 34, 70, 14, demo.INK, radius=7, alpha=0.9)
    cv.mark('gun', x - 90, Y - 60, 260, 120)


def draw(n, cv):
    t = n / demo.FPS
    off = sum(recoil(t - s) for s in SHOTS)
    x = REST_X - BACK * off
    demo.floor(cv, GROUND, color=demo.LINE)
    cv.line(REST_X, GROUND - 14, REST_X, GROUND + 14, demo.MUTED, width=3)  # where it stands at rest
    cv.outline(REST_X - 90, Y - 60, 180, 120, demo.MUTED, width=2, radius=22, alpha=0.5)
    muzzle = REST_X + 170
    for s in SHOTS:
        k = t - s
        if 0 <= k < 0.12:                       # muzzle flash: short rays off the barrel
            a = 1 - k / 0.12
            for ang in (-0.6, 0, 0.6):
                r0, r1 = 26, 26 + 60 * a
                cv.line(muzzle + r0 * math.cos(ang), Y + r0 * math.sin(ang),
                        muzzle + r1 * math.cos(ang), Y + r1 * math.sin(ang), demo.INK, width=5, alpha=a)
        if 0 <= k < 1.0:                        # the round, flying off to the right
            px = muzzle + 30 + 2200 * k
            if px < demo.W + 40:
                demo.dot(cv, px, Y, 18, color=demo.TEAL)
    gun(cv, x)


CAPABILITY = Capability(
    id='recoil',
    name='Recoil',
    family='principles',
    group='Physics',
    aliases=('kickback', 'kick', 'rebound from impact'),
    definition='At the moment it fires or takes a hit, the object snaps backwards a short way, '
               'then glides back to its starting spot.',
    phrasings=('make it kick back when it shoots',
               'it should jolt backwards from the hit and then settle back',
               'give the cannon some kick when it fires'),
    related=('impact-shake', 'momentum-fling', 'spring-return', 'bounce-ease-out', 'bounce-ease-in',
             'impact-hit'),
    api=('videobuilder.capabilities.principles.recoil.recoil',),
    demo=lambda: demo.film(draw),
)
