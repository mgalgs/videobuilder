"""Slow Motion: the film's clock and the action's clock come apart -- inside a
window the action plays at a fraction of its speed, eased in and out of it, so
one moment (here a bounce) stretches out and can be read."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _weight(t, start, end, ramp):
    """How far into slow motion film time `t` is: 0 outside the window, 1 in
    its middle, a smoothstep up over the first `ramp` seconds and down over the last."""
    if t <= start or t >= end:
        return 0.0
    if ramp > 0 and t < start + ramp:
        u = (t - start) / ramp
        return u * u * (3 - 2 * u)
    if ramp > 0 and t > end - ramp:
        u = (end - t) / ramp
        return u * u * (3 - 2 * u)
    return 1.0


def slow_motion_rate(t, start, end, rate=0.25, ramp=0.2):
    """Playback speed at film time `t` (seconds) for `slow_motion` with the same
    arguments: 1 outside the window, `rate` inside it, eased between."""
    ramp = max(0.0, min(ramp, (end - start) / 2))
    return 1 - (1 - rate) * _weight(t, start, end, ramp)


def slow_motion(t, start, end, rate=0.25, ramp=0.2):
    """Film time `t` (seconds) -> action time (seconds): real speed before
    `start` and after `end`, `rate` x speed in between, with `ramp`-second
    smoothstep speed changes at each edge so it slows down and speeds back up
    rather than snapping. Monotonic, and continuous in both time and speed.

    In a film, drive the action from the remapped clock, e.g.
    `s = slow_motion(n / fps, 1.0, 2.0, rate=0.2)` and then pose everything at
    action time `s`. `slow_motion(end_of_film, ...)` says how much action fits."""
    ramp = max(0.0, min(ramp, (end - start) / 2))

    def ease_area(u):  # integral of smoothstep from 0 to u
        return u ** 3 - u ** 4 / 2

    lost = 0.0  # seconds of slowness accumulated so far, at full slowness
    if t > start:
        if ramp > 0:
            lost += ramp * ease_area(vb.clamp01((t - start) / ramp))
        lost += min(max(t - start - ramp, 0.0), end - start - 2 * ramp)
        if ramp > 0:
            u = vb.clamp01((t - end + ramp) / ramp)
            lost += ramp * (u - ease_area(u))
    return t - (1 - rate) * lost


# the demo: a ball bounces across the floor and the bounce plays in slow motion
WINDOW = dict(start=0.85, end=2.15, rate=0.15, ramp=0.35)
R, GROUND = 34, demo.H - 110
X0, X1, TOP = 150, demo.W - 150, 110
TRAIL, GAP = 7, 2  # ghosts left every GAP film frames: wide apart at full speed, bunched in slow motion


def _ball_at(film_t):
    """The ball's (x, y, squash) at film time `film_t`."""
    total = slow_motion(demo.SECONDS, **WINDOW)
    hit = slow_motion((WINDOW['start'] + WINDOW['end']) / 2, **WINDOW)
    s = slow_motion(max(0.0, film_t), **WINDOW)
    x = X0 + (X1 - X0) * s / total
    rest = GROUND - R
    reach = max(hit, total - hit)
    k = (s - hit) / reach
    y = rest - (rest - TOP) * k * k
    squash = max(0.0, 1 - abs(s - hit) / 0.06)  # flattens for a moment on contact
    return x, y, squash


def draw(n, cv):
    t = n / demo.FPS
    demo.floor(cv, GROUND)
    for i in range(TRAIL, 0, -1):
        if n - i * GAP >= 0:
            gx, gy, _ = _ball_at(t - i * GAP / demo.FPS)
            demo.dot(cv, gx, gy, R * 0.8, color=demo.MUTED, alpha=0.32 * (1 - i / (TRAIL + 1)))
    x, y, squash = _ball_at(t)
    near = (y - TOP) / (GROUND - R - TOP)
    cv.ctx.save()
    cv.ctx.translate(x, GROUND + 6)
    cv.ctx.scale(1, 0.22)
    demo.dot(cv, 0, 0, R * (0.6 + 0.6 * near), color='#000000', alpha=0.15 + 0.35 * near)
    cv.ctx.restore()
    sx, sy = 1 + 0.3 * squash, 1 - 0.3 * squash
    cv.ctx.save()
    cv.ctx.translate(x, y + R * (1 - sy))
    cv.ctx.scale(sx, sy)
    demo.dot(cv, 0, 0, R)
    cv.ctx.restore()
    cv.mark('ball', x - R, y - R, 2 * R, 2 * R)
    speed = slow_motion_rate(t, **WINDOW)
    slow = vb.clamp01((1 - speed) / (1 - WINDOW['rate']))
    f = demo.mono(40, 600)
    w, h = vb.text.block_size([f'{speed:.2f}x'], f)
    vb.text.draw(cv, [f'{speed:.2f}x'], f, demo.W - 60 - w, 44, demo.ACCENT if slow > 0.5 else demo.MUTED)
    demo.word(cv, 'SLOW MOTION', demo.W / 2, 70, size=34, color=demo.INK, alpha=slow)


CAPABILITY = Capability(
    id='slow-motion',
    name='Slow Motion',
    family='principles',
    group='Time remapping',
    aliases=('slo-mo', 'slow-mo', 'slowed playback', 'speed ramp down'),
    definition='The action plays at a fraction of its normal speed for a stretch, '
               'so a quick moment is drawn out long enough to see every part of it.',
    phrasings=('slow it way down right at the impact',
               'make that moment play in slo-mo, then back to normal speed',
               'stretch out the bounce so you can really see it'),
    related=('slow-in-and-slow-out', 'delay', 'timing', 'friction-deceleration', 'frame-stutter',
             'scatter-time-playback'),
    api=('videobuilder.capabilities.principles.slow_motion.slow_motion',
         'videobuilder.capabilities.principles.slow_motion.slow_motion_rate'),
    demo=lambda: demo.film(draw),
)
