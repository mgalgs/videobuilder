"""Radar Chart Fill: a web of spokes and rings, then a filled polygon that
swells out from the centre until each corner sits on its value along its
spoke, drawing a profile across several measures at once."""
import math

import videobuilder as vb
from videobuilder.looks import kit as looks

from .. import _demo as demo
from ..schema import Technique


def radar_points(cx, cy, radius, values, p=1.0, start=-math.pi / 2, stagger=0.0, ease=vb.ease_out_back):
    """The polygon's corners at progress `p` (0 -> 1): one per entry of
    `values` (each 0 -> 1 of `radius`), on spokes spaced evenly clockwise
    from angle `start` (default the top). Every corner rides out from
    (cx, cy) along its spoke under `ease`; `stagger` (0 -> 1) delays each
    spoke after the one before by that share of the move."""
    count = len(values)
    pts = []
    for i, v in enumerate(values):
        lag = stagger * i / max(1, count - 1)
        k = ease(vb.clamp01((p - lag) / (1 - stagger))) if stagger < 1 else float(p >= 1)
        a = start + 2 * math.pi * i / count
        r = radius * v * k
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def radar_grid(cv, cx, cy, radius, spokes, rings=4, color=demo.LINE, width=2, p=1.0, start=-math.pi / 2,
               alpha=1.0):
    """The chart's web: `spokes` lines out from (cx, cy) and `rings`
    concentric polygons joining them. `p` (0 -> 1) draws it in: the spokes
    grow out, then the rings appear from the inside outwards."""
    grow = vb.clamp01(p * 2)
    for i in range(spokes):
        a = start + 2 * math.pi * i / spokes
        cv.line(cx, cy, cx + radius * grow * math.cos(a), cy + radius * grow * math.sin(a), color,
                width=width, alpha=alpha)
    for j in range(1, rings + 1):
        show = vb.clamp01((p - 0.5) * 2 * rings - (j - 1))
        if show <= 0:
            continue
        r = radius * j / rings
        ring = [(cx + r * math.cos(start + 2 * math.pi * i / spokes),
                 cy + r * math.sin(start + 2 * math.pi * i / spokes)) for i in range(spokes)]
        looks.outline(cv, ring + ring[:1], color, width, alpha=alpha * show)


def radar_chart(cv, cx, cy, radius, values, p, color, fill_alpha=0.3, width=3, dots=5, start=-math.pi / 2,
                stagger=0.25, ease=vb.ease_out_back, alpha=1.0):
    """The filled radar polygon for `values` (each 0 -> 1) at progress `p`
    (0 -> 1), growing from (cx, cy) out to its values: a translucent fill,
    an outline of width `width` and a dot of radius `dots` on each corner
    (0 for none), all in `color`. `stagger` and `ease` go to
    `radar_points`. Draw `radar_grid` underneath for the web. Returns the
    corners."""
    pts = radar_points(cx, cy, radius, values, p, start=start, stagger=stagger, ease=ease)
    if p <= 0 or len(pts) < 3:
        return pts
    looks.fill(cv, pts, color, alpha=fill_alpha * alpha)
    looks.outline(cv, pts + pts[:1], color, width, alpha=alpha)
    for x, y in pts:
        if dots:
            demo.dot(cv, x, y, r=dots, color=color, alpha=alpha)
    cv.mark('radar', cx - radius, cy - radius, 2 * radius, 2 * radius)
    return pts


# ---- the demo: one profile across six measures ----
AXES = ('SPEED', 'POWER', 'RANGE', 'CONTROL', 'STAMINA', 'AGILITY')
VALUES = (0.88, 0.62, 0.95, 0.45, 0.72, 0.55)


def draw(n, cv):
    cx, cy, radius = demo.W / 2, demo.H / 2 + 8, 190
    web = demo.phase(n, 0.0, 0.7)
    radar_grid(cv, cx, cy, radius, len(AXES), rings=4, color=demo.MUTED, p=web, alpha=0.45)
    f = demo.font(17, 800)
    for i, label in enumerate(AXES):
        a = -math.pi / 2 + 2 * math.pi * i / len(AXES)
        r = radius + 34
        demo.word(cv, label, cx + r * math.cos(a), cy + r * math.sin(a), font=f, color=demo.INK,
                  alpha=demo.phase(n, 0.3 + 0.06 * i, 0.6 + 0.06 * i))
    radar_chart(cv, cx, cy, radius, VALUES, demo.phase(n, 0.8, 2.3), demo.ACCENT)


TECHNIQUE = Technique(
    id='radar-chart-fill',
    name='Radar chart fill',
    family='broadcast',
    group='Charts',
    aliases=('spider chart', 'polar profile', 'web chart', 'star plot'),
    definition='A shaded polygon swells out from the middle of a web of spokes until each corner '
               'stops at its score on its own axis, sketching a profile of several measures at once.',
    phrasings=('a spider chart whose shape grows out to show the stats',
               'animate a radar graph filling in from the centre',
               'a player stats web where the coloured shape expands to each value'),
    related=('hub-and-spoke-spread', 'choropleth-fill', 'polar-coordinate-warp', 'hypocycloid-spirograph',
             'sound-reactive-radial-shape', 'dot-density-map'),
    api=('videobuilder.techniques.broadcast.radar_chart_fill.radar_chart',
         'videobuilder.techniques.broadcast.radar_chart_fill.radar_grid',
         'videobuilder.techniques.broadcast.radar_chart_fill.radar_points'),
    demo=lambda: demo.film(draw),
)
