"""Ball Bounce: the classic animation exercise -- a ball dropped under gravity,
each hop lower and shorter than the last, squashing flat where it hits the
floor and stretching along its fall, while it travels across and comes to rest."""
import math

from .. import _demo as demo
from ..schema import Capability


def ball_bounce(t, height, gravity=3000.0, bounciness=0.62, squash=0.3, stretch=0.15, contact=0.05):
    """A ball dropped from `height` (px above the floor) at `t` = 0 s, under
    `gravity` px/s^2, keeping `bounciness` of its speed at each hit.

    Returns `(h, sx, sy)` for time `t` seconds: `h` the height of the ball's
    bottom above the floor, and `sx`, `sy` the scale to draw it at (anchored
    on its bottom) -- stretched up to `stretch` along a fast fall, and resting
    on the floor squashed up to `squash` for `contact` seconds around each
    hit, volume kept. Before 0 it hangs at `height`; once the hops get too
    small to see it lies still."""
    if t <= 0 or height <= 0:
        return max(height, 0.0), 1.0, 1.0
    v0 = math.sqrt(2 * gravity * height)  # speed at the first hit
    hit = v0 / gravity                    # time of the first hit
    if t < hit:
        h, v, since, until = height - gravity * t * t / 2, gravity * t, None, hit - t
    else:
        v, start = v0 * bounciness, hit
        while True:
            flight = 2 * v / gravity
            if v < 0.02 * v0 or t < start + flight:
                break
            start += flight
            v *= bounciness
        if v < 0.02 * v0:
            return 0.0, 1.0, 1.0
        s = t - start
        h, since, until = v * s - gravity * s * s / 2, s, start + flight - t
        v = abs(v - gravity * s)
    speed = v / v0
    near = min(x for x in (since, until) if x is not None)
    if near < contact:  # on the floor: sit on it and flatten, harder for a faster hit
        hit_speed = (v + gravity * near) / v0
        k = 1 - squash * min(hit_speed, 1) * (1 - near / contact)
        return 0.0, 1 / math.sqrt(k), k
    k = 1 + stretch * speed
    return h, 1 / math.sqrt(k), k


def draw(n, cv):
    r, ground = 40, demo.H - 120
    drop, t0 = demo.H - 300, 0.15
    x0, x1, travel = 200, demo.W - 240, 2.4

    def at(t):  # across the frame at a slowly fading speed, while it bounces
        p = demo.phase(t * demo.FPS, t0, t0 + travel)
        return (x0 + (x1 - x0) * (1 - (1 - p) ** 1.3),) + ball_bounce(t - t0, drop, bounciness=0.7)

    demo.floor(cv, ground)
    for i in range(0, n, 2):  # the path so far, as a fading dotted trail
        x, h, _, _ = at(i / demo.FPS)
        demo.dot(cv, x, ground - h - r, 5, color=demo.MUTED, alpha=0.35 + 0.5 * i / max(n, 1))
    x, h, sx, sy = at(n / demo.FPS)
    near = 1 - min(h / drop, 1)
    cv.ctx.save()
    cv.ctx.translate(x, ground + 6)
    cv.ctx.scale(1, 0.22)
    demo.dot(cv, 0, 0, r * (0.6 + 0.6 * near), color='#000000', alpha=0.1 + 0.35 * near)
    cv.ctx.restore()
    cv.ctx.save()
    cv.ctx.translate(x, ground - h)
    cv.ctx.scale(sx, sy)
    demo.dot(cv, 0, -r, r)
    cv.ctx.restore()
    cv.mark('ball', x - r * sx, ground - h - 2 * r * sy, 2 * r * sx, 2 * r * sy)


CAPABILITY = Capability(
    id='ball-bounce',
    name='Ball Bounce',
    family='principles',
    group='Physics',
    aliases=('bouncing ball', 'bouncing ball exercise', 'gravity bounce'),
    definition='A ball falls under gravity and rebounds from the floor in ever lower, ever shorter hops, '
               'flattening on each impact and stretching as it drops, until it comes to rest.',
    phrasings=('drop a ball and let it bounce across the floor until it stops',
               'make it bounce like a real rubber ball, losing height each time',
               'a ball that bounces along with a bit of squash when it lands'),
    related=('bounce-ease-out', 'bounce-ease-in', 'elastic-collisions', 'overshoot-bounce-in', 'spring-return',
             'newton-s-cradle'),
    api=('videobuilder.capabilities.principles.ball_bounce.ball_bounce',),
    demo=lambda: demo.film(draw),
)
