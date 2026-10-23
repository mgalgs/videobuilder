"""Squircle morph: one solid shape eases from a hard-cornered square through
the soft squircle in between to a perfect circle, by sliding the exponent of
a superellipse rather than blending two outlines."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

SQUARE, SQUIRCLE, CIRCLE, DIAMOND = 40.0, 4.0, 2.0, 1.0  # superellipse exponents of the named shapes


def squircle(cx, cy, w, h, exponent, steps=240, rotation=0.0):
    """The closed point list of the superellipse |x/a|^e + |y/b|^e = 1 fitted
    to a `w` x `h` box centred at (cx, cy), turned `rotation` radians. `exponent`
    2 is an ellipse, 4 the classic squircle, 1 a diamond; it tends to the
    sharp rectangle as it grows (40 reads as square)."""
    a, b, k = w / 2, h / 2, 2 / max(exponent, 0.1)
    cr, sr = math.cos(rotation), math.sin(rotation)
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        x = a * math.copysign(abs(c) ** k, c)
        y = b * math.copysign(abs(s) ** k, s)
        pts.append((cx + x * cr - y * sr, cy + x * sr + y * cr))
    return pts


def squircle_exponent(p, start=SQUARE, end=CIRCLE):
    """The exponent at progress `p` (0 -> 1, clamped) of a morph from `start`
    to `end`, travelling evenly on a log scale so the corners round off at a
    steady rate instead of all at the very end."""
    return vb.log_lerp(start, end, vb.clamp01(p))


def draw_squircle_morph(cv, cx, cy, w, h, p, color, start=SQUARE, end=CIRCLE, rotation=0.0, alpha=1.0):
    """Fill the shape `p` (0 -> 1) of the way from exponent `start` to `end`
    (square to circle by default), in the `w` x `h` box centred at (cx, cy).
    Ease `p` yourself. Returns the exponent drawn."""
    e = squircle_exponent(p, start, end)
    vb.paths.draw(cv, squircle(cx, cy, w, h, e, rotation=rotation), color, fill=True, alpha=alpha)
    return e


def _gentle(p):
    """A soft sine ease-in-out: no lurch, so the log-scale exponent keeps its steady pace."""
    return 0.5 - 0.5 * math.cos(math.pi * p)


def draw(n, cv):
    cx, cy, size = demo.W / 2, demo.H / 2 - 30, 380
    # two gentle legs with a long rest at the classic squircle between them, so the namesake
    # shape holds the screen (and the poster frame, 70% in) rather than flashing past
    to_squircle = _gentle(demo.phase(n, 0.2, 1.2))
    to_circle = _gentle(demo.phase(n, 2.2, 2.7))
    # faint guides: where it starts (square) and where it lands (circle)
    cv.outline(cx - size / 2, cy - size / 2, size, size, demo.LINE, width=2)
    cv.arc(cx, cy, size / 2, 0, 2 * math.pi, demo.LINE, width=2)
    if to_circle > 0:
        e = draw_squircle_morph(cv, cx, cy, size, size, to_circle, demo.ACCENT, start=SQUIRCLE, end=CIRCLE)
    else:
        e = draw_squircle_morph(cv, cx, cy, size, size, to_squircle, demo.ACCENT, start=SQUARE, end=SQUIRCLE)
    cv.mark('shape', cx - size / 2, cy - size / 2, size, size)
    label = 'square' if e > 12 else 'circle' if e < 2.15 else 'squircle'
    demo.word(cv, f'{label}   n = {e:4.1f}', cx, cy + size / 2 + 70, size=36, color=demo.MUTED,
              font=demo.mono(36, 600))


CAPABILITY = Capability(
    id='squircle-morph',
    name='Squircle morph',
    family='shapes',
    group='Shape morphing',
    aliases=('superellipse morph', 'square to circle morph', 'rounded square morph'),
    definition='A filled square softens its corners into a squircle and keeps rounding until it is a '
               'circle, one continuous shape changing its curvature rather than cross-fading.',
    phrasings=('the square smoothly rounds off into a circle',
               'morph a box into a circle through that soft app-icon shape',
               'corners melt away until the square becomes a dot'),
    related=('text-to-shape-morph', 'circle-pop', 'julia-set-morph', 'letter-morph', 'particle-morph',
             'shape-morph-loader'),
    api=('videobuilder.capabilities.shapes.squircle_morph.draw_squircle_morph',
         'videobuilder.capabilities.shapes.squircle_morph.squircle',
         'videobuilder.capabilities.shapes.squircle_morph.squircle_exponent'),
    demo=lambda: demo.film(draw),
)
