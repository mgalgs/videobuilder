"""Tracking Out: a line of text whose letter-spacing slowly widens while it
holds on screen, the letters drifting apart from its centre."""
import dataclasses

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

SETTLE = vb.bezier(0.3, 0.1, 0.4, 1.0)  # a long, soft ease-out: the drift keeps moving almost to the end


def tracking_at(p, start=0.0, end=0.4, ease=SETTLE):
    """The letter-spacing, in em, at progress `p` (0 -> 1) of a track-out
    from `start` to `end`. `end` below `start` tracks in instead."""
    return start + (end - start) * ease(vb.clamp01(p))


def draw_tracking_out(cv, text, font, cx, cy, p, color, start=0.0, end=0.4, ease=SETTLE, fade=0.3, alpha=1.0):
    """Draw one line of `text` centred at (cx, cy), its letter-spacing at
    progress `p` of a track-out from `start` to `end` em (see `tracking_at`).
    The line stays centred, so the letters spread both ways. It fades in over
    the first `fade` of the move (0: no fade). Returns the line's Box."""
    f = dataclasses.replace(font, tracking=tracking_at(p, start, end, ease), css_tracking=False)
    a = alpha * (vb.clamp01(p / fade) if fade > 0 else 1.0)
    w, h = vb.text.block_size([text], f)
    return vb.text.draw(cv, [text], f, cx - w / 2, cy - h / 2, color, alpha=a)


def draw(n, cv):
    p = demo.phase(n, 0.2, 2.9)
    box = draw_tracking_out(cv, 'HORIZON', demo.font(120, 800), demo.W / 2, demo.H / 2 - 20, p, demo.INK,
                            start=-0.02, end=0.32)
    cv.mark('text', *box)
    demo.word(cv, 'A FILM IN THREE PARTS', demo.W / 2, demo.H / 2 + 110, size=30, color=demo.MUTED, weight=600,
              alpha=demo.phase(n, 0.9, 1.6))


TECHNIQUE = Technique(
    id='tracking-out',
    name='Tracking out',
    family='typography',
    group='Per-unit reveals',
    aliases=('letter-spacing animation', 'tracking expand', 'kerning out', 'title spread'),
    definition='The gaps between the letters of a word slowly widen while it holds on screen, '
               'so the title drifts outward from its centre.',
    phrasings=('the letters slowly spread apart like a movie title',
               'animate the letter spacing getting wider',
               'the word breathes out, its letters drifting away from each other'),
    related=('offset-path-expansion', 'dolly-in-and-out', 'text-mask-reveal', 'letter-roll', 'noise-field-warp',
             'scroll-linked-clip-reveal'),
    api=('videobuilder.techniques.typography.tracking_out.draw_tracking_out',
         'videobuilder.techniques.typography.tracking_out.tracking_at'),
    demo=lambda: demo.film(draw),
)
