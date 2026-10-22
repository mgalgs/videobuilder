"""Rotating Polygon Loop: regular polygons turn by exactly one vertex step
each cycle, so the last frame matches the first and the motion repeats
seamlessly."""
import math

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique


def loop_angle(t, sides, period, ease=vb.ease_in_out_quart, direction=1, offset=0.0):
    """The rotation in radians of a regular `sides`-gon at time `t` seconds:
    each `period` it turns one symmetry step (2 pi / `sides`), eased by `ease`
    within the step, so any whole number of periods loops cleanly.
    `direction` is 1 (clockwise) or -1; `offset` shifts this shape's timing in
    seconds, for staggering nested shapes."""
    u = (t - offset) / period
    k = math.floor(u)
    return direction * (k + ease(u - k)) * 2 * math.pi / sides


def polygon_points(cx, cy, r, sides, angle=0.0):
    """The vertices of a regular `sides`-gon of circumradius `r` centred at
    (cx, cy), turned by `angle` radians; at 0 the first vertex points up."""
    return [(cx + r * math.cos(angle - math.pi / 2 + i * 2 * math.pi / sides),
             cy + r * math.sin(angle - math.pi / 2 + i * 2 * math.pi / sides)) for i in range(sides)]


def draw_polygon(cv, cx, cy, r, sides, angle=0.0, color=demo.INK, width=None, alpha=1.0):
    """A regular polygon on `cv`: stroked `width` px wide with mitred corners,
    or filled when `width` is None. Returns its vertices."""
    pts = polygon_points(cx, cy, r, sides, angle)
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(*rgba(color, alpha))
    if width is None:
        c.fill()
    else:
        c.set_line_width(width)
        c.set_line_join(cairo.LINE_JOIN_MITER)
        c.stroke()
    return pts


PERIOD = 1.5  # two full cycles in the 3 s demo
RINGS = ((6, 215, demo.ACCENT), (5, 160, demo.TEAL), (4, 108, demo.INK), (3, 60, demo.ACCENT))


def draw(n, cv):
    t = n / demo.FPS
    cx, cy = demo.W / 2, demo.H / 2
    for i, (sides, r, color) in enumerate(RINGS):
        a = loop_angle(t, sides, PERIOD, direction=1 if i % 2 == 0 else -1, offset=0.08 * i)
        if i == len(RINGS) - 1:
            draw_polygon(cv, cx, cy, r, sides, a, color)
        else:
            draw_polygon(cv, cx, cy, r, sides, a, color, width=9)
    cv.mark('polygons', cx - 215, cy - 215, 430, 430)


TECHNIQUE = Technique(
    id='rotating-polygon-loop',
    name='Rotating polygon loop',
    family='shapes',
    group='Geometric & Swiss style',
    aliases=('spinning polygons', 'polygon spin loop', 'nested polygon rotation', 'geometric spinner'),
    definition='Nested regular polygons each turn by one corner-to-corner step per beat, '
               'alternating direction, so the pattern snaps round and repeats without a visible seam.',
    phrasings=('a few geometric shapes inside each other that keep spinning in a loop',
               'triangles, squares and hexagons rotating against each other on repeat',
               'a looping spinner made of nested polygons'),
    related=('geometric-loop', 'cycle-diagram-rotation', 'turntable-rotation', 'tessellation-triangle-flip',
             'coin-flip', 'globe-spin'),
    api=('videobuilder.techniques.shapes.rotating_polygon_loop.loop_angle',
         'videobuilder.techniques.shapes.rotating_polygon_loop.draw_polygon',
         'videobuilder.techniques.shapes.rotating_polygon_loop.polygon_points'),
    demo=lambda: demo.film(draw),
)
