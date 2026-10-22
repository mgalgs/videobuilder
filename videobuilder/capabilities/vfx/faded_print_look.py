"""Faded Print Look: a grade that makes footage look like an old photographic
print left in the sun -- colour drained, blacks lifted to a warm brown,
whites dulled to cream, a yellowed cast, grain and soft darkened corners."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

SHADOW = (0.24, 0.17, 0.13)     # what pure black fades up to: a dusty brown
PAPER = (0.96, 0.90, 0.78)      # what pure white sinks to: aged cream
TINT = (0.80, 0.62, 0.38)       # the yellowed cast over the midtones


def _paint(ctx, op, rgb, alpha):
    ctx.set_operator(op)
    ctx.set_source_rgb(*rgb)
    ctx.paint_with_alpha(alpha)


def faded_print(cv, amount=1.0, box=None, seed=0, grain=0.25, vignette=0.45):
    """Grade whatever is already drawn in `box` (default the whole canvas) as
    a faded print, `amount` 0 -> 1 from untouched to fully faded: saturation
    drained, blacks lifted to `SHADOW`, whites lowered to `PAPER`, a warm
    `TINT`, `grain` strength of paper grain (`seed` picks the texture; change
    it per frame for live film grain) and a `vignette` darkening the corners.

    Call it last in a frame's `draw`, after the shot: `scene(cv); faded_print(cv, 0.8)`."""
    a = vb.clamp01(amount)
    if a <= 0:
        return
    box = vb.Box(*box) if box is not None else vb.Box.of(cv)
    ctx = cv.ctx
    ctx.save()
    ctx.rectangle(*box)
    ctx.clip()
    _paint(ctx, cairo.OPERATOR_HSL_SATURATION, (0.5, 0.5, 0.5), 0.7 * a)   # drain the colour
    _paint(ctx, cairo.OPERATOR_SOFT_LIGHT, TINT, 0.55 * a)                 # yellow it
    _paint(ctx, cairo.OPERATOR_SCREEN, SHADOW, a)                          # no true black left
    _paint(ctx, cairo.OPERATOR_MULTIPLY, PAPER, a)                         # no true white either
    if vignette:
        r = math.hypot(box.w, box.h) / 2
        g = cairo.RadialGradient(box.cx, box.cy, 0, box.cx, box.cy, r)
        g.add_color_stop_rgba(0.5, 0.3, 0.2, 0.1, 0)
        g.add_color_stop_rgba(1.0, 0.3, 0.2, 0.1, vignette * a)
        ctx.set_operator(cairo.OPERATOR_MULTIPLY)
        ctx.set_source(g)
        ctx.paint()
    if grain:
        ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
        ctx.set_source(vb.paper_grain(cv.width, cv.height, seed=seed))
        ctx.paint_with_alpha(grain * a)
    ctx.restore()


def _draw(n, cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    demo.card(cv, demo.W * 0.72, demo.H * 0.68, w=340, h=210, color=demo.ACCENT)
    faded_print(cv, vb.ease_in_out_quart(demo.phase(n, 0.6, 2.0)), seed=n % 6)


CAPABILITY = Capability(
    id='faded-print-look',
    name='Faded print look',
    family='vfx',
    group='Color & grading',
    aliases=('faded film look', 'vintage photo grade', 'lifted blacks', 'retro wash'),
    definition='Footage is graded to resemble a weathered photo print, with muted colour, '
               'milky lifted shadows, creamy highlights, a warm yellow cast and a little grain.',
    phrasings=('make it look like an old faded photograph',
               'give the shot a washed-out vintage film feel',
               'lift the blacks and warm it up so it looks sun-bleached'),
    related=('dip-to-black', 'crumple', 'gradient-wipe', 'screen-blend', 'multiply-blend',
             'per-character-fade-in'),
    api=('videobuilder.capabilities.vfx.faded_print_look.faded_print',),
    demo=lambda: demo.film(_draw),
)
