"""Tracking In: a line arrives with its letters spread far apart and draws
them together to its set spacing, fading up as it closes."""
import dataclasses

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

SETTLE = vb.bezier(0.2, 0.6, 0.35, 1)  # a soft ease-out: quick start, long gentle landing


def tracking_at(p, start=0.8, end=0.0, ease=SETTLE):
    """The letter-spacing (em) at progress `p` (0 -> 1): `start` eased down
    to `end`, fast at first and settling gently."""
    return end + (start - end) * (1 - ease(vb.clamp01(p)))


def draw_tracking_in(cv, text, font, cx, cy, p, color, spread=0.8, fade=0.6, ease=SETTLE, alpha=1.0):
    """Draw `text` centred at (cx, cy) tracking in at progress `p` (0 -> 1):
    its letter-spacing closes from `font.tracking + spread` em to
    `font.tracking`, and it fades up over the first `fade` of the move.
    The line stays centred as it narrows. Returns the Box of the drawn line."""
    f = dataclasses.replace(font, tracking=tracking_at(p, font.tracking + spread, font.tracking, ease))
    w, h = vb.text.block_size([text], f)
    a = alpha * vb.clamp01(p / fade) if fade > 0 else alpha
    return vb.text.draw(cv, [text], f, cx - w / 2, cy - h / 2, color, alpha=a)


def draw(n, cv):
    box = draw_tracking_in(cv, 'MOTION', demo.font(96, 800), demo.W / 2, demo.H / 2,
                           demo.phase(n, 0.3, 2.2), demo.INK, spread=0.6, fade=0.7)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='tracking-in',
    name='Tracking in',
    family='typography',
    group='Per-unit reveals',
    aliases=('letter-spacing contract', 'tracking squeeze in', 'tracking in text'),
    definition='A word appears with its letters spaced wide apart and draws them together to normal '
               'spacing as it fades up, easing to a stop.',
    phrasings=('the letters start spread out and slide together into the word',
               'the title fades in while its letter spacing tightens',
               'a wide-spaced headline that squeezes into place'),
    related=('scanline-jitter', 'dolly-in-and-out', 'tracking-shot', 'rubber-band-overscroll',
             'player-movement-trail', 'cursor-follower-dot-and-ring'),
    api=('videobuilder.capabilities.typography.tracking_in.draw_tracking_in',
         'videobuilder.capabilities.typography.tracking_in.tracking_at'),
    demo=lambda: demo.film(draw),
)
