"""Parallax occlusion mapping: a flat square, seen in perspective, looks
carved because every pixel marches its view ray down through a height map
until it hits the surface. Raised parts hide what is behind them at low
angles, which a plain bump map can't do.

    grid = relief_texture(stud_height)                 # once, at import
    def draw(n, cv):
        relief_plane(cv, grid, (0, 0, cv.width, cv.height), tilt=40, turn=10, depth=0.9)

Pure Python, so the plane is raymarched at most `resolution` px wide and
scaled up to its box.
"""
import math

from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

PLANE = 10.0  # side of the square, world units, centred on the origin


def _rgb(color):
    c = color.lstrip('#')
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


def stud_height(x, y):
    """One cell of a studded tile, `x`, `y` in [0, 1): a sunken groove, a
    bevelled square plinth and a round stud with a rounded top. Returns the
    height, 0 (deepest) to 1 (top)."""
    dx, dy = abs(x - 0.5), abs(y - 0.5)
    plinth = vb.clamp01((0.42 - max(dx, dy)) / 0.05) * 0.45
    r = math.hypot(dx, dy)
    stud = vb.clamp01((0.24 - r) / 0.05)
    stud = 0.45 + 0.55 * stud * (1 - 0.35 * (r / 0.24) ** 2) if stud > 0 else 0.0
    return max(plinth, stud)


def relief_texture(height, size=128, colors=(demo.LINE, demo.TEAL, demo.ACCENT), strength=6.0):
    """A height-map texture for `relief_plane`: `height(x, y)` sampled on a
    `size` x `size` grid over one tile (it must repeat seamlessly), with a
    slope normal and a colour per texel. `colors` tint low, middle and high
    ground; `strength` steepens the normals."""
    hs = [[height(i / size, j / size) for i in range(size)] for j in range(size)]
    low, mid, high = (_rgb(c) for c in colors)
    texels = []
    for j in range(size):
        row = []
        for i in range(size):
            h = hs[j][i]
            gx = (hs[j][(i + 1) % size] - hs[j][i - 1]) * strength
            gy = (hs[(j + 1) % size][i] - hs[j - 1][i]) * strength
            k = 1 / math.sqrt(gx * gx + gy * gy + 1)
            base = low if h < 0.2 else mid if h < 0.6 else high
            cavity = 0.55 + 0.45 * h  # deep ground catches less light
            row.append((h, -gx * k, -gy * k, k, tuple(c * cavity for c in base)))
        texels.append(row)
    return size, hs, texels


def march(grid, u, v, du, dv, steps):
    """The parallax-occlusion lookup: from texture coordinate (u, v) on the top
    of the relief, step down through `steps` layers while the view ray drifts
    by (du, dv) over the full depth, stop at the first layer below the height
    map and narrow the hit down between it and the layer before. Returns
    (u, v) of the surface the ray actually hits."""
    size, hs, _ = grid
    step = 1.0 / steps
    for k in range(1, steps + 1):
        cu, cv_ = u + du * k * step, v + dv * k * step
        gap = hs[int(cv_ * size) % size][int(cu * size) % size] - (1.0 - k * step)
        if gap >= 0:
            lo, hi = (k - 1) * step, k * step                   # halve the bracketing interval
            for _ in range(4):
                mid = (lo + hi) / 2
                mu, mv = u + du * mid, v + dv * mid
                if hs[int(mv * size) % size][int(mu * size) % size] - (1.0 - mid) >= 0:
                    hi = mid
                else:
                    lo = mid
            return u + du * hi, v + dv * hi
    return u + du, v + dv


def relief_plane(cv, grid, box, tilt=40.0, turn=0.0, depth=0.9, tiles=5, distance=12.0, aim=0.0, fov=50.0,
                 light=(-0.5, 0.6, 0.65), background=demo.BG, resolution=960):
    """Draw a flat square floor in perspective into `box` (x, y, w, h), with
    `grid` (from `relief_texture`) repeated `tiles` times across it and
    parallax-occlusion mapped `depth` deep (in tile widths; 0 draws it flat).
    The camera looks down at the floor's centre (or `aim` units beyond it)
    from `tilt` degrees above, swung `turn` degrees around it, `distance`
    away, with `fov` degrees of vertical view. Raymarched at most `resolution` px wide, then scaled up."""
    x, y, w, h = box
    rw = max(16, min(resolution, round(w * cv.scale_factor())))
    rh = max(9, round(rw * h / w))
    el, az = math.radians(tilt), math.radians(turn)
    fx, fy, fz = -math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), -math.sin(el)
    cx, cy, cz = (-aim * math.sin(az) - distance * fx, aim * math.cos(az) - distance * fy, -distance * fz)
    n = math.hypot(fx, fy)
    rx, ry = fy / n, -fx / n                                    # right: forward x up, level
    ux, uy, uz = ry * fz, -rx * fz, rx * fy - ry * fx           # up: right x forward
    t = math.tan(math.radians(fov) / 2)
    ln = math.sqrt(sum(c * c for c in light))
    lx, ly, lz = (c / ln for c in light)
    size, _, texels = grid
    per = tiles / PLANE                                         # tile units per world unit
    sink = depth / per                                          # relief depth, world units
    half = PLANE / 2
    bg = bytes(round(c * 255) for c in _rgb(background))
    px = bytearray(bg * (rw * rh))
    for j in range(rh):
        sy = (1 - 2 * (j + 0.5) / rh) * t
        for i in range(rw):
            sx = (2 * (i + 0.5) / rw - 1) * t * rw / rh
            dx, dy, dz = fx + sx * rx + sy * ux, fy + sx * ry + sy * uy, fz + sy * uz
            if dz >= -1e-6:
                continue
            s = -cz / dz
            hx, hy = cx + s * dx, cy + s * dy
            if abs(hx) > half or abs(hy) > half:
                continue
            u, v = (hx + half) * per, (hy + half) * per
            if depth > 0:
                d = math.sqrt(dx * dx + dy * dy + dz * dz)
                steps = 10 + int(40 * (1 + dz / d))              # more layers at grazing angles
                du, dv = dx / -dz * sink * per, dy / -dz * sink * per
                u, v = march(grid, u, v, du, dv, steps)
                if not (0 <= u <= tiles and 0 <= v <= tiles):   # ran out through the side
                    continue
            _, nx, ny, nz, (r, g, b) = texels[int(v * size) % size][int(u * size) % size]
            lit = 0.28 + 0.85 * max(0.0, nx * lx + ny * ly + nz * lz)
            o = (j * rw + i) * 3
            px[o], px[o + 1], px[o + 2] = (min(255, int(c * lit * 255)) for c in (r, g, b))
    img = vb.Image.from_pil(PILImage.frombytes('RGB', (rw, rh), bytes(px)))
    cv.image(img, x, y, w, h)


GRID = relief_texture(stud_height)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.0, demo.SECONDS))
    grow = vb.ease_out_expo(demo.phase(n, 0.35, 1.3))  # flat texture first, then the relief appears
    relief_plane(cv, GRID, (0, 0, demo.W, demo.H), tilt=64 - 40 * p, turn=-30 + 55 * p,
                 depth=0.9 * grow, distance=12 - 2.5 * p, aim=1.5 * p)


CAPABILITY = Capability(
    id='parallax-occlusion-mapping',
    name='Parallax occlusion mapping',
    family='camera',
    group='Shader looks',
    aliases=('POM', 'relief mapping', 'steep parallax mapping'),
    definition='A flat textured surface looks deeply carved because each pixel traces the view ray '
               'down into a height map, so raised bits shift and hide what lies behind them as the camera moves.',
    phrasings=('make this flat floor look like it has real bumps without adding geometry',
               'fake deep 3D relief on a flat plane that holds up as the camera tilts',
               'studs that pop out of the texture and block each other at low angles'),
    related=('two-point-five-d-photo-parallax', 'displacement-map', 'pointer-parallax-layers',
             'polar-coordinate-warp', 'parallax-slide', 'parallax-letter-layers'),
    api=('videobuilder.capabilities.camera.parallax_occlusion_mapping.relief_plane',
         'videobuilder.capabilities.camera.parallax_occlusion_mapping.relief_texture',
         'videobuilder.capabilities.camera.parallax_occlusion_mapping.march',
         'videobuilder.capabilities.camera.parallax_occlusion_mapping.stud_height'),
    demo=lambda: demo.film(draw),
)
