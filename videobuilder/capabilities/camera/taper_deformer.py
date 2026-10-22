"""Taper deformer: a shape is squeezed or flared by a scale that changes
steadily along one axis, so a box can narrow towards a point at the top
or open out wider than its base while the base itself stays put."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def taper(points, amount, axis=1, start=0.0, end=1.0, center=None):
    """`points` (2D or 3D tuples) tapered along coordinate `axis`.

    Each point's position along `axis` gives `s`, 0 at `start` and 1 at `end`
    (clamped). Its other coordinates are scaled about `center` (default the
    origin) by `1 + amount * s`: the `start` end keeps its size, the `end`
    end is scaled by `1 + amount`. `amount=-1` pinches the `end` to a point,
    positive values flare it. The scale is linear, so straight edges stay
    straight; corners are enough for a box, but curved outlines want enough
    points (`vb.paths.resample`)."""
    span = (end - start) or 1.0
    out = []
    for p in points:
        c = center or (0.0,) * len(p)
        k = 1 + amount * vb.clamp01((p[axis] - start) / span)
        out.append(tuple(v if i == axis else c[i] + (v - c[i]) * k for i, v in enumerate(p)))
    return out


# -- the demo: a gridded box seen in perspective, tapered along its height --

HALF, TALL = 1.0, 2.6         # box half-width and height, in world units (y up, base at y=0)
ROWS, COLS = 8, 4             # grid lines drawn on each face
FOCAL, DIST, PITCH = 1000, 9.0, 0.38
LIGHT = (-0.45, 0.65, 0.6)


def _box():
    xs, zs = (-HALF, HALF), (-HALF, HALF)
    return [(x, y, z) for y in (0.0, TALL) for z in zs for x in xs]  # bottom 0-3, top 4-7


# Each face as corner indices into _box(), going around the face.
FACES = ((0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5))
EDGES = ((0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4), (0, 4), (1, 5), (2, 6), (3, 7))


def _camera(p, yaw):
    x, y, z = p
    y -= TALL / 2
    x, z = x * math.cos(yaw) - z * math.sin(yaw), x * math.sin(yaw) + z * math.cos(yaw)
    y, z = y * math.cos(PITCH) - z * math.sin(PITCH), y * math.sin(PITCH) + z * math.cos(PITCH)
    return x, y, z


def _screen(p):
    x, y, z = p
    d = DIST - z
    return demo.W / 2 + FOCAL * x / d, demo.H / 2 - 30 - FOCAL * y / d


def _sub(a, b):
    return tuple(i - j for i, j in zip(a, b))


def _lerp(a, b, t):
    return tuple(i + (j - i) * t for i, j in zip(a, b))


def _face(cv, quad, mid, rows, cols):
    """Draw one camera-space face if it faces the camera: shaded fill, grid, outline."""
    u, v = _sub(quad[1], quad[0]), _sub(quad[3], quad[0])
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    size = math.sqrt(sum(i * i for i in n))
    if size < 1e-6:
        return  # pinched flat
    centre = tuple(sum(c) / 4 for c in zip(*quad))
    if sum(i * j for i, j in zip(n, _sub(centre, mid))) < 0:
        n = tuple(-i for i in n)  # point outward
    if sum(i * j for i, j in zip(n, _sub((0, 0, DIST), centre))) <= 0:
        return  # back face
    lnorm = math.sqrt(sum(i * i for i in LIGHT))
    lit = max(0.0, sum(i * j for i, j in zip(n, LIGHT)) / (size * lnorm))
    pts = [_screen(p) for p in quad]
    vb.paths.draw(cv, pts, demo.ACCENT, fill=True)
    vb.paths.draw(cv, pts, '#000000', fill=True, alpha=0.62 * (1 - lit))
    for i in range(1, rows):
        a, b = _lerp(quad[0], quad[3], i / rows), _lerp(quad[1], quad[2], i / rows)
        cv.line(*_screen(a), *_screen(b), '#000000', width=2, alpha=0.18)
    for i in range(1, cols):
        a, b = _lerp(quad[0], quad[1], i / cols), _lerp(quad[3], quad[2], i / cols)
        cv.line(*_screen(a), *_screen(b), '#000000', width=2, alpha=0.18)
    vb.paths.draw(cv, pts, '#000000', width=2, closed=True, alpha=0.35)


def _amount(n):
    """Hold, pinch the top almost to a point, then flare it wider than the base."""
    pinch = vb.ease_in_out_quart(demo.phase(n, 0.35, 1.35))
    flare = vb.ease_in_out_quart(demo.phase(n, 1.7, 2.65))
    return -0.88 * pinch + 1.38 * flare


def draw(n, cv):
    t = n / demo.FPS
    yaw = 0.62 + 0.16 * t
    amount = _amount(n)
    rest = [_camera(p, yaw) for p in _box()]
    bent = [_camera(p, yaw) for p in taper(_box(), amount, axis=1, start=0.0, end=TALL)]

    # contact shadow under the base, which never moves
    bx, by = _screen(_camera((0, 0, 0), yaw))
    cv.ctx.save()
    cv.ctx.translate(bx, by + 18)
    cv.ctx.scale(1, 0.18)
    demo.dot(cv, 0, 0, 190, color='#000000', alpha=0.35)
    cv.ctx.restore()

    for a, b in EDGES:  # the undeformed box as a faint ghost, for reference
        cv.line(*_screen(rest[a]), *_screen(rest[b]), demo.INK, width=2, alpha=0.18)

    mid = tuple(sum(c) / 8 for c in zip(*bent))
    for f in FACES:
        rows = COLS if f in (FACES[0], FACES[1]) else ROWS
        _face(cv, [bent[i] for i in f], mid, rows, COLS)

    sign = '+' if amount > 0.005 else '−' if amount < -0.005 else ' '
    demo.word(cv, f'taper {sign}{abs(amount):.2f}', demo.W / 2, demo.H - 60, size=34, color=demo.MUTED,
              font=demo.mono(34))
    xs = [_screen(p)[0] for p in bent]
    ys = [_screen(p)[1] for p in bent]
    cv.mark('box', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


CAPABILITY = Capability(
    id='taper-deformer',
    name='Taper deformer',
    family='camera',
    group='3D motion',
    aliases=('taper modifier', 'flare deformer', 'taper'),
    definition='An object is scaled more and more along one axis, so one end keeps its size while the '
               'other squeezes in towards a point or flares out wider.',
    phrasings=('squeeze the top of the box in so it turns into a pyramid',
               'make the column narrower towards the top',
               'flare the shape out so it gets wider at one end'),
    related=('pucker-and-bloat', 'koch-snowflake', 'lens-distortion', 'circle-pop',
             'variable-font-width-animation', 'angled-lower-third'),
    api=('videobuilder.capabilities.camera.taper_deformer.taper', 'videobuilder.paths.draw'),
    demo=lambda: demo.film(draw),
)
