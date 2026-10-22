"""Icon State Morph: a line icon changes meaning by reshaping its own strokes
-- the three bars of a menu icon swing into the cross of a close icon, the
middle bar shrinking away -- instead of cutting from one glyph to the next."""
import math

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Technique

# Icons as stroke lists in a unit box (-1..1 each way, y down). A stroke is an
# open point list; `None` is a stroke the icon doesn't have, so another icon's
# stroke in that slot shrinks away to its own middle.
MENU = (((-0.8, -0.55), (0.8, -0.55)), ((-0.8, 0.0), (0.8, 0.0)), ((-0.8, 0.55), (0.8, 0.55)))
CLOSE = (((-0.62, -0.62), (0.62, 0.62)), None, ((-0.62, 0.62), (0.62, -0.62)))
BACK = (((-0.75, 0.0), (0.0, -0.7)), ((-0.75, 0.0), (0.8, 0.0)), ((-0.75, 0.0), (0.0, 0.7)))
CHECK = (((-0.75, 0.05), (-0.25, 0.55)), None, ((-0.25, 0.55), (0.8, -0.55)))
PLUS = (((0.0, -0.75), (0.0, 0.75)), None, ((-0.75, 0.0), (0.75, 0.0)))


def _collapsed(stroke):
    """`stroke` shrunk to a point at its middle (by arc length)."""
    mid = paths.reveal(stroke, 0.5)[-1]
    return [mid] * len(stroke)


def icon_morph(a, b, t, turn=0.0, n=24):
    """The strokes of icon `a` turning into icon `b` at `t` (0 -> 1, clamped),
    as `(points, presence)` pairs in the unit box. The icons pair stroke for
    stroke by slot (pad the shorter with `None`); each pair is resampled to
    `n` points and interpolated with `paths.morph`. A slot that is `None` on
    one side grows from, or shrinks to, its partner's middle, and its
    `presence` (0..1, for alpha) follows. `turn`: the whole icon rotates this
    many full turns across the morph, the classic flourish (0.5 = half a turn)."""
    t = vb.clamp01(t)
    k = max(len(a), len(b))
    a, b = tuple(a) + (None,) * (k - len(a)), tuple(b) + (None,) * (k - len(b))
    ang = 2 * math.pi * turn * t
    ca, sa = math.cos(ang), math.sin(ang)
    out = []
    for sa_, sb_ in zip(a, b):
        if sa_ is None and sb_ is None:
            continue
        presence = 1.0 if sa_ is not None and sb_ is not None else (1 - t if sb_ is None else t)
        pa = list(sa_) if sa_ is not None else _collapsed(sb_)
        pb = list(sb_) if sb_ is not None else _collapsed(sa_)
        pts = paths.morph(pa, pb, t, n=n)
        out.append(([(x * ca - y * sa, x * sa + y * ca) for x, y in pts], presence))
    return out


def draw_icon_morph(cv, a, b, t, cx, cy, size, color, width=None, turn=0.0, alpha=1.0):
    """Draw icon `a` morphing into icon `b` at `t`, centred on (cx, cy) and
    `size` px across, its strokes `width` px wide (default `size` / 9) with
    round caps. `t` is raw progress -- ease it first. See `icon_morph`.
    Returns the icon's Box."""
    width = width or size / 9
    half = size / 2
    for pts, presence in icon_morph(a, b, t, turn=turn):
        if presence <= 0.01:
            continue
        paths.draw(cv, [(cx + x * half, cy + y * half) for x, y in pts], color, width=width,
                   alpha=alpha * presence)
    return vb.Box(cx - half, cy - half, size, size)


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H / 2 - 30, 150
    there = vb.ease_in_out_quart(demo.phase(n, 0.5, 1.2))
    back = vb.ease_in_out_quart(demo.phase(n, 1.9, 2.6))
    t = there - back
    demo.dot(cv, cx, cy, r, color=demo.ACCENT)
    if back > 0:   # the return trip unwinds the half turn the other way
        box = draw_icon_morph(cv, CLOSE, MENU, back, cx, cy, 150, demo.INK, turn=-0.5)
    else:
        box = draw_icon_morph(cv, MENU, CLOSE, there, cx, cy, 150, demo.INK, turn=0.5)
    cv.mark('icon', *box)
    f = demo.font(34, 700)
    demo.word(cv, 'MENU', cx, cy + r + 70, font=f, color=demo.MUTED, alpha=1 - t)
    demo.word(cv, 'CLOSE', cx, cy + r + 70, font=f, color=demo.MUTED, alpha=t)


TECHNIQUE = Technique(
    id='icon-state-morph',
    name='Icon state morph',
    family='shapes',
    group='Icon animation',
    aliases=('icon morph', 'animated icon transition', 'hamburger to close', 'morphing icon'),
    definition='A line icon switches to a different icon by bending, turning and sliding its own strokes '
               'into the new shape, so the change of state reads as one continuous motion.',
    phrasings=('the menu button turns into an X when you tap it',
               'make the icon change into the other icon instead of just swapping',
               'the three lines twist into a close cross and back'),
    related=('play-pause-morph', 'text-to-shape-morph', 'chart-type-morph', 'loading-state-morph',
             'shared-element-transition', 'symbol-to-letter-decode'),
    api=('videobuilder.techniques.shapes.icon_state_morph.draw_icon_morph',
         'videobuilder.techniques.shapes.icon_state_morph.icon_morph',
         'videobuilder.paths.morph'),
    demo=lambda: demo.film(draw),
)
