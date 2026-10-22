"""Bounce Ease Out: an easing curve that lands like a ball dropped on a floor,
hitting the target and bouncing off it in shrinking hops before it settles."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def bounce_ease_out(x):
    """Progress `x` in [0, 1] -> eased progress, ending in three shrinking
    bounces off 1 (the classic piecewise-parabola curve)."""
    x = vb.clamp01(x)
    n, d = 7.5625, 2.75
    if x < 1 / d:
        return n * x * x
    if x < 2 / d:
        x -= 1.5 / d
        return n * x * x + 0.75
    if x < 2.5 / d:
        x -= 2.25 / d
        return n * x * x + 0.9375
    x -= 2.625 / d
    return n * x * x + 0.984375


def draw(n, cv):
    r, ground = 34, demo.H - 110
    top, rest = 90 + r, ground - r
    y = top + (rest - top) * bounce_ease_out(demo.phase(n, 0.4, 1.9))
    near = (y - top) / (rest - top)  # 1 on the floor: the shadow tightens as the ball comes down
    cv.ctx.save()
    cv.ctx.translate(demo.W / 2, ground + 6)
    cv.ctx.scale(1, 0.22)
    demo.dot(cv, 0, 0, r * (0.6 + 0.6 * near), color='#000000', alpha=0.15 + 0.35 * near)
    cv.ctx.restore()
    demo.floor(cv, ground)
    demo.dot(cv, demo.W / 2, y, r)
    cv.mark('ball', demo.W / 2 - r, y - r, 2 * r, 2 * r)


CAPABILITY = Capability(
    id='bounce-ease-out',
    name='Bounce Ease Out',
    family='principles',
    group='Easing',
    aliases=('bounce out', 'ease out bounce'),
    definition='A move that hits its target and bounces back off it in a few quickly shrinking hops, '
               'like a ball dropped on a hard floor.',
    phrasings=('drops in and bounces a few times before it settles',
               'lands like a bouncing ball',
               'falls and bounces on the ground'),
    related=('ease-out-back', 'bounce-ease-in', 'squash-and-stretch'),
    api=('videobuilder.capabilities.principles.bounce_ease_out.bounce_ease_out',),
    demo=lambda: demo.film(draw),
)
