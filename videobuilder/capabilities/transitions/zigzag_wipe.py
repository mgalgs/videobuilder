"""Zigzag wipe: the incoming scene pushes in behind a saw-tooth edge that
travels across the frame, its teeth pointing the way it moves."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _teeth(x, height, teeth, depth):
    """The zigzag boundary top to bottom: `teeth` points `depth` deep whose
    tips reach `x`."""
    step = height / teeth
    pts = [(x - depth, -1)]
    for i in range(teeth):
        pts += [(x, (i + 0.5) * step), (x - depth, (i + 1) * step)]
    pts[-1] = (x - depth, height + 1)
    return pts


def zigzag_wipe(cv, a, b, p, teeth=9, depth=None, ease=vb.ease_in_out_quart, edge_color=None, edge_width=6,
                reverse=False):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` in full, then `b(cv)`
    clipped to the side of a saw-tooth edge that sweeps left to right (right to
    left with `reverse`). `teeth` is how many points run down the edge, `depth`
    how far each juts (default one tooth's height); `edge_color`, when given,
    strokes the edge so it reads against similar scenes.

    In a film, call it while two shots are live in an overlap, e.g.
    `zigzag_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    w = cv.width
    depth = cv.height / teeth if depth is None else depth
    x = -1 + (w + depth + 2) * ease(vb.clamp01(p))  # tips from just off the left to the base past the right
    pts = _teeth(x, cv.height, teeth, depth)
    if reverse:
        pts = [(w - px, py) for px, py in pts]
    side = -1 if not reverse else w + 1
    c = cv.ctx
    a(cv)
    c.save()
    c.new_path()
    c.move_to(side, -1)
    for pt in pts:
        c.line_to(*pt)
    c.line_to(side, cv.height + 1)
    c.close_path()
    c.clip()
    b(cv)
    c.restore()
    if edge_color is not None:
        c.save()
        c.new_path()
        c.move_to(*pts[0])
        for pt in pts[1:]:
            c.line_to(*pt)
        c.set_source_rgba(*vb.canvas.rgba(edge_color))
        c.set_line_width(edge_width)
        c.set_line_join(0)  # miter: keep the points sharp
        c.stroke()
        c.restore()


CAPABILITY = Capability(
    id='zigzag-wipe',
    name='Zigzag wipe',
    family='transitions',
    group='Wipes',
    aliases=('saw-tooth wipe', 'sawtooth wipe', 'jagged wipe'),
    definition='The next scene slides in behind a line of sharp triangular teeth that travels '
               'across the screen, so the cut between the two shots is a jagged saw edge.',
    phrasings=('wipe to the next shot with a jagged zigzag edge',
               'a sawtooth line that sweeps across and reveals the next scene',
               'transition with a spiky edge moving left to right'),
    related=('zig-zag-distortion', 'paint-brush-wipe', 'wipe-reveal', 'ribbon-sweep', 'accordion-fold',
             'smoke-dissolve'),
    api=('videobuilder.capabilities.transitions.zigzag_wipe.zigzag_wipe',),
    demo=lambda: demo.two_scenes(lambda cv, a, b, p: zigzag_wipe(cv, a, b, p, edge_color=demo.ACCENT)),
)
