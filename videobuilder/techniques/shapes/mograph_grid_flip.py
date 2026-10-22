"""Mograph grid flip: a picture cut into a grid of tiles, each tile turning
over on its own axis in a wave across the grid, so the picture on the tiles'
backs takes over tile by tile."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

TURN = vb.bezier(0.6, 0.0, 0.3, 1.0)


def grid_flip(cv, front, back, p, box=None, cols=8, rows=4, gap=8, radius=6, stagger=0.65, depth=0.22,
              lift=0.08, shade=0.55, ease=TURN, gap_color=None):
    """Draw the grid at progress `p` (0 -> 1): `front(cv)` and `back(cv)` each
    draw a whole scene in frame coordinates; every tile of `box` (default the
    frame) shows its own patch of one or the other. Tiles turn 180 degrees
    about their vertical axis in a diagonal wave from the top left, each
    starting `stagger` (a fraction of the run) after the first and lasting
    the rest. While a tile turns, its leading edge grows by `depth` and the
    trailing one shrinks (a cheap perspective), the tile swells by `lift` and
    darkens by up to `shade` as it goes edge-on. `gap` px separate the tiles
    over `gap_color` (default: whatever is already on the canvas).

    It has the `transition(cv, a, b, p)` shape, so a film can call it inside
    an overlap as `grid_flip(cv, a, b, p)`."""
    x0, y0, bw, bh = box if box is not None else (0, 0, cv.width, cv.height)
    if gap_color is not None:
        cv.rect(x0, y0, bw, bh, gap_color)
    tw, th = (bw - gap * (cols - 1)) / cols, (bh - gap * (rows - 1)) / rows
    span = max(1, cols + rows - 2)
    c = cv.ctx
    for r in range(rows):
        for k in range(cols):
            t = vb.clamp01((p - stagger * (r + k) / span) / (1 - stagger)) if stagger < 1 else float(p >= 1)
            angle = math.pi * ease(t)
            cos, sin = math.cos(angle), math.sin(angle)
            cx, cy = x0 + k * (tw + gap) + tw / 2, y0 + r * (th + gap) + th / 2
            grow = 1 + lift * sin
            hw, hh = tw / 2 * abs(cos) * grow, th / 2 * grow
            if hw < 0.5:
                continue
            # The right edge swings toward us on the first half of the turn and away on the second.
            near, far = hh * (1 + depth * sin), hh * (1 - depth * sin)
            left_h, right_h = (far, near) if cos > 0 else (near, far)
            c.save()
            c.move_to(cx - hw, cy - left_h)
            c.line_to(cx + hw, cy - right_h)
            c.line_to(cx + hw, cy + right_h)
            c.line_to(cx - hw, cy + left_h)
            c.close_path()
            c.clip()
            c.translate(cx, cy)
            c.scale(abs(cos) * grow, grow * (1 + depth * sin * 0.5))
            c.translate(-cx, -cy)
            with cv.clip(cx - tw / 2, cy - th / 2, tw, th, radius):
                (front if cos > 0 else back)(cv)
                if sin > 0.01:
                    cv.fill('#000000', alpha=shade * sin)
            c.restore()


def draw(n, cv):
    pad = 110
    box = (pad, pad * 0.8, demo.W - 2 * pad, demo.H - 1.6 * pad)
    grid_flip(cv, demo.scene_a, demo.scene_b, demo.phase(n, 0.35, 2.55), box=box, cols=8, rows=4, gap=10)
    cv.mark('grid', *box)


TECHNIQUE = Technique(
    id='mograph-grid-flip',
    name='Mograph grid flip',
    family='shapes',
    group='Repeaters & patterns',
    aliases=('tile flip wave', 'cloner flip', 'flipping tiles', 'grid card flip'),
    definition='An image split into a grid of tiles turns over one tile at a time in a sweeping wave, '
               'each tile showing a new picture on its back.',
    phrasings=('break the picture into squares that flip over one after another to show the next one',
               'a wall of tiles turning over in a wave across the screen',
               'flip the grid of cards diagonally to reveal the new image'),
    related=('tile-flip', 'flip', 'cloner-grid', 'layout-animation-flip', 'logo-3d-spin-reveal',
             'character-3d-flip'),
    api=('videobuilder.techniques.shapes.mograph_grid_flip.grid_flip',),
    demo=lambda: demo.film(draw),
)
