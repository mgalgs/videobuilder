"""Dimension line annotation: thin extension lines rise off two edges of an
object, a measuring line runs between them with arrowheads at either end, and
the measurement pops in at its midpoint -- the drafting-table way of saying
"this is how big it is"."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _arrowhead(cv, x, y, ux, uy, color, size, alpha):
    """A filled arrowhead with its tip at (x, y), pointing along unit (ux, uy)."""
    px, py = -uy, ux
    bx, by = x - ux * size, y - uy * size
    pts = [(x, y), (bx + px * size * 0.42, by + py * size * 0.42), (bx - px * size * 0.42, by - py * size * 0.42)]
    ctx = cv.ctx
    ctx.save()
    ctx.new_path()
    ctx.move_to(*pts[0])
    for pt in pts[1:]:
        ctx.line_to(*pt)
    ctx.close_path()
    ctx.set_source_rgba(*vb.canvas.rgba(color, alpha))
    ctx.fill()
    ctx.restore()


def dimension_line(cv, a, b, p, label=None, offset=60, color=demo.ACCENT, font=None, ink=None,
                   width=3, tick=22, head=16, gap=14):
    """Draw a dimension line measuring from point `a` to point `b` (two (x, y)
    points on an object's edge) at progress `p` (0 -> 1), over what is
    already on `cv`. The line sits `offset` px to the left of the direction
    a -> b (negative for the other side). Over the first quarter the two
    extension lines grow out from the object; then the measuring line grows
    from its midpoint to both ends; at the ends, arrowheads and end ticks
    snap in, and `label` pops in at the midpoint, the line parting around it.
    `font` defaults to a bold 30 px kit font, `ink` to `color`. Returns the
    label's Box, or None while it is hidden."""
    (ax, ay), (bx, by) = a, b
    length = math.hypot(bx - ax, by - ay)
    if length <= 0 or p <= 0:
        return None
    ux, uy = (bx - ax) / length, (by - ay) / length
    nx, ny = uy, -ux                       # the side the line sits on
    sa, sb = (ax + nx * offset, ay + ny * offset), (bx + nx * offset, by + ny * offset)
    mx, my = (sa[0] + sb[0]) / 2, (sa[1] + sb[1]) / 2
    sign = 1 if offset >= 0 else -1

    ext = vb.ease_out_quint(vb.clamp01(p / 0.25))
    reach = (abs(offset) + tick * 0.6) * ext
    for (ex, ey) in (a, b):                # extension lines, from just off the edge outward
        x0, y0 = ex + nx * sign * 8, ey + ny * sign * 8
        cv.line(x0, y0, x0 + nx * sign * max(0, reach - 8), y0 + ny * sign * max(0, reach - 8),
                color, width=max(1, width - 1), alpha=0.55 * ext)

    run = vb.ease_in_out_quart(vb.clamp01((p - 0.15) / 0.5))
    snap = vb.ease_out_back(vb.clamp01((p - 0.6) / 0.25))
    pop = vb.ease_out_back(vb.clamp01((p - 0.68) / 0.32))

    half = length / 2 * run
    hole = 0.0
    box = None
    if label and pop > 0:
        f = font or demo.font(30, 800)
        tw, th = vb.text.block_size([label], f)
        hole = (tw if abs(ux) >= abs(uy) else th) / 2 + gap
        hole = min(hole * vb.clamp01(pop), length / 2 - head)
        k = 0.6 + 0.4 * pop                # grows about the midpoint as it pops
        with cv.layer(opacity=vb.clamp01(pop * 1.5), dx=mx * (1 - k), dy=my * (1 - k), scale=k):
            vb.text.draw(cv, [label], f, mx - tw / 2, my - th / 2, ink or color)
        box = vb.Box(mx - tw / 2, my - th / 2, tw, th)
        cv.mark('label', *box)
    for d in (-1, 1):                      # the two halves, from the label gap outward
        if half > hole:
            cv.line(mx + ux * d * hole, my + uy * d * hole, mx + ux * d * half, my + uy * d * half,
                    color, width=width)
    if snap > 0:
        for (ex, ey), d in ((sa, -1), (sb, 1)):
            t = tick / 2 * snap
            cv.line(ex - nx * t, ey - ny * t, ex + nx * t, ey + ny * t, color, width=width)
            _arrowhead(cv, ex, ey, ux * d, uy * d, color, head * snap, vb.clamp01(snap))
    return box


def draw(n, cv):
    w, h = 620, 300
    x, y = (demo.W - w) / 2 + 40, (demo.H - h) / 2 - 10
    demo.card(cv, x + w / 2, y + h / 2, w=w, h=h, color=demo.TEAL)
    pw = demo.phase(n, 0.3, 1.9)
    count = vb.ease_out_quint(vb.clamp01((pw - 0.68) / 0.32))
    dimension_line(cv, (x, y + h), (x + w, y + h), pw, label=f'{round(1920 * count)} px', offset=-70)
    ph = demo.phase(n, 0.9, 2.5)
    count = vb.ease_out_quint(vb.clamp01((ph - 0.68) / 0.32))
    dimension_line(cv, (x, y + h), (x, y), ph, label=f'{round(1080 * count)}', offset=70, color=demo.INK)


CAPABILITY = Capability(
    id='dimension-line-annotation',
    name='Dimension line annotation',
    family='broadcast',
    group='Annotation',
    aliases=('measurement callout', 'size markers', 'measure line'),
    definition='A thin measuring line with arrowheads and end ticks stretches along one side of an '
               'object, and the size it measures pops up in a gap at its middle.',
    phrasings=('show how wide the box is with a measuring line and the number in the middle',
               'add a technical-drawing style width marker under the product',
               'draw size arrows along the edges and label them with the measurements'),
    related=('callout-highlight', 'line-chart-draw-on', 'sparkline-draw', 'slopegraph-reveal',
             'parallel-coordinates-draw', 'streamlines'),
    api=('videobuilder.capabilities.broadcast.dimension_line_annotation.dimension_line',),
    demo=lambda: demo.film(draw),
)
