"""Bounce Ease In: the mirror of Bounce Ease Out -- the move gathers itself in
a few hops that grow each time, then launches off the last one to its target."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from .bounce_ease_out import bounce_ease_out


def bounce_ease_in(x):
    """Progress `x` in [0, 1] -> eased progress, starting with three growing
    hops off 0 before the final rise to 1 (`bounce_ease_out` run backwards)."""
    return 1 - bounce_ease_out(1 - vb.clamp01(x))


def draw(n, cv):
    r, ground = 34, demo.H - 110
    top, rest = 90 + r, ground - r
    lift = bounce_ease_in(demo.phase(n, 0.4, 2.3))
    y = rest + (top - rest) * lift
    near = 1 - lift  # 1 on the floor: the shadow tightens as the ball comes down
    demo.dot(cv, demo.W / 2, top, r, color=demo.MUTED, alpha=0.25)  # where it is headed
    cv.ctx.save()
    cv.ctx.translate(demo.W / 2, ground + 6)
    cv.ctx.scale(1, 0.22)
    demo.dot(cv, 0, 0, r * (0.6 + 0.6 * near), color='#000000', alpha=0.15 + 0.35 * near)
    cv.ctx.restore()
    demo.floor(cv, ground)
    demo.dot(cv, demo.W / 2, y, r)
    cv.mark('ball', demo.W / 2 - r, y - r, 2 * r, 2 * r)


TECHNIQUE = Technique(
    id='bounce-ease-in',
    name='Bounce Ease In',
    family='principles',
    group='Easing',
    aliases=('bounce in', 'ease in bounce'),
    definition='A move that winds up with a few small hops, each higher than the last, '
               'before springing off the final one all the way to its target.',
    phrasings=('hops a few times, getting higher, then jumps up',
               'bounces to build up speed before it takes off',
               'the bounce happens at the start instead of the end'),
    related=('ball-bounce', 'overshoot-bounce-in', 'settle', 'momentum-fling', 'smooth-scroll-inertia',
             'icon-hover-bounce'),
    api=('videobuilder.techniques.principles.bounce_ease_in.bounce_ease_in',),
    demo=lambda: demo.film(draw),
)
