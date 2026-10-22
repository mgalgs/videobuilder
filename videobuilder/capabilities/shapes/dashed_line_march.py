"""Marching Ants: a dashed stroke whose dashes slide steadily along the path
while the path itself stays put, as on a selection box or a route line."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def march_offset(t, speed=60.0, dash=18.0, gap=12.0):
    """The cairo dash offset at time `t` seconds for dashes travelling
    `speed` px/s forwards along the path (negative: backwards), wrapped to one
    dash period so it stays small however long the film runs."""
    return -(speed * t) % (dash + gap)


def draw_marching(cv, points, color, t, dash=18.0, gap=12.0, speed=60.0, width=3, closed=False,
                  under=None, alpha=1.0):
    """Stroke the point list `points` dashed, the dashes marching `speed` px/s
    along it at time `t` seconds. `under`: a colour stroked solid beneath, so
    the gaps show it (the two-tone selection look). Round caps make each dash
    a pill; the dash state is reset afterwards."""
    if under is not None:
        vb.paths.draw(cv, points, under, width=width, closed=closed, alpha=alpha)
    cv.ctx.set_dash([dash, gap], march_offset(t, speed, dash, gap))
    try:
        vb.paths.draw(cv, points, color, width=width, closed=closed, alpha=alpha)
    finally:
        cv.ctx.set_dash([])


def marching_rect(cv, x, y, w, h, color, t, **kw):
    """`draw_marching` around the box (x, y, w, h), clockwise from its top-left:
    a selection marquee. `kw` goes to `draw_marching`."""
    draw_marching(cv, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], color, t, closed=True, **kw)


def _route(x0, x1, y, amp, n=80):
    return [(x0 + (x1 - x0) * i / n, y + amp * math.sin(i / n * 2 * math.pi)) for i in range(n + 1)]


def draw(n, cv):
    t = n / demo.FPS
    cx, top = demo.W / 2, demo.H * 0.36
    demo.card(cv, cx, top, w=340, h=200)
    pad = 26
    marching_rect(cv, cx - 170 - pad, top - 100 - pad, 340 + 2 * pad, 200 + 2 * pad, demo.INK, t,
                  dash=16, gap=12, speed=70, width=4, under=demo.BG)
    x0, x1, y = demo.W * 0.18, demo.W * 0.82, demo.H * 0.74
    route = _route(x0, x1, y, 50)
    draw_marching(cv, route, demo.TEAL, t, dash=22, gap=18, speed=110, width=7)
    demo.dot(cv, x0, y, r=20, color=demo.MUTED)
    demo.dot(cv, x1, y, r=20, color=demo.TEAL)
    cv.mark('marquee', cx - 170 - pad, top - 100 - pad, 340 + 2 * pad, 200 + 2 * pad)


CAPABILITY = Capability(
    id='dashed-line-march',
    name='Marching ants',
    family='shapes',
    group='Lines & strokes',
    aliases=('marching ants', 'animated dashed line', 'crawling dashes', 'dash offset animation'),
    definition='A dashed outline or line stays where it is while its dashes creep steadily along it, '
               'like a column of ants on the move.',
    phrasings=('a dotted selection box with the dashes crawling around it',
               'make the dashed route line look like it is flowing toward the destination',
               'animate the dashes so they keep moving along the border'),
    related=('ant-colony-pheromone-trails', 'particle-trail', 'stroke-draw-on', 'line-draw-logo-reveal',
             'streamlines', 'path-emitter'),
    api=('videobuilder.capabilities.shapes.dashed_line_march.draw_marching',
         'videobuilder.capabilities.shapes.dashed_line_march.marching_rect',
         'videobuilder.capabilities.shapes.dashed_line_march.march_offset'),
    demo=lambda: demo.film(draw),
)
