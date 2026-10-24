"""Extrusion Depth Reveal: the same flat-outline-pushed-back-into-a-growing-
solid move as Extrusion (`../camera/extrusion.py`, which keeps the
capability), on type rather than shapes: flat type grows a solid side, the
depth pushing out from behind each letter until the word stands as a block.
This module's own code stays (a film may still import it), but it is no
longer a capability of its own."""
import math

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'extrusion'


def _shade(color, k):
    """`color` darkened towards black by `k` (0 -> 1), as an (r, g, b) tuple."""
    r, g, b, _ = vb.rgba(color)
    return tuple(round(c * 255 * (1 - k)) for c in (r, g, b))


def draw_extruded(cv, text, font, x, y, depth, color, side, angle=45.0, shade=0.45, step=1.0):
    """Draw `text` from its top-left (x, y) as extruded type: the face in
    `color`, with a solid side `depth` px deep running away at `angle` degrees
    (0 is to the right, 90 straight down), in `side`, darkening by up to
    `shade` towards the back. Animate `depth` from 0 to reveal it. The side is
    stacked copies `step` px apart, so the face never moves. Returns the Box
    of the face."""
    dx, dy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    slices = math.ceil(max(0.0, depth) / step)
    for i in range(slices, 0, -1):
        d = min(i * step, depth)
        vb.text.draw(cv, [text], font, x + dx * d, y + dy * d, _shade(side, shade * d / max(depth, 1e-9)))
    return vb.text.draw(cv, [text], font, x, y, color)


def depth_at(p, depth, ease=vb.ease_out_quint):
    """The extrusion depth at progress `p` (0 -> 1): eased from 0 to `depth`."""
    return depth * ease(vb.clamp01(p))


DEPTH = 80
ANGLE = 50


def draw(n, cv):
    f = demo.font(190, 900)
    text = 'DEPTH'
    w, h = vb.text.block_size([text], f)
    # centre the finished block, face plus its full side
    x = (demo.W - w - DEPTH * math.cos(math.radians(ANGLE))) / 2
    y = (demo.H - h - DEPTH * math.sin(math.radians(ANGLE))) / 2
    d = depth_at(demo.phase(n, 0.4, 2.4), DEPTH, ease=vb.ease_in_out_quart)
    box = draw_extruded(cv, text, f, x, y, d, demo.INK, demo.TEAL, angle=ANGLE)
    cv.mark('text', *box)
