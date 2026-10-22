"""Air Drag: a falling thing speeds up, but the air pushes back harder the
faster it goes (drag ~ speed squared), so it levels off at a steady top
speed instead of accelerating forever."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def air_drag(t, terminal=360.0, gravity=720.0):
    """A fall from rest under gravity and velocity-squared drag, `t` seconds
    in, as `(distance, speed)`: speed is `terminal * tanh(gravity * t /
    terminal)`, reaching ~96% of `terminal` after two `terminal / gravity`
    time constants, and distance is its integral. Units are whatever
    `terminal` (per second) and `gravity` (per second squared) are in, e.g.
    px. Negative `t` is held at rest."""
    t = max(0.0, t)
    k = gravity / terminal
    x = k * t
    # log(cosh(x)), written so large x doesn't overflow cosh
    logcosh = x + math.log1p(math.exp(-2 * x)) - math.log(2)
    return terminal / k * logcosh, terminal * math.tanh(x)


TERMINAL, GRAVITY = 360.0, 720.0   # px/s, px/s^2: half a second to get most of the way to top speed
START = 0.3                        # s: when it's let go
TOP, FOLLOW = 70.0, demo.H / 2     # screen y it starts at; the camera tracks it once it reaches FOLLOW
RAIL, TICK = 210, 60               # ruler half-spacing from centre, and world px between ticks
R = 26


def _arrow(cv, x, y0, y1, color, width=4):
    cv.line(x, y0, x, y1, color, width=width)
    head = 9 if y1 > y0 else -9
    cv.line(x, y1, x - 7, y1 - head, color, width=width)
    cv.line(x, y1, x + 7, y1 - head, color, width=width)


def draw(n, cv):
    t = n / demo.FPS - START
    fall, speed = air_drag(t, TERMINAL, GRAVITY)
    cam = max(0.0, TOP + fall - FOLLOW)   # world -> screen: y - cam
    cx, y = demo.W / 2, TOP + fall - cam

    # rulers that scroll past once the camera follows: their pace is the speed
    first = int(cam // TICK)
    for i in range(first, first + int(demo.H // TICK) + 2):
        ty = i * TICK - cam
        for side in (-1, 1):
            cv.line(cx + side * RAIL, ty, cx + side * (RAIL - 18), ty, demo.MUTED, width=2, alpha=0.6)
    for side in (-1, 1):
        cv.line(cx + side * RAIL, 0, cx + side * RAIL, demo.H, demo.LINE, width=2)

    # where it was every 0.15 s: gaps widen, then even out at top speed
    k = 1
    while k * 0.15 < t:
        gy = TOP + air_drag(t - k * 0.15, TERMINAL, GRAVITY)[0] - cam
        if gy < -R:
            break
        demo.dot(cv, cx, gy, R * 0.45, color=demo.ACCENT, alpha=0.35 * (1 - k / 14))
        k += 1

    # gravity (constant) down on the left, drag (grows with speed squared) up on the right
    pull = 70
    _arrow(cv, cx - R - 30, y - pull / 2, y + pull / 2, demo.ACCENT)
    push = pull * (speed / TERMINAL) ** 2
    if push > 4:
        _arrow(cv, cx + R + 30, y + push / 2, y - push / 2, demo.TEAL)
    small = demo.font(20, 700)
    vb.text.draw(cv, ['gravity'], small, cx - R - 30 - vb.text.measure('gravity', small) - 14, y - 12, demo.ACCENT)
    vb.text.draw(cv, ['drag'], small, cx + R + 44, y - 12, demo.TEAL, alpha=min(1.0, push / 20))
    demo.dot(cv, cx, y, R)
    cv.mark('ball', cx - R, y - R, 2 * R, 2 * R)

    # speedometer: fills up and flattens against the terminal-speed line
    mx, my, mh = demo.W - 150, 90, 340
    cv.rect(mx, my, 26, mh, demo.LINE, radius=6)
    full = mh * 0.85
    cv.rect(mx, my + mh - full * speed / TERMINAL, 26, full * speed / TERMINAL, demo.ACCENT, radius=6)
    ty = my + mh - full
    for x in range(int(mx) - 14, int(mx) + 40, 10):
        cv.line(x, ty, x + 5, ty, demo.INK, width=2)
    vb.text.draw(cv, ['terminal', 'speed'], demo.font(18, 700), mx + 46, ty - 22, demo.INK)
    vb.text.draw(cv, ['speed'], small, mx - 10, my + mh + 14, demo.MUTED)


CAPABILITY = Capability(
    id='air-drag',
    name='Air Drag',
    family='principles',
    group='Physics',
    aliases=('aerodynamic drag', 'velocity-squared drag', 'terminal velocity', 'air resistance'),
    definition='A falling object picks up speed quickly at first, then the push of the air grows until it '
               'matches gravity and the object settles into a steady top speed.',
    phrasings=('make it fall like real air is slowing it down',
               'it should speed up and then level off at a constant falling speed',
               'drop it with air resistance so it hits terminal velocity'),
    related=('momentum-fling', 'wind-field', 'fountain', 'falling-leaves', 'smoke-simulation', 'speed-lines'),
    api=('videobuilder.capabilities.principles.air_drag.air_drag',),
    demo=lambda: demo.film(draw),
)
