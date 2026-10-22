"""Diamond wipe: the incoming scene opens out of a point as a diamond (a
square turned 45 degrees) that grows until it fills the frame."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def diamond_wipe(cv, a, b, p, center=None, ease=vb.ease_in_out_quart, edge=None, edge_width=6):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` full frame, then
    `b(cv)` clipped to a diamond centred on `center` (default the frame's
    centre) whose size grows from nothing at `p` = 0 to just covering the
    frame at `p` = 1. `edge`, a colour, strokes the diamond's rim.

    In a film, call it while two shots are live in an overlap, e.g.
    `diamond_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    cx, cy = center if center is not None else (cv.width / 2, cv.height / 2)
    # |x - cx| + |y - cy| <= r covers the frame once r reaches the farthest corner's distance.
    reach = max(abs(x - cx) + abs(y - cy) for x in (0, cv.width) for y in (0, cv.height))
    r = reach * ease(vb.clamp01(p))
    a(cv)
    if r <= 0:
        return
    c = cv.ctx
    c.save()
    c.new_path()
    c.move_to(cx, cy - r)
    c.line_to(cx + r, cy)
    c.line_to(cx, cy + r)
    c.line_to(cx - r, cy)
    c.close_path()
    if edge is not None:
        c.set_source_rgba(*vb.canvas.rgba(edge))
        c.set_line_width(edge_width)
        c.stroke_preserve()
    c.clip()
    b(cv)
    c.restore()


CAPABILITY = Capability(
    id='diamond-wipe',
    name='Diamond wipe',
    family='transitions',
    group='Wipes',
    aliases=('diamond iris', 'rhombus wipe'),
    definition='The next scene appears inside a small diamond at the middle of the screen, '
               'and the diamond widens until it takes over the whole frame.',
    phrasings=('open the next shot through a growing diamond',
               'reveal the new scene with a diamond that expands from the center',
               'like an iris transition but diamond shaped'),
    related=('circular-clip-reveal', 'wipe-reveal', 'paint-brush-wipe', 'fill-sweep-button',
             'shape-fill-sweep', 'tessellation-triangle-flip'),
    api=('videobuilder.capabilities.transitions.diamond_wipe.diamond_wipe',),
    demo=lambda: demo.two_scenes(lambda cv, a, b, p: diamond_wipe(cv, a, b, p, edge=demo.ACCENT)),
)
