"""Wireframe Terrain: a perspective grid of lines whose heights follow smooth
noise, rolling toward the camera so hills keep rising out of the horizon
and sliding past underneath."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _hash(i, j, seed):
    """A deterministic value in [-1, 1] for lattice point (i, j)."""
    h = (i * 374761393 + j * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 32767.5 - 1.0


def _noise(u, v, seed):
    """Smooth 2-D value noise in [-1, 1]."""
    i, j = math.floor(u), math.floor(v)
    fu, fv = u - i, v - j
    fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    a = _hash(i, j, seed) + (_hash(i + 1, j, seed) - _hash(i, j, seed)) * fu
    b = _hash(i, j + 1, seed) + (_hash(i + 1, j + 1, seed) - _hash(i, j + 1, seed)) * fu
    return a + (b - a) * fv


def terrain_height(x, z, seed=0, wavelength=4.0):
    """Ground height at world point (x, z): two octaves of value noise,
    roughly in [-1, 1]. `wavelength`: world units between hills."""
    u, v = x / wavelength, z / wavelength
    return 0.7 * _noise(u, v, seed) + 0.3 * _noise(2.1 * u, 2.1 * v, seed + 1)


def wireframe_terrain(cv, t, box=None, color=demo.TEAL, seed=0, speed=2.0, cols=44, rows=36,
                      spacing=0.6, relief=1.0, camera=1.6, horizon=0.38, width=1.6, alpha=1.0):
    """Draw a noise-displaced wireframe ground plane at time `t` (seconds)
    into `box` (a `vb.Box`, default the whole canvas), seen in perspective
    from a camera `camera` units above it. The terrain scrolls toward the
    viewer at `speed` units a second, so drawing it every frame with a rising
    `t` flies over it. `cols` x `rows` grid cells of `spacing` units;
    `relief`: height of the hills; `horizon`: where the vanishing line sits,
    as a fraction of the box height. Far lines fade into the horizon.
    Deterministic for a given `seed` and `t`."""
    box = box or vb.Box.of(cv)
    hx, hy = box.x + box.w / 2, box.y + box.h * horizon
    focal = box.w * 0.55
    travel = t * speed
    shift = travel % spacing
    near = 0.6
    xs = [(c - cols / 2) * spacing for c in range(cols + 1)]
    zs = [near + r * spacing - shift for r in range(rows + 1)]
    zs = [z for z in zs if z > 0.15]
    far = zs[-1]

    def project(x, z):
        y = relief * terrain_height(x, z + travel, seed)
        return hx + focal * x / z, hy + focal * (camera - y) / z

    grid = [[project(x, z) for x in xs] for z in zs]
    fade = [vb.clamp01(1.2 * (1 - (z - near) / (far - near))) ** 0.8 for z in zs]
    c = cv.ctx
    with cv.clip(box.x, box.y, box.w, box.h):
        c.set_line_width(width)
        c.set_line_join(1)  # round
        for r, line in enumerate(grid):  # rows: lines across, one per depth
            c.new_path()
            c.move_to(*line[0])
            for p in line[1:]:
                c.line_to(*p)
            c.set_source_rgba(*vb.canvas.rgba(color, alpha * fade[r]))
            c.stroke()
        for k in range(len(xs)):  # columns: lines running into the distance, per segment to fade
            for r in range(len(zs) - 1):
                (x0, y0), (x1, y1) = grid[r][k], grid[r + 1][k]
                c.move_to(x0, y0)
                c.line_to(x1, y1)
                c.set_source_rgba(*vb.canvas.rgba(color, alpha * (fade[r] + fade[r + 1]) / 2))
                c.stroke()


def draw(n, cv):
    t = n / demo.FPS
    wireframe_terrain(cv, t)
    cv.mark('terrain', 0, demo.H * 0.38, demo.W, demo.H * 0.62)


TECHNIQUE = Technique(
    id='wireframe-terrain',
    name='Wireframe terrain',
    family='particles',
    group='Terrain',
    aliases=('grid terrain', 'scrolling heightmap', 'synthwave grid'),
    definition='A mesh of grid lines laid over rolling hills in perspective, the landscape '
               'streaming steadily toward the camera as if flying low over it.',
    phrasings=('a retro wireframe landscape scrolling toward me',
               'fly over a bumpy line-grid ground',
               'an endless mesh of hills moving past like an 80s game'),
    related=('displacement-map', 'slopegraph-reveal', 'wireframe-reveal', 'scrollytelling-step-sequence',
             'isolines-contour-animation', 'scroll-parallax-layers'),
    api=('videobuilder.techniques.particles.wireframe_terrain.wireframe_terrain',
         'videobuilder.techniques.particles.wireframe_terrain.terrain_height'),
    demo=lambda: demo.film(draw),
)
