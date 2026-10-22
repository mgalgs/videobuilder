"""Crumple: the outgoing scene wrinkles into a creased, faceted wad of paper,
which then opens back out flat as the incoming scene."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _mesh(cols, rows, seed):
    """Per-vertex randomness for a crumple: (jx, jy, z) for each grid point,
    each in -1..1, fixed by `seed` so the creases hold still while they deepen."""
    rnd = random.Random(seed)
    return [[(rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for _ in range(cols + 1)]
            for _ in range(rows + 1)]


def crumple_sheet(cv, scene, amount, x=0.0, y=0.0, w=None, h=None, size=0.32, cols=16, rows=9, seed=7,
                  light=(-0.5, -0.7, 0.5)):
    """Draw `scene` (a `scene(cv)` callable drawing the whole frame) as a
    sheet of paper crumpled by `amount` (0 flat, 1 a tight wad).

    The region (x, y, w, h) (default the frame) is split into a `cols` x
    `rows` triangle mesh; as `amount` grows each vertex is pulled toward the
    region's centre (to `size` of the region at 1) and jostled, and each
    facet is shaded from a random height field lit from `light`, so it reads
    as creased paper. Nothing is drawn outside the shrinking sheet: fill a
    backdrop first."""
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    if amount <= 0:
        scene(cv)
        return
    sub = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    scene(sub)
    sub.surface.flush()
    cx, cy = x + w / 2, y + h / 2
    a = vb.clamp01(amount)
    k = 1 - (1 - size) * a                     # how much of the region the sheet still spans
    jit = 0.55 * a * min(w / cols, h / rows)   # crease jostle, under one cell so facets stay sane
    depth = 1.4 * a * min(w / cols, h / rows)  # crease height, for shading only
    noise = _mesh(cols, rows, seed)
    src, dst = {}, {}
    for j in range(rows + 1):
        for i in range(cols + 1):
            sx, sy = x + w * i / cols, y + h * j / rows
            jx, jy, z = noise[j][i]
            inner = 0 < i < cols and 0 < j < rows
            # Edges pinch in a little extra so the wad's outline turns ragged.
            pinch = 1 if inner else 1 - 0.18 * a * (0.5 + 0.5 * jx)
            src[i, j] = (sx, sy)
            dst[i, j] = (cx + (sx - cx) * k * pinch + jit * jx, cy + (sy - cy) * k * pinch + jit * jy, depth * z)
    lx, ly, lz = light
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ln, ly / ln, lz / ln
    c = cv.ctx
    pat = cairo.SurfacePattern(sub.surface)
    pat.set_filter(cairo.FILTER_GOOD)
    pat.set_extend(cairo.EXTEND_PAD)
    for j in range(rows):
        for i in range(cols):
            quad = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
            # Alternate the diagonal so the creases don't all run one way.
            tris = ((0, 1, 2), (0, 2, 3)) if (i + j) % 2 else ((0, 1, 3), (1, 2, 3))
            for t in tris:
                ks = [quad[n] for n in t]
                _facet(c, pat, sub.scale, [src[q] for q in ks], [dst[q] for q in ks], (lx, ly, lz))


def _facet(c, pat, scale, s, d, light):
    """One triangle: the source triangle `s` of the scene mapped onto `d`
    (x, y, z), then shaded by how `d` faces `light`."""
    (x0, y0), (x1, y1), (x2, y2) = s
    (u0, v0, z0), (u1, v1, z1), (u2, v2, z2) = d
    det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if abs(det) < 1e-9:
        return
    # Affine map taking s onto d: [u v] = A [x y] + t.
    a = ((u1 - u0) * (y2 - y0) - (u2 - u0) * (y1 - y0)) / det
    b = ((u2 - u0) * (x1 - x0) - (u1 - u0) * (x2 - x0)) / det
    cc = ((v1 - v0) * (y2 - y0) - (v2 - v0) * (y1 - y0)) / det
    dd = ((v2 - v0) * (x1 - x0) - (v1 - v0) * (x2 - x0)) / det
    m = cairo.Matrix(a, cc, b, dd, u0 - a * x0 - b * y0, v0 - cc * x0 - dd * y0)
    # Grow the clip a hair past the facet so neighbours overlap and no seams show.
    mx, my = (u0 + u1 + u2) / 3, (v0 + v1 + v2) / 3
    pts = []
    for u, v in ((u0, v0), (u1, v1), (u2, v2)):
        du, dv = u - mx, v - my
        n = math.hypot(du, dv) or 1
        pts.append((u + du / n * 0.75, v + dv / n * 0.75))
    c.save()
    c.move_to(*pts[0])
    c.line_to(*pts[1])
    c.line_to(*pts[2])
    c.close_path()
    c.clip()
    c.save()
    c.transform(m)
    c.scale(1 / scale, 1 / scale)
    c.set_source(pat)
    c.paint()
    c.restore()
    # Facet normal from the crease heights; brighter facing the light, darker away.
    ex, ey, ez = u1 - u0, v1 - v0, z1 - z0
    fx, fy, fz = u2 - u0, v2 - v0, z2 - z0
    nx, ny, nz = ey * fz - ez * fy, ez * fx - ex * fz, ex * fy - ey * fx
    nn = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
    if nz < 0:
        nx, ny, nz = -nx, -ny, -nz
    lit = (nx * light[0] + ny * light[1] + nz * light[2]) / nn - light[2]
    if lit > 0:
        c.set_source_rgba(1, 1, 1, min(0.5, lit * 0.9))
    else:
        c.set_source_rgba(0, 0, 0, min(0.6, -lit * 1.1))
    c.paint()
    c.restore()


def crumple(cv, a, b, p, backdrop=demo.BG, size=0.32, seed=7):
    """Draw the crumple at progress `p` (0 -> 1): `a(cv)` crumples into a
    small creased wad over the first half, the wad turns over to `b` at the
    middle, and `b(cv)` uncrumples back to a flat full frame over the second.
    `backdrop` fills the frame behind the sheet.

    In a film, call it while two shots are live in an overlap, e.g.
    `crumple(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    amount = vb.ease_in_out_quart(1 - abs(2 * p - 1))
    cv.fill(backdrop)
    # A slow quarter-turn as it wads up, so it feels handled, not just scaled.
    turn = 0.12 * math.sin(math.pi * p)
    c = cv.ctx
    c.save()
    c.translate(cv.width / 2, cv.height / 2)
    c.rotate(turn)
    c.translate(-cv.width / 2, -cv.height / 2)
    crumple_sheet(cv, a if p < 0.5 else b, amount, size=size, seed=seed)
    c.restore()


CAPABILITY = Capability(
    id='crumple',
    name='Crumple',
    family='transitions',
    group='Page and Fold',
    aliases=('paper crumple', 'crinkle transition', 'crumple reveal'),
    definition='The picture creases and scrunches up like a sheet of paper balled in a fist, '
               'then the wad opens back out flat as the next scene.',
    phrasings=('scrunch the shot up like paper and unfold the next one',
               'crumple the first scene into a ball, then smooth it out into the second',
               'a crinkled-paper transition between the two clips'),
    related=('cut-out-paper-animation', 'pixelate-transition', 'crt-scanlines', 'elastic-stretch', 'confetti',
             'paper-fold-reveal'),
    api=('videobuilder.capabilities.transitions.crumple.crumple',
         'videobuilder.capabilities.transitions.crumple.crumple_sheet'),
    demo=lambda: demo.two_scenes(crumple, start=0.6, length=1.8),
)
