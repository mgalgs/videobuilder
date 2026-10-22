"""Delaunay Triangle Mesh: a field of drifting points joined into triangles
that re-form as the points move, each facet shaded flat so the whole reads
as a slowly shifting low-poly surface."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def delaunay(points):
    """Delaunay triangulation of `points` [(x, y), ...] (Bowyer-Watson): a
    list of `(i, j, k)` index triples, each wound clockwise on screen. Fine
    for the few hundred points a frame needs; re-run it every frame and the
    edges flip on their own as the points drift."""
    pts = [(float(x), float(y)) for x, y in points]
    n = len(pts)
    if n < 3:
        return []
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0) * 20
    pts += [(cx - span, cy - span), (cx + span, cy - span), (cx, cy + span)]  # a super-triangle round them all

    def circle(t):
        (ax, ay), (bx, by), (qx, qy) = pts[t[0]], pts[t[1]], pts[t[2]]
        d = 2 * (ax * (by - qy) + bx * (qy - ay) + qx * (ay - by))
        if abs(d) < 1e-12:
            return cx, cy, math.inf
        a2, b2, q2 = ax * ax + ay * ay, bx * bx + by * by, qx * qx + qy * qy
        ux = (a2 * (by - qy) + b2 * (qy - ay) + q2 * (ay - by)) / d
        uy = (a2 * (qx - bx) + b2 * (ax - qx) + q2 * (bx - ax)) / d
        return ux, uy, (ax - ux) ** 2 + (ay - uy) ** 2

    tris = {(n, n + 1, n + 2): circle((n, n + 1, n + 2))}
    for i in range(n):
        px, py = pts[i]
        bad = [t for t, (ux, uy, r2) in tris.items() if (px - ux) ** 2 + (py - uy) ** 2 < r2]
        edges = {}
        for t in bad:
            del tris[t]
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = tuple(sorted(e))
                edges[k] = None if k in edges else e  # an edge two bad triangles share is inside the hole
        for e in edges.values():
            if e is not None:
                t = (e[0], e[1], i)
                tris[t] = circle(t)
    out = []
    for a, b, c in tris:
        if max(a, b, c) >= n:
            continue
        (ax, ay), (bx, by), (qx, qy) = pts[a], pts[b], pts[c]
        out.append((a, b, c) if (bx - ax) * (qy - ay) - (by - ay) * (qx - ax) > 0 else (a, c, b))
    return out


def drifting_points(x, y, w, h, cols, rows, t, amount=0.35, seed=0):
    """A jittered `cols` x `rows` grid of points filling the box (x, y, w, h)
    at time `t` seconds. Inner points wander on slow loops up to `amount` of
    a cell from home; edge points slide only along their edge and the four
    corners stay put, so the mesh always fills the box."""
    rnd = random.Random(seed)
    cw, ch = w / (cols - 1), h / (rows - 1)
    out = []
    for r in range(rows):
        for c in range(cols):
            fx, fy = rnd.uniform(0.3, 0.7), rnd.uniform(0.3, 0.7)
            ph, jx, jy = rnd.uniform(0, 2 * math.pi), rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2)
            dx = (jx + amount * math.sin(t * fx * 2 + ph)) * cw
            dy = (jy + amount * math.cos(t * fy * 2 + ph * 1.7)) * ch
            if c in (0, cols - 1):
                dx = 0
            if r in (0, rows - 1):
                dy = 0
            out.append((x + c * cw + dx, y + r * ch + dy))
    return out


def _mix(a, b, k):
    a, b = vb.canvas.rgba(a), vb.canvas.rgba(b)
    return tuple(round(255 * (u + (v - u) * k)) for u, v in zip(a[:3], b[:3]))


def draw_mesh(cv, points, dark, bright, heights=None, light=(-0.45, -0.6, 0.66), edge=None, edge_width=1.5,
              dot=None, dot_r=3.0, triangles=None):
    """Triangulate `points` (unless `triangles` are given) and fill each facet
    flat, between `dark` and `bright` by how squarely it faces `light` (an
    (x, y, z) direction; z points out of the screen). `heights` gives each
    point a z so the facets tilt like a low-poly surface; without them every
    facet is equally lit. `edge` strokes the triangle sides, `dot` marks the
    points. Returns the triangles drawn."""
    tris = delaunay(points) if triangles is None else triangles
    zs = heights or [0.0] * len(points)
    lx, ly, lz = light
    ll = math.sqrt(lx * lx + ly * ly + lz * lz) or 1.0
    c = cv.ctx
    for a, b, q in tris:
        (ax, ay), (bx, by), (qx, qy) = points[a], points[b], points[q]
        ux, uy, uz = bx - ax, by - ay, zs[b] - zs[a]
        vx, vy, vz = qx - ax, qy - ay, zs[q] - zs[a]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        k = vb.clamp01((nx * lx + ny * ly + nz * lz) / (nl * ll))
        c.new_path()
        c.move_to(ax, ay)
        c.line_to(bx, by)
        c.line_to(qx, qy)
        c.close_path()
        c.set_source_rgba(*vb.canvas.rgba(_mix(dark, bright, k)))
        c.fill_preserve()
        c.set_line_width(0.75)  # a hairline in the facet's own colour closes the anti-aliasing seams
        c.stroke()
    if edge:
        seen = set()
        for t in tris:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = tuple(sorted(e))
                if k not in seen:
                    seen.add(k)
                    cv.line(*points[e[0]], *points[e[1]], edge, width=edge_width, alpha=0.35)
    if dot:
        for px, py in points:
            demo.dot(cv, px, py, dot_r, color=dot)
    return tris


def draw(n, cv):
    t = n / demo.FPS
    x, y, w, h = 90, 60, demo.W - 180, demo.H - 120
    pts = drifting_points(x, y, w, h, 11, 7, t * 1.6 + 2, amount=0.3, seed=5)
    # a gentle swell travelling across the field tilts the facets towards and away from the light
    zs = [90 * math.sin((px - x) / w * 5 + t * 1.8) * math.cos((py - y) / h * 3.5 - t * 1.1) for px, py in pts]
    draw_mesh(cv, pts, '#262b52', '#7d86f0', heights=zs, edge='#c9ceff', dot=demo.INK)
    cv.mark('mesh', x, y, w, h)


CAPABILITY = Capability(
    id='delaunay-triangle-mesh',
    name='Delaunay triangle mesh',
    family='shapes',
    group='Polygon & tessellation',
    aliases=('triangle mesh drift', 'low-poly mesh motion', 'triangulated field', 'Delaunay triangulation'),
    definition='Scattered points drift slowly while lines join them into a web of flat-shaded triangles '
               'that keep re-forming, so the area looks like a gently shifting faceted surface.',
    phrasings=('a low-poly triangle background where the points keep moving',
               'connect moving dots into triangles that reshape as they drift',
               'a faceted geometric mesh that slowly shifts and catches the light'),
    related=('gradient-mesh-drift', 'noise-vertex-wobble', 'sierpinski-gasket', 'low-poly-faceting',
             'tessellation-triangle-flip', 'geometric-loop'),
    api=('videobuilder.capabilities.shapes.delaunay_triangle_mesh.draw_mesh',
         'videobuilder.capabilities.shapes.delaunay_triangle_mesh.delaunay',
         'videobuilder.capabilities.shapes.delaunay_triangle_mesh.drifting_points'),
    demo=lambda: demo.film(draw),
)
