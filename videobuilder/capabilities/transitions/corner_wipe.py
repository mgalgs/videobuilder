"""Corner wipe: the incoming scene grows out of one corner of the frame as a
quarter circle, its curved edge sweeping across until it covers everything."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

CORNERS = ('top-left', 'top-right', 'bottom-left', 'bottom-right')


def corner_wipe(cv, a, b, p, corner='top-left', ease=vb.ease_in_out_quart, edge=None, edge_width=6):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` underneath, `b(cv)`
    clipped to a circle centred on `corner` whose radius eases from 0 to the
    frame's diagonal. `edge`, a colour, strokes the moving curved edge.

    In a film, call it while two shots are live in an overlap, e.g.
    `corner_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    if corner not in CORNERS:
        raise ValueError(f'corner must be one of {", ".join(CORNERS)}, not {corner!r}')
    w, h = cv.width, cv.height
    cx = 0 if corner.endswith('left') else w
    cy = 0 if corner.startswith('top') else h
    r = ease(vb.clamp01(p)) * math.hypot(w, h)
    a(cv)
    if r <= 0:
        return
    c = cv.ctx
    c.save()
    c.new_path()
    c.arc(cx, cy, r, 0, 2 * math.pi)
    c.clip()
    try:
        b(cv)
    finally:
        c.restore()
    if edge is not None and r < math.hypot(w, h):
        c.save()
        c.new_path()
        c.arc(cx, cy, r, 0, 2 * math.pi)
        c.set_source_rgba(*vb.rgba(edge, 1.0))
        c.set_line_width(edge_width)
        c.stroke()
        c.restore()


CAPABILITY = Capability(
    id='corner-wipe',
    name='Corner wipe',
    family='transitions',
    group='Wipes',
    aliases=('corner reveal', 'corner expand', 'quarter-circle wipe'),
    definition='The next scene spreads out from one corner of the screen in a growing curve '
               'until it covers the whole frame.',
    phrasings=('reveal the next shot from the top-left corner',
               'have the new scene grow out of a corner and take over the screen',
               'a round wipe that starts in the corner'),
    related=('uncover', 'roll-up', 'zoom-out-reveal', 'slide-over-cover', 'paint-brush-wipe', 'tumble'),
    api=('videobuilder.capabilities.transitions.corner_wipe.corner_wipe',),
    demo=lambda: demo.two_scenes(lambda cv, a, b, p: corner_wipe(cv, a, b, p, edge=demo.ACCENT)),
)
