"""Speed Ramp: the playback rate of a motion eases from one speed to another
-- normal into slow motion and back up to fast -- rather than cutting between
speeds. `speed_ramp` turns film time into source time, so any animation driven
by it slows and speeds up smoothly."""
import math

from .. import _demo as demo
from ..schema import Technique


def speed_ramp(t, keys):
    """Film time `t` (seconds) -> source time: the integral of a playback speed
    that holds each `(time, speed)` key in `keys` and eases between them with
    a smoothstep, so the rate never jumps. `keys` are sorted by time; before
    the first key and after the last the speed holds.

    Drive an animation with it, e.g. `x = x0 + v * speed_ramp(n / fps, ((0.8, 1), (1.3, 0.2), (2, 0.2), (2.4, 2)))`."""
    keys = sorted(keys)
    t0, v0 = keys[0]
    src = v0 * min(t, t0)
    for (a, va), (b, vb_) in zip(keys, keys[1:]):
        if t <= a:
            break
        length = b - a
        u = min(t, b) - a
        x = u / length if length > 0 else 1.0
        src += va * u + (vb_ - va) * length * (x ** 3 - x ** 4 / 2)  # integral of smoothstep
    tn, vn = keys[-1]
    if t > tn:
        src += vn * (t - tn)
    return src


def speed_at(t, keys):
    """The playback speed `speed_ramp` uses at film time `t`."""
    keys = sorted(keys)
    if t <= keys[0][0]:
        return keys[0][1]
    for (a, va), (b, vb_) in zip(keys, keys[1:]):
        if t <= b:
            x = (t - a) / (b - a) if b > a else 1.0
            return va + (vb_ - va) * x * x * (3 - 2 * x)
    return keys[-1][1]


KEYS = ((0.0, 1.6), (0.6, 1.6), (1.1, 0.1), (1.8, 0.1), (2.3, 1.6), (3.0, 1.6))
TOP = 1.6
R = 30
LEFT, RIGHT = 90 + R, demo.W - 90 - R
LANE = 250


def _x(t):
    return LEFT + (RIGHT - LEFT) * speed_ramp(t, KEYS) / speed_ramp(demo.SECONDS, KEYS)


def _ball(cv, x, angle, alpha=1.0):
    demo.dot(cv, x, LANE, R, alpha=alpha)
    for k in range(3):  # spokes, so the roll shows the rate too
        a = angle + k * math.pi / 3
        dx, dy = math.cos(a) * (R - 10), math.sin(a) * (R - 10)
        cv.line(x - dx, LANE - dy, x + dx, LANE + dy, demo.BG, width=4, alpha=0.55 * alpha)


def draw(n, cv):
    t = n / demo.FPS
    ground = LANE + R
    demo.floor(cv, ground + 4)
    for i in range(21):  # a ruler under the lane
        tx = LEFT - R + i * (RIGHT - LEFT + 2 * R) / 20
        cv.line(tx, ground + 4, tx, ground + (16 if i % 5 == 0 else 10), demo.MUTED, width=2, alpha=0.6)
    for k in range(5, 0, -1):  # ghosts at equal film-time steps: far apart when fast, bunched when slow
        tk = t - k * 0.06
        if tk >= 0:
            _ball(cv, _x(tk), _x(tk) / R, alpha=0.32 * (1 - k / 6))
    x = _x(t)
    _ball(cv, x, x / R)
    cv.mark('ball', x - R, LANE - R, 2 * R, 2 * R)

    # the speed curve, with a playhead: the ramp itself, drawn
    gx, gy, gw, gh, top = 240, demo.H - 40, demo.W - 480, 110, TOP * 1.1
    cv.line(gx, gy, gx + gw, gy, demo.LINE, width=2)
    py = lambda v: gy - gh * v / top  # noqa: E731
    cv.line(gx, py(1), gx + gw, py(1), demo.LINE, width=1, alpha=0.6)
    steps = 120
    for i in range(steps):
        a, b = demo.SECONDS * i / steps, demo.SECONDS * (i + 1) / steps
        cv.line(gx + gw * a / demo.SECONDS, py(speed_at(a, KEYS)), gx + gw * b / demo.SECONDS,
                py(speed_at(b, KEYS)), demo.TEAL if b <= t else demo.MUTED, width=3)
    v = speed_at(t, KEYS)
    hx = gx + gw * t / demo.SECONDS
    cv.line(hx, gy, hx, gy - gh, demo.INK, width=2, alpha=0.7)
    demo.dot(cv, hx, py(v), 7, color=demo.INK)
    demo.word(cv, f'{v:.1f}×', demo.W / 2, 110, size=64, font=demo.mono(64))
    demo.word(cv, 'speed', gx - 40, py(1), size=18, color=demo.MUTED, weight=600)


TECHNIQUE = Technique(
    id='speed-ramp',
    name='Speed Ramp',
    family='principles',
    group='Time remapping',
    aliases=('time remap', 'velocity ramp', 'ramp cut', 'variable speed', 'slow-motion ramp'),
    definition='A shot whose playback rate glides between speeds, sinking into slow motion and '
               'then surging fast again, instead of switching speed in one jump.',
    phrasings=('slow it down to slow-mo in the middle and then speed it back up',
               'ramp the speed so it eases into slow motion',
               'make the action go fast, then slow, then fast again, smoothly'),
    related=('steps-easing', 'speed-lines', 'velocity-preserving-retarget', 'linear-easing',
             'animated-gradient-sweep', 'distance-based-duration'),
    api=('videobuilder.techniques.principles.speed_ramp.speed_ramp',
         'videobuilder.techniques.principles.speed_ramp.speed_at'),
    demo=lambda: demo.film(draw),
)
