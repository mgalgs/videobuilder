"""Iris wipe: the incoming scene opens out of a circle that grows from a point
until it covers the frame (or, closing, the outgoing scene shrinks away into
a circle with the incoming one around it)."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def iris_wipe(cv, a, b, p, cx=None, cy=None, close=False, rim=None, rim_width=6, ease=vb.ease_in_out_quart):
    """Draw the iris at progress `p` (0 -> 1). Opening (the default), `b(cv)`
    shows inside a circle centred at (`cx`, `cy`) (default the frame's centre)
    that grows from nothing to just past the farthest corner, over `a(cv)`.
    With `close=True`, `a` shrinks away inside the circle instead, `b` around
    it. `rim`, a colour, strokes the circle's edge; `ease` shapes the motion.

    In a film, call it while two shots are live in an overlap, e.g.
    `iris_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    W, H = cv.width, cv.height
    cx = W / 2 if cx is None else cx
    cy = H / 2 if cy is None else cy
    reach = max(math.hypot(x - cx, y - cy) for x in (0, W) for y in (0, H)) + rim_width
    e = ease(vb.clamp01(p))
    r = reach * (1 - e if close else e)
    outside, inside = (b, a) if close else (a, b)
    outside(cv)
    if r <= 0:
        return
    c = cv.ctx
    c.save()
    c.new_path()
    c.arc(cx, cy, r, 0, 2 * math.pi)
    c.clip()
    inside(cv)
    c.restore()
    if rim is not None:
        cv.arc(cx, cy, r, 0, 2 * math.pi, rim, width=rim_width)


def _demo():
    # Iris in from A to B, hold, then iris out back to A, so both forms show
    # and the clip loops. The closing iris is mid-way at the poster frame
    # (70% = 2.1 s): Scene B sits in a red-rimmed circle with A around it.
    def draw(n, cv):
        p_in, p_out = demo.phase(n, 0.1, 1.1), demo.phase(n, 1.4, 2.8)
        if p_out > 0:
            iris_wipe(cv, demo.scene_b, demo.scene_a, p_out, close=True, rim=demo.ACCENT)
        else:
            iris_wipe(cv, demo.scene_a, demo.scene_b, p_in, rim=demo.ACCENT)
    return demo.film(draw)


CAPABILITY = Capability(
    id='iris-wipe',
    name='Iris wipe',
    family='transitions',
    group='Wipes',
    aliases=('iris in', 'iris out', 'circle wipe', 'iris transition'),
    definition='A circle opens from a point in the middle of the frame and keeps growing, '
               'showing the next scene inside it, until that scene fills the whole screen.',
    phrasings=('open the next shot out of a growing circle',
               'a round wipe from the centre into the new scene',
               'close the scene down to a circle like an old cartoon ending'),
    related=('circular-clip-reveal', 'paint-brush-wipe', 'wipe-reveal', 'logo-mask-wipe-reveal',
             'area-fill-sweep', 'circle-pop'),
    api=('videobuilder.capabilities.transitions.iris_wipe.iris_wipe',),
    demo=_demo,
)
