"""Ocean waves: a water surface built from a few Gerstner waves added together.
Each wave lifts the surface on a sine and also slides the points toward its
crest, so crests come out narrow and peaked and troughs broad and flat, the
way real swell looks. Several waves at different headings and lengths roll
across one another, so the pattern never simply repeats."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...canvas import rgba
from ..schema import Technique

G = 9.81 * 60  # gravity in px/s^2 for a surface ~60 px to the metre: sets how fast each wavelength travels

# (heading in degrees, wavelength px, amplitude px, steepness 0..1): a long swell rolling toward the
# viewer (-90: along -z) and two shorter chops crossing it.
SWELL = ((-90, 420, 26, 0.85), (-62, 230, 13, 0.75), (-125, 150, 7, 0.7))


def gerstner(x, z, t, waves=SWELL, gravity=G):
    """The surface point that sits over (x, z) at rest, at time `t` seconds,
    as `(x', height, z')` with height positive up.

    Each wave is `(heading_degrees, wavelength, amplitude, steepness)`; it
    travels along its heading at the deep-water speed for its wavelength,
    lifts the point by `amplitude * sin` and pushes it horizontally by
    `steepness * amplitude * cos`, which sharpens the crests. Keep each
    wave's `steepness` <= 1 and the sum of `steepness * amplitude * k`
    (k = 2pi / wavelength) under 1, or the crests loop over themselves."""
    px, py, pz = x, 0.0, z
    for heading, length, amp, steep in waves:
        k = 2 * math.pi / length
        dx, dz = math.cos(math.radians(heading)), math.sin(math.radians(heading))
        f = k * (dx * x + dz * z) - math.sqrt(gravity * k) * t
        c, s = math.cos(f), math.sin(f)
        q = steep / (k * len(waves))  # spread the steepness so the waves together stay below a fold
        px += q * dx * c
        pz += q * dz * c
        py += amp * s
    return px, py, pz


def _mix(a, b, u):
    a, b = rgba(a), rgba(b)
    return tuple(round(255 * (a[i] + (b[i] - a[i]) * u)) for i in range(3))


def draw_ocean(cv, t, box=None, waves=SWELL, cols=120, rows=60, depth=2600, camera=300,
               deep='#16365a', light='#cfeefa', fog=demo.BG):
    """An ocean surface of `waves` at time `t`, seen from `camera` px above
    the water, filling `box` (x, y, w, h; default the whole canvas) from the
    horizon on its top edge to the near water on its bottom edge, `depth` px
    of sea away. Sampled on a `cols` x `rows` grid that widens with distance
    to fill the view, and drawn back to front as shaded facets: faces turned
    toward the low light ahead run toward `light`, the rest toward `deep`,
    and distance fades into `fog`."""
    bx, by, bw, bh = box if box is not None else (0, 0, cv.width, cv.height)
    near = 240.0
    focal = bh * near / camera  # the rest-level water at the near row lands on the box's bottom edge
    sun = (0.0, 0.8, 0.6)  # unit vector toward a light high up ahead: it catches the crests' far faces
    crest = sum(w[2] for w in waves) or 1.0
    grid = []
    for j in range(rows + 1):
        z = -0.4 * near + (depth + 0.4 * near) * (j / rows) ** 1.7  # bunched up near the viewer; starts below
        # the box's bottom edge so a trough passing there never opens a gap
        half = 0.6 * bw * (near + z) / focal  # a little wider than the view, so displaced edges stay off-screen
        grid.append([gerstner(-half + 2 * half * i / cols, z, t, waves) for i in range(cols + 1)])

    def screen(p):
        x, y, z = p
        d = near + z
        return bx + bw / 2 + focal * x / d, by + focal * (camera - y) / d

    with cv.clip(bx, by - 60, bw, bh + 60):  # headroom: crests near the horizon may poke above it
        for j in range(rows - 1, -1, -1):
            fade = (j / rows) ** 1.2
            for i in range(cols):
                a, b, c, d = grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]
                ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
                vx, vy, vz = d[0] - a[0], d[1] - a[1], d[2] - a[2]
                nx, ny, nz = uz * vy - uy * vz, ux * vz - uz * vx, uy * vx - ux * vy  # v x u: points up
                norm = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                lit = (nx * sun[0] + ny * sun[1] + nz * sun[2]) / norm
                height = (a[1] + b[1] + c[1] + d[1]) / (4 * crest)  # -1 trough .. 1 crest
                shade = vb.clamp01(0.25 + 0.25 * height + 2.2 * (lit - 0.82)) ** 1.4
                col = _mix(_mix(deep, light, shade), fog, fade * 0.8)
                pts = [screen(p) for p in (a, b, c, d)]
                vb.paths.draw(cv, pts, col, fill=True)
                vb.paths.draw(cv, pts, col, width=1, closed=True)  # hairline seal so facets show no gaps
    cv.mark('ocean', bx, by, bw, bh)


def draw(n, cv):
    t = n / demo.FPS
    horizon = demo.H * 0.24
    draw_ocean(cv, t, box=(0, horizon, demo.W, demo.H - horizon))


TECHNIQUE = Technique(
    id='ocean-waves',
    name='Ocean waves',
    family='particles',
    group='Water & light',
    aliases=('Gerstner waves', 'sum-of-sines ocean', 'trochoidal waves'),
    definition='A water surface swells and rolls as several waves cross it at once, '
               'their crests pinched to sharp ridges between wide, smooth troughs.',
    phrasings=('make it look like open sea rolling toward the camera',
               'a choppy water surface with swells moving through it',
               'animated ocean with peaked waves behind the title'),
    related=('wave-deformer', 'wave-stagger', 'sine-wave-text', 'sine-wave-distortion', 'oscillation',
             'ripple-rings'),
    api=('videobuilder.techniques.particles.ocean_waves.gerstner',
         'videobuilder.techniques.particles.ocean_waves.draw_ocean'),
    demo=lambda: demo.film(draw),
)
