"""Diagonal Wipe: a straight, slanted edge travels across the frame from one
corner side to the other; behind it is the incoming scene, ahead of it the
outgoing one."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...looks.kit import clip_to


def diagonal_wipe(cv, a, b, p, angle=30.0, ease=vb.ease_in_out_quart, edge=None, edge_width=8):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` everywhere, then
    `b(cv)` clipped to the side of a straight edge already swept past.

    `angle` is the direction the edge travels, in degrees clockwise from
    rightwards (30 sweeps from the top-left towards the bottom-right; 180 + 30
    runs the other way); the edge itself lies square to that. `ease` shapes
    its travel. `edge`, a colour, draws a line along the edge `edge_width` wide.

    In a film, call it while two shots are live in an overlap, e.g.
    `diagonal_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    w, h = cv.width, cv.height
    dx, dy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    reach = [x * dx + y * dy for x in (0, w) for y in (0, h)]
    pad = edge_width  # start and end with the edge line fully off frame
    s0, s1 = min(reach) - pad, max(reach) + pad
    s = s0 + (s1 - s0) * ease(vb.clamp01(p))
    cx, cy = dx * s, dy * s           # a point on the edge
    tx, ty = -dy, dx                  # along the edge
    far = 2 * (w + h)
    ends = [(cx + tx * far, cy + ty * far), (cx - tx * far, cy - ty * far)]
    behind = ends + [(x - dx * far, y - dy * far) for x, y in reversed(ends)]
    a(cv)
    with clip_to(cv, behind):
        b(cv)
    if edge:
        cv.line(*ends[0], *ends[1], edge, width=edge_width)


def transition(cv, a, b, p):
    diagonal_wipe(cv, a, b, p, edge=demo.ACCENT)


TECHNIQUE = Technique(
    id='diagonal-wipe',
    name='Diagonal wipe',
    family='transitions',
    group='Wipes',
    aliases=('angled wipe', 'slant wipe'),
    definition='A straight line tilted at an angle slides across the picture, '
               'and everything it has passed over already shows the next scene.',
    phrasings=('wipe to the next shot with a slanted edge',
               'sweep the new scene in on a diagonal, corner to corner',
               'an angled line crossing the screen that swaps one scene for the other'),
    related=('paint-brush-wipe', 'wipe-reveal', 'ribbon-sweep', 'area-fill-sweep', 'roll-up', 'flip'),
    api=('videobuilder.techniques.transitions.diagonal_wipe.diagonal_wipe',),
    demo=lambda: demo.two_scenes(transition),
)
