"""Shape Stacking Drop: blocks fall in from above one after another, each
landing on the one before with a small squash, until they stand as a tower."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def stack_drop(t, count, height, ground, top=-200.0, start=0.0, every=0.4, fall=0.4, settle=0.2):
    """Where each of `count` stacked blocks is at time `t` (seconds).

    Block `i` starts falling at `start + i * every` from bottom edge `top`,
    accelerating like a dropped object for `fall` seconds until its bottom
    edge rests on `ground - i * height` (on top of block `i - 1`). For
    `settle` seconds after it lands it squashes and recovers.

    Returns a list with one `(bottom_y, squash)` per block that has started
    (blocks not yet dropped are left off, so `len` is how many to draw):
    `bottom_y` is its bottom edge, `squash` runs 0 -> about 1 -> 0 over the
    landing; scale the block's width up and height down by a little of it.
    """
    out = []
    for i in range(count):
        local = t - (start + i * every)
        if local < 0:
            break
        rest = ground - i * height
        x = vb.clamp01(local / fall)
        y = top + (rest - top) * x * x  # constant acceleration from rest
        after = (local - fall) / settle
        squash = math.sin(math.pi * after) * (1 - after) * 1.6 if 0 < after < 1 else 0.0
        out.append((y, squash))
    return out


COLORS = (demo.ACCENT, demo.TEAL, demo.INK, '#f2b632', '#7c83f2')


def draw(n, cv):
    w, h, ground = demo.W * 0.18, demo.H * 0.1, demo.H * 0.84
    demo.floor(cv, ground)
    cx = demo.W / 2
    for i, (y, squash) in enumerate(stack_drop(n / demo.FPS, 5, h, ground, top=0,
                                                  start=0.1, every=0.45, fall=0.4)):
        bw, bh = w * (1 + 0.12 * squash), h * (1 - 0.14 * squash)
        x = cx - bw / 2 + w * (0.04 if i % 2 else -0.03)  # a slightly uneven, hand-stacked column
        cv.shadow(x, y - bh, bw, bh, radius=6, dy=4, blur=10, color=(0, 0, 0, 0.4))
        cv.rect(x, y - bh, bw, bh, COLORS[i % len(COLORS)], radius=6)
        cv.mark(f'block{i}', x, y - bh, bw, bh)


TECHNIQUE = Technique(
    id='shape-stacking-drop',
    name='Shape stacking drop',
    family='shapes',
    group='Explainer & infographic',
    aliases=('block stack', 'building block drop', 'tower build'),
    definition='Solid blocks drop in from above one after another, each landing with a little squash '
               'on top of the last, until they form a standing tower.',
    phrasings=('have the boxes fall in and pile up one on top of another',
               'build a tower by dropping blocks onto it one at a time',
               'drop the pieces in so they stack into a column'),
    related=('stacked-bar-build', 'stacked-line-build', 'rigid-body-pile', 'voxel-build', 'pyramid-build',
             'domino-toppling'),
    api=('videobuilder.techniques.shapes.shape_stacking_drop.stack_drop',),
    demo=lambda: demo.film(draw),
)
