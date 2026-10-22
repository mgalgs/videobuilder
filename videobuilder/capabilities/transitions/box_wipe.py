"""Box wipe: the incoming scene shows through a rectangle that opens from the
centre of the frame and grows until it fills it, covering the outgoing scene."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def box_wipe(cv, a, b, p, cx=0.5, cy=0.5, ease=vb.ease_in_out_quart, edge=None, edge_width=6, reverse=False):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` fills the frame and
    `b(cv)` shows inside a box with the frame's proportions, centred at
    (`cx`, `cy`) as fractions of the frame, growing from nothing to the whole
    frame. `edge`, a colour, strokes the box's border `edge_width` px wide.
    `reverse=True` closes instead: `a` shrinks away inside the box, `b` around it.

    In a film, call it while two shots are live in an overlap, e.g.
    `box_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    W, H = cv.width, cv.height
    s = ease(vb.clamp01(p))
    if reverse:
        a, b, s = b, a, 1 - s
    ox, oy = cx * W, cy * H
    # The box's sides head out from the centre at rates that reach every edge together.
    x0, x1 = ox * (1 - s), ox + (W - ox) * s
    y0, y1 = oy * (1 - s), oy + (H - oy) * s
    a(cv)
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        return
    with cv.clip(x0, y0, x1 - x0, y1 - y0):
        b(cv)
    if edge is not None and 0 < s < 1:
        cv.outline(x0, y0, x1 - x0, y1 - y0, edge, width=edge_width)


TECHNIQUE = Technique(
    id='box-wipe',
    name='Box wipe',
    family='transitions',
    group='Wipes',
    aliases=('box in', 'box out', 'iris box', 'rectangle wipe'),
    definition='A rectangle opens out from the middle of the picture and keeps growing to the edges, '
               'with the next scene inside it replacing the old one.',
    phrasings=('open the next shot as a growing square from the centre',
               'a rectangle expands out of the middle to bring in the new scene',
               'box out from the centre into the next clip'),
    related=('paint-brush-wipe', 'wipe-reveal', 'letterbox', 'uncover', 'scroll-linked-clip-reveal', 'roll-up'),
    api=('videobuilder.techniques.transitions.box_wipe.box_wipe',),
    demo=lambda: demo.two_scenes(lambda cv, a, b, p: box_wipe(cv, a, b, p, edge=demo.INK)),
)
