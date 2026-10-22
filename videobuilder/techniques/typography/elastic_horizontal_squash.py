"""Elastic Horizontal Squash: each letter of a word goes wide and flat, then
narrow and tall, its width and height always trading against each other like
a rubber block, in a wave along the word that wobbles out and settles."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def squash(t, amp=0.45, hz=2.2, decay=2.6):
    """How squashed a letter is `t` seconds after its kick: a damped
    oscillation about 0, starting wide (> 0 is wider and flatter, < 0
    narrower and taller) and dying away. 0 before the kick."""
    if t <= 0:
        return 0.0
    return amp * math.exp(-decay * t) * math.sin(2 * math.pi * hz * t)


def squash_scale(s):
    """A squash amount -> `(sx, sy)`: the width grows by `1 + s` and the
    height shrinks to match, so the letter keeps its area."""
    sx = max(0.2, 1 + s)
    return sx, 1 / sx


def draw_squash(cv, text, font, x, y, t, color, stagger=0.07, alpha=1.0, **kw):
    """Draw `text` from its top-left (x, y) with every letter squashing in
    turn: letter i is kicked `i * stagger` s after `t` = 0 and scales about
    the foot of its own place on the line, so the line never shifts. `kw`
    goes to `squash`. Returns the Box of the line at rest."""
    w, h = vb.text.block_size([text], font)
    foot = y + h * 0.82  # about where the letters stand
    left = x
    for i, ch in enumerate(text):
        adv = vb.text.measure(ch, font)
        if not ch.isspace():
            sx, sy = squash_scale(squash(t - i * stagger, **kw))
            cx = left + adv / 2
            cv.ctx.save()
            cv.ctx.translate(cx, foot)
            cv.ctx.scale(sx, sy)
            vb.text.draw(cv, [ch], font, -adv / 2, y - foot, color, alpha=alpha)
            cv.ctx.restore()
        left += adv
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(150, 900)
    text = 'ELASTIC'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    demo.floor(cv, y + h * 0.82 + 6)
    box = draw_squash(cv, text, f, x, y, n / demo.FPS - 0.4, demo.INK)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='elastic-horizontal-squash',
    name='Elastic horizontal squash',
    family='typography',
    group='Stretch and squash',
    aliases=('letter squash and stretch', 'elastic type', 'rubber letters'),
    definition='Letters bulge wide and flat, then pull narrow and tall, height always trading against '
               'width, in a springy wave that wobbles along the word and settles.',
    phrasings=('make the letters squish sideways and spring back like rubber',
               'the word stretches wide and snaps back with a jiggle',
               'each letter wobbles fat then thin, like jelly'),
    related=('squash-and-stretch', 'squash-on-tap', 'elastic-stretch', 'rubber-band-overscroll',
             'rubber-band-snap', 'elastic-ease-out'),
    api=('videobuilder.techniques.typography.elastic_horizontal_squash.draw_squash',
         'videobuilder.techniques.typography.elastic_horizontal_squash.squash',
         'videobuilder.techniques.typography.elastic_horizontal_squash.squash_scale'),
    demo=lambda: demo.film(draw),
)
