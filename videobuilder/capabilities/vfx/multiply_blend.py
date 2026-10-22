"""Multiply blend: a top layer is composited by multiplying its colours into
the picture below, so it can only darken -- white in the top layer leaves the
bottom untouched, black stays black, and overlapping colours stack like
translucent inks into deeper tones."""
import math

import cairo

from .. import _demo as demo
from ..schema import Capability

PAPER = '#efece4'
INKS = ('#29b6e8', '#e8409a', '#f5d327')   # cyan, magenta, yellow


def multiply_blend(cv, under, over, amount=1.0):
    """Draw `under(cv)`, then `over(cv)` as one group multiplied into it with
    cairo's MULTIPLY operator. `amount` (0 -> 1) fades the effect in: 0 leaves
    `under` alone, 1 is the full multiply. Where `over` is transparent or
    white the picture below shows through unchanged.

    In a film, pass the plate and the overlay as callables, e.g.
    `multiply_blend(cv, lambda c: plate(c, shot), lambda c: texture(c, shot), 1.0)`;
    `over` may itself call `multiply_blend` to stack several layers."""
    under(cv)
    if amount <= 0:
        return
    c = cv.ctx
    c.save()
    c.push_group()
    over(cv)
    c.pop_group_to_source()
    c.set_operator(cairo.OPERATOR_MULTIPLY)
    c.paint_with_alpha(min(1.0, amount))
    c.restore()


def _plate(cv):
    """Light paper with the sample photo in a panel, so the ink shows both on
    white (its own colour) and over the picture (the picture, darkened)."""
    cv.fill(PAPER)
    img = demo.photo()
    pw, ph = 520, 340
    x, y = (demo.W - pw) / 2, (demo.H - ph) / 2
    cv.image(img, x, y, pw, ph)


def _inks(t):
    """Three ink discs, each multiplied over the plate and over each other,
    gathering from the edges toward an overlapping trefoil at time `t` (s)."""
    gather = demo.phase(round(t * demo.FPS), 0.2, 2.2)
    gather = 1 - (1 - gather) ** 3
    spread = 380 - 270 * gather

    def draw(cv):
        for i, color in enumerate(INKS):
            ang = -math.pi / 2 + i * 2 * math.pi / 3 + 0.6 * (1 - gather)
            cx = demo.W / 2 + spread * 1.25 * math.cos(ang)
            cy = demo.H / 2 + spread * math.sin(ang)
            layer = lambda c, cx=cx, cy=cy, color=color: demo.dot(c, cx, cy, r=170, color=color)  # noqa: E731
            # Each disc multiplies into the discs before it, so the overlaps go red, green, blue, then near black.
            multiply_blend(cv, lambda c: None, layer)
    return draw


def _draw(n, cv):
    multiply_blend(cv, _plate, _inks(n / demo.FPS))
    demo.word(cv, 'Multiply', 110, 40, size=28, color=demo.BG)


CAPABILITY = Capability(
    id='multiply-blend',
    name='Multiply blend',
    family='vfx',
    group='Blend & composite',
    aliases=('multiply mode', 'darken blend', 'multiply composite'),
    definition='A layer is laid over the picture so that its colours tint and deepen whatever sits underneath, '
               'with its white parts vanishing and overlaps getting darker.',
    phrasings=('lay the colour over the photo like transparent ink so it only darkens',
               'put this texture on top but make the white bits disappear',
               'overlap the colours so they get darker where they cross, like printed inks'),
    related=('additive-dissolve', 'duotone', 'cross-dissolve', 'dip-to-black', 'posterization', 'faded-print-look'),
    api=('videobuilder.capabilities.vfx.multiply_blend.multiply_blend',),
    demo=lambda: demo.film(_draw),
)
