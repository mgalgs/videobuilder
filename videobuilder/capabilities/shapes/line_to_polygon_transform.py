"""Line-to-polygon transform: a straight line of equal segments folds at its
joints, from both ends inwards, until its two ends meet as a closed polygon.

`vb.paths.morph` already blends any two point lists, but a straight blend
shrinks the segments on the way; this keeps every side its full length, so
the line reads as one stiff chain folding shut."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def line_to_polygon(cx, cy, side, sides, p, stagger=0.0, rotation=0.0):
    """The `sides + 1` points of a chain of `sides` segments, each `side` px
    long, at fold progress `p` (0 -> 1): a straight horizontal line at 0, a
    regular polygon centred on (cx, cy) at 1, its last point back on its
    first. Each of the `sides - 1` joints turns by up to 360/sides degrees;
    `stagger` (0..1) makes the joints bend one after another, from both ends
    of the line in towards its middle, instead of all together. The chain stays centred on (cx, cy)
    and symmetric about its middle throughout; `rotation` (radians) turns the
    whole figure."""
    p = vb.clamp01(p)
    joints = sides - 1
    full = 2 * math.pi / sides
    ranks = [min(i, joints - 1 - i) for i in range(joints)]  # outer joints first, the middle last
    span = 1 + stagger * max(ranks)
    turns = [full * vb.clamp01(p * span - stagger * r) for r in ranks]
    heading = sum(turns) / 2 + rotation  # the middle of the chain stays level
    pts = [(0.0, 0.0)]
    for k in range(sides):
        x, y = pts[-1]
        pts.append((x + side * math.cos(heading), y + side * math.sin(heading)))
        if k < joints:
            heading -= turns[k]  # turning this way cups the chain, its ends rising to meet at the top
    # centre with the ends half-weighted: the line's midpoint at 0, the polygon's centre at 1
    weights = [0.5] + [1.0] * (len(pts) - 2) + [0.5]
    mx = sum(w * x for w, (x, _) in zip(weights, pts)) / sides
    my = sum(w * y for w, (_, y) in zip(weights, pts)) / sides
    return [(cx + x - mx, cy + y - my) for x, y in pts]


def draw_line_to_polygon(cv, cx, cy, side, sides, p, color, fill=None, width=4, stagger=0.0,
                         rotation=0.0, vertices=None, fill_from=0.85):
    """Draw the fold at progress `p` (see `line_to_polygon`): the stroke in
    `color`, a small dot on each joint in `vertices` (default: none), and
    `fill` fading in over the last stretch from `fill_from` as the ends close.
    Returns the points."""
    pts = line_to_polygon(cx, cy, side, sides, p, stagger, rotation)
    if fill is not None and p > fill_from:
        vb.paths.draw(cv, pts[:-1], fill, fill=True, alpha=vb.clamp01((p - fill_from) / (1 - fill_from)))
    vb.paths.draw(cv, pts, color, width=width, closed=p >= 1)
    if vertices is not None:
        for x, y in pts[1:-1]:
            demo.dot(cv, x, y, r=width * 1.6, color=vertices)
    return pts


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.5, 2.3))
    pts = draw_line_to_polygon(cv, demo.W / 2, demo.H / 2 + 20, 120, 6, p, demo.INK, fill=demo.LINE, width=4,
                               stagger=0.5, vertices=demo.MUTED)
    ends = demo.ACCENT if p < 1 else demo.TEAL
    for x, y in (pts[0], pts[-1]):
        demo.dot(cv, x, y, r=9, color=ends)
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    cv.mark('shape', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


CAPABILITY = Capability(
    id='line-to-polygon-transform',
    name='Line-to-polygon transform',
    family='shapes',
    group='Lines & strokes',
    aliases=('line morph to polygon', 'line straighten to shape', 'line fold to shape'),
    definition='A straight line bends at its joints, corner by corner from the ends inwards, until its two ends meet '
               'and it closes into a polygon.',
    phrasings=('a line that folds up into a hexagon',
               'the stroke bends round and joins into a closed shape',
               'turn a flat line into a polygon by bending it at the points'),
    related=('bend-deformer', 'arc-bend-morph', 'text-to-shape-morph', 'line-weave', 'rotating-polygon-loop',
             'shape-morph'),
    api=('videobuilder.capabilities.shapes.line_to_polygon_transform.line_to_polygon',
         'videobuilder.capabilities.shapes.line_to_polygon_transform.draw_line_to_polygon',
         'videobuilder.paths.draw'),
    demo=lambda: demo.film(draw),
)
