"""Soft Body Jelly: a shape built from a ring of points tied together by
springs, with the air inside pushing out, so it squashes when it lands,
wobbles and settles like a jelly instead of moving as one rigid piece."""
import math
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def jelly_ring(cx, cy, r, frames, fps=30, points=24, vx=0.0, vy=0.0, gravity=1500.0, floor=None,
               stiffness=3000.0, shear=400.0, pressure=1.0, damping=0.3, friction=0.25, substeps=12):
    """Simulate a jelly ring of `points` masses on a circle of radius `r`
    centred at (cx, cy), launched at (vx, vy) px/s. Returns one outline (a
    tuple of (x, y)) per frame for `frames` frames at `fps`.

    Each point is sprung to its neighbours (`stiffness`) and to the points
    a quarter-turn away (`shear`, which keeps the ring from folding), and a
    pressure term pushes the outline back towards its starting area
    (`pressure` 0 = an empty bag, 1 = full of jelly). `floor` is the y of a
    ground the points land on, with `friction` 0..1 on the ones touching
    it. Lower `damping` wobbles longer. The result is pure: same arguments,
    same outlines, so a `draw(n, cv)` can index it by frame."""
    return _simulate(float(cx), float(cy), float(r), int(frames), float(fps), int(points), float(vx), float(vy),
                     float(gravity), None if floor is None else float(floor), float(stiffness), float(shear),
                     float(pressure), float(damping), float(friction), int(substeps))


def _area(px, py):
    n = len(px)
    return 0.5 * sum(px[i] * py[(i + 1) % n] - px[(i + 1) % n] * py[i] for i in range(n))


@lru_cache(maxsize=32)
def _simulate(cx, cy, r, frames, fps, n, vx, vy, gravity, floor, k, ks, pressure, damping, friction, substeps):
    px = [cx + r * math.cos(2 * math.pi * i / n) for i in range(n)]
    py = [cy + r * math.sin(2 * math.pi * i / n) for i in range(n)]
    ux, uy = [vx] * n, [vy] * n
    springs = []
    for i in range(n):
        for j, stiff in ((1, k), (2, k * 0.5), (n // 4, ks)):
            a, b = i, (i + j) % n
            springs.append((a, b, math.hypot(px[a] - px[b], py[a] - py[b]), stiff))
    rest_area = _area(px, py)
    dt = 1.0 / fps / substeps
    out = []
    for _ in range(frames):
        out.append(tuple(zip(px, py)))
        for _ in range(substeps):
            fx, fy = [0.0] * n, [0.0] * n
            for a, b, rest, stiff in springs:
                dx, dy = px[b] - px[a], py[b] - py[a]
                d = math.hypot(dx, dy) or 1e-6
                nx, ny = dx / d, dy / d
                rel = (ux[b] - ux[a]) * nx + (uy[b] - uy[a]) * ny
                f = stiff * (d - rest) + damping * 8 * rel
                fx[a] += f * nx; fy[a] += f * ny
                fx[b] -= f * nx; fy[b] -= f * ny
            if pressure:
                # Push each edge outward along its normal, harder the more the area has shrunk.
                p = pressure * k * 9.6 * (rest_area / max(_area(px, py), 1.0) - 1.0)
                for i in range(n):
                    j = (i + 1) % n
                    ex, ey = px[j] - px[i], py[j] - py[i]
                    gx, gy = ey * p * 0.5, -ex * p * 0.5  # outward normal times edge length, shared by both ends
                    fx[i] += gx; fy[i] += gy
                    fx[j] += gx; fy[j] += gy
            for i in range(n):
                ux[i] += fx[i] * dt
                uy[i] += (fy[i] + gravity) * dt
                ux[i] *= 1 - 0.02 * damping
                uy[i] *= 1 - 0.02 * damping
                px[i] += ux[i] * dt
                py[i] += uy[i] * dt
                if floor is not None and py[i] > floor:
                    py[i] = floor
                    uy[i] = min(uy[i], 0.0) * -0.15
                    ux[i] *= 1 - friction
    return tuple(out)


def jelly_path(cv, outline):
    """Trace `outline` (as `jelly_ring` returns) on `cv.ctx` as one smooth
    closed curve through every point (Catmull-Rom as cubic Beziers), ready
    to fill or stroke."""
    c, n = cv.ctx, len(outline)
    c.new_path()
    c.move_to(*outline[0])
    for i in range(n):
        p0, p1, p2, p3 = outline[i - 1], outline[i], outline[(i + 1) % n], outline[(i + 2) % n]
        c.curve_to(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                   p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1])
    c.close_path()


def draw_jelly(cv, outline, color=demo.ACCENT, alpha=1.0, dots=None):
    """Fill `outline` as a smooth jelly; `dots` (a color) also marks each mass point."""
    jelly_path(cv, outline)
    cv.ctx.set_source_rgba(*vb.canvas.rgba(color, alpha))
    cv.ctx.fill()
    if dots:
        for x, y in outline:
            demo.dot(cv, x, y, 4, color=dots, alpha=alpha)
    xs, ys = [p[0] for p in outline], [p[1] for p in outline]
    cv.mark('jelly', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


GROUND = demo.H - 80
R = 90


def draw(n, cv):
    rings = jelly_ring(demo.W / 2 - 150, 140, R, round(demo.SECONDS * demo.FPS), demo.FPS, vx=180.0, floor=GROUND)
    outline = rings[n]
    demo.floor(cv, GROUND)
    xs = [p[0] for p in outline]
    w = max(xs) - min(xs)
    cv.ctx.save()
    cv.ctx.translate(sum(xs) / len(xs), GROUND + 4)
    cv.ctx.scale(1, 0.12)
    demo.dot(cv, 0, 0, w * 0.55, color='#000000', alpha=0.3)
    cv.ctx.restore()
    draw_jelly(cv, outline, dots=demo.INK)


CAPABILITY = Capability(
    id='soft-body-jelly',
    name='Soft Body Jelly',
    family='principles',
    group='Physics',
    aliases=('jelly physics', 'soft body wobble', 'jelly deformation', 'mass-spring model', 'deformable blob'),
    definition='A shape whose outline is a ring of points held together by springs, so it squashes, '
               'bulges and wobbles on impact before settling back like a lump of jelly.',
    phrasings=('make it land and jiggle like a jelly',
               'a squishy blob that wobbles when it hits the floor',
               'give the shape soft, gooey physics instead of a rigid bounce'),
    related=('morphing-blob', 'noise-vertex-wobble', 'elastic-collisions', 'squash-and-stretch',
             'blob-to-icon-morph', 'pucker-and-bloat'),
    api=('videobuilder.capabilities.principles.soft_body_jelly.jelly_ring',
         'videobuilder.capabilities.principles.soft_body_jelly.draw_jelly',
         'videobuilder.capabilities.principles.soft_body_jelly.jelly_path'),
    demo=lambda: demo.film(draw),
)
