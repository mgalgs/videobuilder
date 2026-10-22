"""Motion blur: whatever moves during a frame's exposure is smeared along the
path it travelled, so fast things streak and still things stay sharp, each
by its own amount and in its own direction."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def accumulate(cv, draws):
    """Draw the average of `draws` (each a `draw(cv)`): every one is drawn into
    its own group and the groups are summed at equal weight, so a pixel only
    one of them covers ends up at 1/len(draws) of its colour and alpha, the
    way light adds up on film. The result composites over what is already on
    `cv` like any single drawing."""
    draws = list(draws)
    if not draws:
        return
    c = cv.ctx
    w = 1 / len(draws)
    c.save()
    c.push_group()
    for draw in draws:
        c.push_group()
        draw(cv)
        sample = c.pop_group()
        c.save()
        c.set_source(sample)
        c.set_operator(cairo.OPERATOR_ADD)
        c.paint_with_alpha(w)
        c.restore()
    c.pop_group_to_source()
    c.paint()
    c.restore()


def motion_blur(cv, draw, t, shutter=0.5, samples=16):
    """Draw `draw(cv, t)` -- a subject, or a whole scene, at time `t` (in
    frames; fractional times must work) -- as a camera with a `shutter` of
    that many frames would expose it: `samples` evenly spaced instants across
    `t - shutter / 2` to `t + shutter / 2`, averaged (see `accumulate`).

    Each part is blurred by its own movement, so a subject easing to a stop
    sharpens as it slows, a spinning one blurs in arcs, and whatever is still
    stays crisp. `shutter` 0.5 is film's usual 180-degree shutter; 1.0 and up
    exaggerate. In a film, call `motion_blur(cv, lambda c, t: subject(c, t), n)`
    from `draw(n, cv)`."""
    if shutter <= 0 or samples <= 1:
        draw(cv, t)
        return
    n = int(samples)
    times = [t + shutter * (i / (n - 1) - 0.5) for i in range(n)]
    accumulate(cv, [lambda c, s=s: draw(c, s) for s in times])


def directional_blur(cv, draw, dx, dy, samples=16):
    """Draw `draw(cv)` streaked along the vector (`dx`, `dy`): copies spaced
    evenly from half the vector back to half forward, averaged -- the linear
    motion blur of something that moved that far during the exposure."""
    if math.hypot(dx, dy) < 0.5 or samples <= 1:
        draw(cv)
        return
    n = int(samples)

    def shifted(k):
        def paint(c):
            with c.layer(dx=dx * k, dy=dy * k):
                draw(c)
        return paint
    accumulate(cv, [shifted(i / (n - 1) - 0.5) for i in range(n)])


# The demo: a card dashes across and back, sharp at rest and streaked in
# flight; under it three dots lap the frame at steady slow, quick and fast
# speeds, their blur growing with their speed.
LEFT, RIGHT, CARD_Y = demo.W * 0.2, demo.W * 0.8, demo.H * 0.32
DASHES = ((0.55, 1.05, LEFT, RIGHT), (1.85, 2.35, RIGHT, LEFT))  # (start s, end s, from x, to x)
LANES = (demo.H * 0.64, demo.H * 0.76, demo.H * 0.88)
DOTS = ((4, demo.TEAL), (12, demo.ACCENT), (32, demo.INK))  # (px per frame, colour), one per lane
R = 16
LAP = demo.W + 4 * R


def card_x(t):
    x = LEFT
    for start, end, a, b in DASHES:
        if t / demo.FPS >= start:
            p = vb.clamp01((t / demo.FPS - start) / (end - start))
            x = a + (b - a) * vb.ease_in_out_quart(p)
    return x


def card_at(cv, t):
    demo.card(cv, card_x(t), CARD_Y, w=200, h=120)


def dot_at(speed, color, y):
    def draw(cv, t):
        x = (demo.W * 0.3 + speed * t) % LAP - 2 * R
        demo.dot(cv, x, y, r=R, color=color)
    return draw


def draw(n, cv):
    for y in LANES:
        cv.line(40, y, demo.W - 40, y, demo.LINE, width=1)
    motion_blur(cv, card_at, n, shutter=1.0, samples=32)
    for (speed, color), y in zip(DOTS, LANES):
        motion_blur(cv, dot_at(speed, color, y), n, shutter=1.0, samples=24)


CAPABILITY = Capability(
    id='motion-blur',
    name='Motion blur',
    family='vfx',
    group='Blur & focus',
    aliases=('directional blur', 'linear blur', 'streak blur', 'shutter blur', 'vector motion blur'),
    definition='Anything moving is smeared along its own path in proportion to its speed, so fast parts '
               'streak while slow or still parts stay crisp.',
    phrasings=('add motion blur so the fast moves look smooth and not choppy',
               'make the card streak as it flies across the screen',
               'blur things in the direction they move, like a real camera would'),
    related=('zoom-blur', 'smear-frame', 'whip-pan', 'tracking-shot', 'blur-dissolve', 'blur-up-image-load'),
    api=('videobuilder.capabilities.vfx.motion_blur.motion_blur',
         'videobuilder.capabilities.vfx.motion_blur.directional_blur',
         'videobuilder.capabilities.vfx.motion_blur.accumulate'),
    demo=lambda: demo.film(draw),
)
