"""Area Fill Sweep: an area chart is revealed from left to right, the shaded
region under the line filling in behind a moving vertical edge."""
import math

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def swept(points, p):
    """The part of the left-to-right polyline `points` at or left of the sweep
    edge at progress `p` (0 -> 1 across its x span), ending exactly on the edge."""
    p = vb.clamp01(p)
    x0, x1 = points[0][0], points[-1][0]
    sx = x0 + (x1 - x0) * p
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        if b[0] <= sx:
            out.append(b)
            continue
        t = (sx - a[0]) / (b[0] - a[0]) if b[0] != a[0] else 0.0
        out.append((sx, a[1] + (b[1] - a[1]) * t))
        break
    return out


def area_fill_sweep(cv, points, base_y, p, color, line_color=None, width=4, fill_alpha=0.55,
                    edge=True, edge_color=None):
    """Draw the area chart under `points` (left to right, (x, y) in px) down
    to the baseline `base_y`, revealed to progress `p` (0 -> 1): the shaded
    area fades from `fill_alpha` at the line to clear at the baseline, the
    line is stroked `width` px in `line_color` (default `color`), and with
    `edge` a thin bright rule and a dot ride the leading edge while it moves.
    Returns the (x, y) of the sweep head."""
    pts = swept(points, p)
    head = pts[-1]
    if len(pts) < 2 or head[0] <= pts[0][0]:
        return head
    c = cv.ctx
    top = min(y for _, y in points)
    c.new_path()
    c.move_to(pts[0][0], base_y)
    for x, y in pts:
        c.line_to(x, y)
    c.line_to(head[0], base_y)
    c.close_path()
    grad = cairo.LinearGradient(0, top, 0, base_y)
    grad.add_color_stop_rgba(0, *rgba(color, fill_alpha))
    grad.add_color_stop_rgba(1, *rgba(color, fill_alpha * 0.08))
    c.set_source(grad)
    c.fill()
    vb.paths.draw(cv, pts, line_color or color, width=width)
    if edge and p < 1:
        ink = edge_color or line_color or color
        cv.line(head[0], head[1], head[0], base_y, ink, width=2, alpha=0.8)
        demo.dot(cv, head[0], head[1], r=width * 2.2, color=ink)
    return head


def _series(x0, x1, n=40):
    """A smooth, rising-with-dips curve sampled as heights 0..1."""
    out = []
    for i in range(n + 1):
        t = i / n
        v = 0.18 + 0.55 * t + 0.12 * math.sin(t * 9.0) + 0.06 * math.sin(t * 23.0 + 1.0)
        out.append((x0 + (x1 - x0) * t, v))
    return out


def draw(n, cv):
    left, right, top, base = demo.W * 0.12, demo.W * 0.88, demo.H * 0.16, demo.H * 0.84
    for i in range(5):
        y = base - (base - top) * i / 4
        cv.line(left, y, right, y, demo.LINE, width=2)
    demo.floor(cv, base)
    cv.line(left, top - 10, left, base, demo.MUTED, width=3)
    pts = [(x, base - (base - top) * v) for x, v in _series(left, right)]
    p = vb.ease_in_out_quart(demo.phase(n, 0.3, 2.4))
    area_fill_sweep(cv, pts, base, p, demo.TEAL, width=5, edge_color=demo.INK)
    cv.mark('chart', left, top, right - left, base - top)


CAPABILITY = Capability(
    id='area-fill-sweep',
    name='Area fill sweep',
    family='broadcast',
    group='Charts',
    aliases=('area chart reveal', 'area chart wipe-on', 'area chart build'),
    definition='An area chart builds from left to right, its line and the shading beneath it '
               'appearing together behind a moving vertical edge.',
    phrasings=('animate the area chart filling in from left to right',
               'reveal the shaded graph like it is being drawn across the screen',
               'sweep the area under the line in over time'),
    related=('shape-fill-sweep', 'fill-sweep-button', 'choropleth-fill', 'scanline-wipe', 'wipe-reveal',
             'diagonal-wipe'),
    api=('videobuilder.capabilities.broadcast.area_fill_sweep.area_fill_sweep',
         'videobuilder.capabilities.broadcast.area_fill_sweep.swept'),
    demo=lambda: demo.film(draw),
)
