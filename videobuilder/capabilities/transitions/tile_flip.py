"""Tile flip: the frame splits into a grid of tiles that turn over one after
another in a diagonal wave, the outgoing scene on their fronts and the
incoming scene on their backs."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


REST = 0.02  # how near face-on (as a share of full width) a tile counts as resting


def tile_flip(cv, a, b, p, cols=8, rows=4, spread=0.55, axis='y', behind='#000000', shade=0.45):
    """Draw the flip at progress `p` (0 -> 1): the frame cut into `cols` x
    `rows` tiles, each turning half a revolution about its own `axis` ('y'
    spins left-right, 'x' tumbles top-bottom), showing `a(cv)` until edge-on
    and `b(cv)` after. Tiles start in a wave from the top-left corner; `spread`
    is the share of `p` that wave takes to cross the grid (0: all at once).
    `behind` shows in the gaps as tiles turn; `shade` darkens a tile as it
    turns away from the viewer.

    In a film, call it while two shots are live in an overlap, e.g.
    `tile_flip(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    W, H = cv.width, cv.height
    cv.fill(behind)
    c = cv.ctx
    span = max(1, cols + rows - 2)
    xs = [round(W * k / cols) for k in range(cols + 1)]  # whole-pixel edges, so resting tiles butt with no seam
    ys = [round(H * r / rows) for r in range(rows + 1)]
    for r in range(rows):
        for k in range(cols):
            delay = spread * (k + r) / span
            q = vb.ease_in_out_quart(vb.clamp01((p - delay) / (1 - spread)))
            squash = math.cos(math.pi * q)
            front = squash >= 0
            # within REST of face-on a tile is drawn flat; the turn is rescaled
            # from there so it leaves rest without a pop or a hairline gap
            s = min(1.0, abs(squash) / (1 - REST))
            if s < 1e-3:
                continue
            x, y, tw, th = xs[k], ys[r], xs[k + 1] - xs[k], ys[r + 1] - ys[r]
            if s < 1:
                cx, cy = x + tw / 2, y + th / 2
                lift = 1 + 0.12 * math.sqrt(1 - s * s)  # the turning tile swells a little, as if nearer
                sx, sy = (s, lift) if axis == 'y' else (lift, s)
                c.save()
                c.translate(cx, cy)
                c.scale(sx, sy)
                c.translate(-cx, -cy)
            # a turning tile reaches a pixel past its cell on the turning axis, so
            # the sub-pixel gap it opens as it leaves rest doesn't show as a seam
            pad = (1 if axis == 'y' else 0, 0 if axis == 'y' else 1) if s < 1 else (0, 0)
            with cv.clip(x - pad[0], y - pad[1], tw + 2 * pad[0], th + 2 * pad[1]):
                (a if front else b)(cv)
                if shade and s < 1:
                    cv.fill('#000000', alpha=shade * (1 - s))
            if s < 1:
                c.restore()

CAPABILITY = Capability(
    id='tile-flip',
    name='Tile flip',
    family='transitions',
    group='Shatter and Break',
    aliases=('grid flip', 'tile flip transition', 'mosaic flip', 'checkerboard flip'),
    definition='The picture breaks into a grid of squares that each turn over like cards in a rippling '
               'wave, and the backs of the squares together make up the next scene.',
    phrasings=('split the screen into tiles that flip over to show the next shot',
               'a wave of little panels turning around to reveal the new scene',
               'flip the image over block by block'),
    related=('flip', 'mograph-grid-flip', 'layout-animation-flip', 'tile-grid-title-reveal', 'word-flip-in',
             'tessellation-triangle-flip'),
    api=('videobuilder.capabilities.transitions.tile_flip.tile_flip',),
    demo=lambda: demo.two_scenes(tile_flip, start=1.2, length=1.6),
)
