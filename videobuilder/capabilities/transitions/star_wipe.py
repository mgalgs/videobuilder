"""Star wipe: the incoming scene shows through a star that opens from a point
in the frame and grows, turning a little, until it covers the outgoing one."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...canvas import rgba
from ..schema import Capability


def star_points(cx, cy, r, points=5, inner=0.45, turn=0.0):
    """The outline of a `points`-pointed star centred at (cx, cy): tips at
    radius `r`, notches at `r * inner`, first tip straight up, then rotated
    by `turn` radians. A list of (x, y)."""
    out = []
    for i in range(points * 2):
        rad = r if i % 2 == 0 else r * inner
        a = -math.pi / 2 + turn + i * math.pi / points
        out.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return out


def star_wipe(cv, a, b, p, cx=None, cy=None, points=5, inner=0.45, spin=0.35, ease=vb.bezier(0.45, 0, 0.6, 1),
              edge=None, edge_width=6):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` full frame, with `b(cv)`
    inside a star centred at (cx, cy) (default the frame centre) that grows
    from nothing until even its notches clear every corner, turning `spin`
    radians on the way. `edge`, if given, strokes the star's outline in that
    colour, `edge_width` px wide.

    In a film, call it while two shots are live in an overlap, e.g.
    `star_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    w, h = cv.width, cv.height
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    # The notches are the star's nearest edge, so they set the size that covers the frame.
    reach = max(math.hypot(x - cx, y - cy) for x, y in ((0, 0), (w, 0), (0, h), (w, h)))
    e = ease(vb.clamp01(p))
    pts = star_points(cx, cy, e * reach / inner * 1.05, points, inner, spin * e)
    a(cv)
    c = cv.ctx
    c.save()
    _path(c, pts)
    c.clip()
    b(cv)
    c.restore()
    if edge:
        _path(c, pts)
        c.set_source_rgba(*rgba(edge))
        c.set_line_width(edge_width)
        c.stroke()


def _path(c, pts):
    c.new_path()
    c.move_to(*pts[0])
    for pt in pts[1:]:
        c.line_to(*pt)
    c.close_path()


CAPABILITY = Capability(
    id='star-wipe',
    name='Star wipe',
    family='transitions',
    group='Wipes',
    aliases=('star iris', 'star reveal', 'star transition'),
    definition='A star shape opens up in the middle of the old shot and grows, turning slightly, '
               'with the new shot inside it, until the new shot fills the frame.',
    phrasings=('go to the next scene through a growing star',
               'do that cheesy star transition between the two shots',
               'reveal the next slide inside an expanding star'),
    related=('circular-clip-reveal', 'star-rating-fill', 'zoom-out-reveal', 'tumble', 'logo-mask-wipe-reveal',
             'uncover'),
    api=('videobuilder.capabilities.transitions.star_wipe.star_wipe',
         'videobuilder.capabilities.transitions.star_wipe.star_points'),
    demo=lambda: demo.two_scenes(lambda cv, a, b, p: star_wipe(cv, a, b, p, edge=demo.ACCENT)),
)
