"""Checkerboard Wipe: the frame is cut into a grid of squares; half of them,
in a checker pattern, wipe across to the incoming scene first, then the other
half follow, until the whole board has turned over."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

_DIRS = {'right': (1, 0), 'left': (-1, 0), 'down': (0, 1), 'up': (0, -1)}


def _cell_part(x, y, w, h, q, direction):
    """The part of the cell (x, y, w, h) uncovered at progress `q`, wiping toward `direction`."""
    dx, dy = _DIRS[direction]
    if dx:
        ww = w * q
        return (x if dx > 0 else x + w - ww), y, ww, h
    hh = h * q
    return x, (y if dy > 0 else y + h - hh), w, hh


def checkerboard_wipe(cv, a, b, p, cols=8, rows=None, direction='right', overlap=0.25, ease=vb.ease_in_out_quart):
    """Draw the checkerboard wipe at progress `p` (0 -> 1): `a(cv)` underneath,
    `b(cv)` showing through a grid of `cols` x `rows` cells (`rows` defaults to
    whatever keeps the cells square). Cells of one checker colour wipe toward
    `direction` ('right', 'left', 'down' or 'up') first, the other colour
    second; `overlap` (0 -> 1) is how much the two passes run together.

    In a film, call it while two shots are live in an overlap, e.g.
    `checkerboard_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    if direction not in _DIRS:
        raise ValueError(f'checkerboard_wipe: direction must be one of {", ".join(_DIRS)}, not {direction!r}')
    W, H = cv.width, cv.height
    rows = rows or max(1, round(cols * H / W))
    cw, ch = W / cols, H / rows
    span = (1 + overlap) / 2              # each pass's share of p
    passes = [ease(vb.clamp01(p / span)), ease(vb.clamp01((p - (1 - span)) / span))]
    a(cv)
    if passes[0] <= 0:
        return
    c = cv.ctx
    c.save()
    for r in range(rows):
        for k in range(cols):
            q = passes[(r + k) % 2]
            if q > 0:
                # Cells overlap their neighbours by a hair so no seam of `a` shows once both passes land.
                c.rectangle(*_cell_part(k * cw, r * ch, cw + 0.5, ch + 0.5, q, direction))
    c.clip()
    try:
        b(cv)
    finally:
        c.restore()


CAPABILITY = Capability(
    id='checkerboard-wipe',
    name='Checkerboard wipe',
    family='transitions',
    group='Wipes',
    aliases=('checker wipe', 'checkerboard transition', 'checkerboard reveal'),
    definition='The screen is split into a grid of squares and the next scene wipes into every other '
               'square first, then into the squares between them, like a chessboard filling in.',
    phrasings=('change scenes with a chessboard pattern of squares',
               'wipe to the next shot in a checkered grid',
               'fill in alternating squares until the new scene is all there'),
    related=('wipe-reveal', 'paint-brush-wipe', 'fill-sweep-button', 'tile-grid-title-reveal',
             'area-fill-sweep', 'tile-flip'),
    api=('videobuilder.capabilities.transitions.checkerboard_wipe.checkerboard_wipe',),
    demo=lambda: demo.two_scenes(checkerboard_wipe, start=1.0, length=1.6),
)
