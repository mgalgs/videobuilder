"""Offset Path Expansion: copies of a shape's outline step outward from it one
after another, each a set distance further out, like contour lines spreading
from the shape's edge."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _area(points):
    n = len(points)
    return sum(points[i][0] * points[(i + 1) % n][1] - points[(i + 1) % n][0] * points[i][1] for i in range(n)) / 2


def offset_path(points, distance, step=6.0):
    """The closed point list `points` grown outward by `distance` px (inward
    when negative): each edge pushed out along its normal, outer corners
    rounded with arcs of about `step` px hops, inner corners mitred. Exact for
    convex shapes; on concave ones keep `distance` below the shortest edge
    next to an inner corner, or the mitres overlap. Winding doesn't matter."""
    n = len(points)
    if n < 3 or not distance:
        return list(points)
    side = math.copysign(1, _area(points))
    out = []
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = points[i - 1], points[i], points[(i + 1) % n]
        e0, e1 = (bx - ax, by - ay), (cx - bx, cy - by)
        l0, l1 = math.hypot(*e0) or 1.0, math.hypot(*e1) or 1.0
        n0 = (e0[1] / l0 * side, -e0[0] / l0 * side)
        n1 = (e1[1] / l1 * side, -e1[0] / l1 * side)
        turn = (e0[0] * e1[1] - e0[1] * e1[0]) * side
        if turn * distance > 0:  # the corner points away from the offset: round it
            a0, a1 = math.atan2(n0[1], n0[0]), math.atan2(n1[1], n1[0])
            sweep = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            hops = max(1, math.ceil(abs(sweep * distance) / step))
            angles = (a0 + sweep * k / hops for k in range(hops + 1))
            out += [(bx + math.cos(a) * distance, by + math.sin(a) * distance) for a in angles]
        else:  # the corner folds into the offset: meet at the mitre
            mx, my = n0[0] + n1[0], n0[1] + n1[1]
            dot = mx * n0[0] + my * n0[1] or 1.0
            out.append((bx + mx * distance / dot, by + my * distance / dot))
    return out


def draw_offset_expansion(cv, points, p, color, count=6, gap=26.0, width=3.0, stagger=0.55, fade=0.75,
                          ease=vb.ease_out_quint):
    """Draw `count` outlines of the closed shape `points` stepping outward at
    progress `p` (0 -> 1). Ring k comes out of the shape's edge and eases to
    `gap * k` px beyond it; `stagger` (0..1) is how much of the run is spent
    starting them one after another. Rings further out are fainter, down to
    `1 - fade` of full strength. The shape itself is not drawn."""
    span = 1 - stagger
    for k in range(1, count + 1):
        start = stagger * (k - 1) / max(1, count - 1)
        q = ease(vb.clamp01((p - start) / span)) if span > 0 else float(p >= start)
        if q <= 0:
            continue
        alpha = (1 - fade * (k - 1) / max(1, count - 1)) * min(1.0, q * 4)
        vb.paths.draw(cv, offset_path(points, gap * k * q), color, width=width, closed=True, alpha=alpha)


def _shape():
    """A rounded triangle a little below centre (the offset of a small triangle)."""
    cx, cy, r = demo.W / 2, demo.H / 2 + 20, 60
    tri = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in (-math.pi / 2, math.pi / 6, 5 * math.pi / 6)]
    return tri, offset_path(tri, 16)


def draw(n, cv):
    tri, body = _shape()
    p = demo.phase(n, 0.4, 2.6)
    outline = offset_path(tri, 16 + 10)  # rings start just off the shape's edge
    draw_offset_expansion(cv, outline, p, demo.TEAL, count=6, gap=26, width=3)
    vb.paths.draw(cv, body, demo.ACCENT, fill=True)
    xs, ys = [x for x, _ in body], [y for _, y in body]
    cv.mark('shape', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


CAPABILITY = Capability(
    id='offset-path-expansion',
    name='Offset path expansion',
    family='shapes',
    group='Lines & strokes',
    aliases=('offset paths', 'contour expansion', 'concentric outlines', 'echo outlines'),
    definition='Outlines of a shape grow out from its edge one after another, each settling a fixed '
               'distance further out, so the shape ends up ringed by evenly spaced contours.',
    phrasings=('copies of the outline spread outward from the shape like ripples',
               'the shape sprouts concentric outlines that step out around it',
               'rings that follow the shape\'s own silhouette expanding away from it'),
    related=('stroke-draw-on', 'isochrone-expansion', 'offset', 'outline-to-fill', 'focus-ring-draw',
             'stroke-width-pulse'),
    api=('videobuilder.capabilities.shapes.offset_path_expansion.offset_path',
         'videobuilder.capabilities.shapes.offset_path_expansion.draw_offset_expansion'),
    demo=lambda: demo.film(draw),
)
