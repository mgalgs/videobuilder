"""Elastic Horizontal Squash: letters trading height for width on springs,
the same as Rubber letters (`type_rubber.py`, which keeps the capability
-- its own alias "rubber letters" is that Type style's own title): each
letter of a word goes wide and flat, then narrow and tall, its width and
height always trading against each other like a rubber block, in a wave
along the word that wobbles out and settles. This module's own code stays
(a film may still import it), but it is no longer a capability of its
own."""
import math

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'type-rubber'


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


def draw_squash(cv, text, font, x, y, t, color, stagger=0.07, alpha=1.0, tracking=0.0, **kw):
    """Draw `text` from its top-left (x, y) with every letter squashing in
    turn: letter i is kicked `i * stagger` s after `t` = 0 and scales about
    the foot of its own place on the line, so the line never shifts.
    `tracking` px is added between letters so neighbours that bulge wide
    together stay apart. `kw` goes to `squash`. Returns the Box of the line
    at rest."""
    w, h = vb.text.block_size([text], font)
    w += tracking * max(0, len(text) - 1)
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
        left += adv + tracking
    return vb.Box(x, y, w, h)


KICK_EVERY = 1.3  # s between kicks, so the word is mid-wobble at the poster


def draw(n, cv):
    f = demo.font(150, 900)
    text = 'ELASTIC'
    tracking = 16
    w, h = vb.text.block_size([text], f)
    w += tracking * (len(text) - 1)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    demo.floor(cv, y + h * 0.82 + 6)
    t = n / demo.FPS - 0.4
    if t > 0:
        t %= KICK_EVERY  # kick again each time the wave has nearly settled
    box = draw_squash(cv, text, f, x, y, t, demo.INK, tracking=tracking, amp=0.32, decay=1.8)
    cv.mark('text', *box)
