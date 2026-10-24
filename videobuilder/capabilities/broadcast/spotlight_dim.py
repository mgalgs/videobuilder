"""Spotlight Dim: everything on screen darkens except one region, which stays
at full brightness, so the eye goes straight to it."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _hole(ctx, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def spotlight_dim(cv, box, amount, color='#08090c', strength=0.7, radius=18, pad=10, feather=18, steps=6):
    """Darken the whole frame except `box` (a `vb.Box` or (x, y, w, h)), at
    `amount` 0 -> 1 of the full dim. Call it after drawing the scene.

    The lit region is `box` grown by `pad`, with corner `radius`; `strength`
    is the dim's opacity at full `amount`; `feather` px softens the cut's
    edge, built from `steps` stacked rings. Animate `amount` (and `box`) to
    bring the spotlight in, move it or let it go."""
    a = vb.clamp01(amount) * strength
    if a <= 0:
        return
    x, y, w, h = tuple(box)
    x, y, w, h = x - pad, y - pad, w + 2 * pad, h + 2 * pad
    n = max(1, steps) if feather > 0 else 1
    each = 1 - (1 - a) ** (1 / n)  # n stacked fills add up to `a` outside the feather
    r, g, b, _ = vb.rgba(color)
    ctx = cv.ctx
    ctx.save()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    for i in range(n):
        grow = feather * i / n
        ctx.new_path()
        ctx.rectangle(0, 0, cv.width, cv.height)
        _hole(ctx, x - grow, y - grow, w + 2 * grow, h + 2 * grow, radius + grow)
        ctx.set_source_rgba(r, g, b, each)
        ctx.fill()
    ctx.restore()


CARDS = (('Revenue', demo.TEAL), ('Signups', demo.ACCENT), ('Churn', demo.TEAL))


def _scene(cv, lift):
    cv.fill('#e9e6df')
    demo.word(cv, 'This quarter', demo.W / 2, 90, size=40, color=demo.BG)
    boxes = []
    for i, (label, color) in enumerate(CARDS):
        cx, cy = demo.W / 2 + (i - 1) * 270, demo.H / 2 + 10
        up = 8 * lift if i == 1 else 0
        demo.card(cv, cx, cy - up, w=220, h=140, color=color, scale=1 + (0.05 * lift if i == 1 else 0))
        demo.word(cv, label, cx, cy + 115, size=28, color=demo.BG)
        boxes.append(vb.Box(cx - 120, cy - 80 - up, 240, 220 + up))
    return boxes


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.7, 1.3))
    boxes = _scene(cv, p)
    spotlight_dim(cv, boxes[1], p, pad=6, feather=12)
    cv.mark('spotlit', *boxes[1])


CAPABILITY = Capability(
    id='spotlight-dim',
    name='Spotlight dim',
    family='broadcast',
    group='Annotation',
    aliases=('dim the rest', 'focus dim', 'spotlight overlay', 'highlight cutout', 'coachmark', 'spotlight callout'),
    definition='The whole frame darkens except for one area, which stays bright as if a spotlight '
               'were on it, pulling attention there.',
    phrasings=('darken everything except the card we are talking about',
               'grey out the rest of the screen so this part stands out',
               'put a spotlight on that one item and dim the background'),
    related=('spotlight-hover', 'spotlight-follow', 'vignette', 'rim-light',
             'coachmark-spotlight-cutout', 'shine-glint-sweep'),
    api=('videobuilder.capabilities.broadcast.spotlight_dim.spotlight_dim',
         'videobuilder.capabilities.shapes.callout_highlight.callout_highlight',
         'videobuilder.capabilities.ui.coachmark_spotlight_cutout.tour_hole',
         'videobuilder.capabilities.ui.coachmark_spotlight_cutout.coachmark_tip'),
    demo=lambda: demo.film(draw),
)
