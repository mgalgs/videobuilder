"""Weight and Mass: the same push moves a light thing and a heavy thing very
differently -- the light one darts off and stops on a dime, the heavy one is
slow to get going, takes longer, and carries past its mark before it settles."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def weight_ease(mass):
    """An easing curve for an object of `mass` in [0, 1] (0 light, 1 heavy).

    Light objects start quickly and stop crisply; heavier ones resist the
    start (a long slow ramp) and resist the stop (a small overshoot past 1
    that eases back). Pair with `weight_seconds` so heavy moves also take longer."""
    m = vb.clamp01(mass)
    lerp = lambda a, b: a + (b - a) * m  # noqa: E731
    return vb.bezier(lerp(0.25, 0.8), 0.0, lerp(0.1, 0.3), lerp(1.0, 1.14))


def weight_seconds(seconds, mass, heavy=2.6):
    """How long a move of `seconds` (at mass 0) takes at `mass` in [0, 1]:
    up to `heavy` times longer for the heaviest object."""
    return seconds * (1 + (heavy - 1) * vb.clamp01(mass))


def weight_squash(ease, p, amount=0.35, dp=0.02):
    """(scale_x, scale_y) for an object moving horizontally along `ease` at
    progress `p`: it squashes against its direction while it is pushed into
    speed and while it brakes, the effort reading as mass. Keeps area."""
    def v(q):
        return (ease(min(1.0, q + dp)) - ease(max(0.0, q - dp))) / (2 * dp)
    accel = abs(v(p + dp) - v(p - dp)) / (2 * dp) if 0 < p < 1 else 0.0
    s = 1 + amount * min(1.0, accel / 12)
    return s, 1 / s


LANES = ((0.0, 'light', demo.TEAL, 44, 44), (1.0, 'heavy', demo.ACCENT, 130, 104))
START, BASE = 0.4, 0.75


def draw(n, cv):
    x0, x1 = 170, demo.W - 170
    label = demo.mono(18)
    for i, (mass, name, color, w, h) in enumerate(LANES):
        ground = 200 + i * 240
        demo.floor(cv, ground)
        cv.line(x1, ground - 140, x1, ground, demo.MUTED, width=2, alpha=0.5)  # the mark both are pushed to
        vb.text.draw(cv, [name], label, 80, ground - 150, demo.MUTED)
        ease = weight_ease(mass)
        p = demo.phase(n, START, START + weight_seconds(BASE, mass))
        sx, sy = weight_squash(ease, p, amount=0.35 * mass)  # only the heavy one strains
        cx, bw, bh = x0 + (x1 - x0) * ease(p), w * sx, h * sy
        cv.shadow(cx - bw / 2, ground - bh, bw, bh, radius=12, dy=6, blur=18, color=(0, 0, 0, 0.45))
        cv.rect(cx - bw / 2, ground - bh, bw, bh, color, radius=12)
        cv.mark(name, cx - bw / 2, ground - bh, bw, bh)


CAPABILITY = Capability(
    id='weight-and-mass',
    name='Weight and Mass',
    family='principles',
    group='Principle sub-capabilities',
    aliases=('heaviness', 'mass perception', 'sense of weight'),
    definition='Timing that tells you how heavy something is: a heavy object starts slowly, takes longer, '
               'and drifts past its mark before settling, while a light one zips off and stops at once.',
    phrasings=('make the big block feel heavy when it moves',
               'give it some weight, like it is hard to push',
               'the light thing should zip and the heavy thing should lumber'),
    related=('gravity-well-attraction', 'inertia', 'mass-spring-cloth', 'timing', 'air-drag',
             'variable-font-weight-animation'),
    api=('videobuilder.capabilities.principles.weight_and_mass.weight_ease',
         'videobuilder.capabilities.principles.weight_and_mass.weight_seconds',
         'videobuilder.capabilities.principles.weight_and_mass.weight_squash'),
    demo=lambda: demo.film(draw),
)
