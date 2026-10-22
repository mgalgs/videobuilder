"""Smear Frame: on the few frames of a very fast move, the subject is drawn
stretched along its path from where it was on the frame before to where it
is now, so the eye reads one streak instead of a jump."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def smear_frame(cv, draw, x0, y0, x1, y1, size, threshold=0.25, thin=0.5):
    """Draw `draw(cv)` -- the subject centred on (0, 0), `size` px across
    at rest -- at (x1, y1), smeared back towards (x0, y0), where it was on
    the previous frame.

    When the step is shorter than `threshold` x `size` it draws the subject
    plainly at (x1, y1). Otherwise it stretches it along the step to cover
    both positions and narrows it across (by up to `thin`, keeping a sense of
    volume), so a move of a few frames reads as a streak. In a film, pass the
    subject's position on frame `n - 1` and on frame `n`."""
    dx, dy = x1 - x0, y1 - y0
    dist = math.hypot(dx, dy)
    if dist < threshold * size:
        cv.ctx.save()
        cv.ctx.translate(x1, y1)
        draw(cv)
        cv.ctx.restore()
        return
    stretch = (size + dist) / size
    across = max(thin, 1 / math.sqrt(stretch))
    cv.ctx.save()
    cv.ctx.translate((x0 + x1) / 2, (y0 + y1) / 2)
    cv.ctx.rotate(math.atan2(dy, dx))
    cv.ctx.scale(stretch, across)
    draw(cv)
    cv.ctx.restore()


R = 46
LEFT, RIGHT, Y = 260, demo.W - 260, demo.H / 2 + 20
ZIPS = ((0.7, 0.95, LEFT, RIGHT), (1.9, 2.15, RIGHT, LEFT))  # (start s, end s, from x, to x)


def x_at(n):
    x = LEFT
    for start, end, a, b in ZIPS:
        if n / demo.FPS >= start:
            x = a + (b - a) * vb.ease_in_out_quart(demo.phase(n, start, end))
    return x


def ball(cv):
    demo.dot(cv, 0, 0, R)


def draw(n, cv):
    demo.floor(cv, Y + R + 30)
    for x in (LEFT, RIGHT):  # the two places it rests
        cv.arc(x, Y, R + 10, 0, 2 * math.pi, demo.MUTED, width=2, alpha=0.4)
    x0, x1 = x_at(max(0, n - 1)), x_at(n)
    smear_frame(cv, ball, x0, Y, x1, Y, 2 * R)
    cv.mark('ball', min(x0, x1) - R, Y - R, abs(x1 - x0) + 2 * R, 2 * R)


TECHNIQUE = Technique(
    id='smear-frame',
    name='Smear Frame',
    family='principles',
    group='Principle sub-techniques',
    aliases=('smear', 'smears', 'stretch smear', 'animation smear'),
    definition='During a very quick move, the object is drawn for a frame or two as one long stretched '
               'shape spanning where it was and where it is, instead of jumping between the two.',
    phrasings=('stretch it out into a streak as it zips across',
               'make the fast move look cartoony, smeared between positions',
               'draw it elongated for a couple of frames while it whooshes over'),
    related=('motion-blur', 'accumulation-motion-blur', 'spin-blur', 'whip-pan', 'linear-wipe', 'zoom-blur'),
    api=('videobuilder.techniques.principles.smear_frame.smear_frame',),
    demo=lambda: demo.film(draw),
)
