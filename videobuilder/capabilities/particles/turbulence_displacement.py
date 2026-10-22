"""Turbulence field: every point is shoved by a smooth, seeded noise field
that drifts over time, so a crowd of particles churns chaotically while
neighbours still move together."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _lattice(ix, iy, iz, seed):
    """A repeatable pseudo-random value in [-1, 1] for one integer lattice corner."""
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1103515245) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFF) / 32767.5 - 1.0


def value_noise(x, y, z=0.0, seed=0):
    """Smooth seeded 3-D value noise in [-1, 1]: random values on the integer
    lattice, blended with a smoothstep. Use `z` as time to make a 2-D field
    drift."""
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    u, v, w = (f * f * (3 - 2 * f) for f in (fx, fy, fz))

    def lerp(a, b, t):
        return a + (b - a) * t

    def plane(k):
        a = lerp(_lattice(ix, iy, k, seed), _lattice(ix + 1, iy, k, seed), u)
        b = lerp(_lattice(ix, iy + 1, k, seed), _lattice(ix + 1, iy + 1, k, seed), u)
        return lerp(a, b, v)
    return lerp(plane(iz), plane(iz + 1), w)


def turbulence(x, y, t=0.0, seed=0, scale=260.0, octaves=3, speed=0.6):
    """The field's push at pixel (x, y) at time `t` seconds, as a vector
    (dx, dy) of roughly unit size. `scale` is the size in px of the broadest
    swirls; each of `octaves` adds detail at half the size and half the
    strength; `speed` is how fast the field changes, in lattice cells a second."""
    dx = dy = 0.0
    freq, amp, total = 1.0 / scale, 1.0, 0.0
    z = t * speed
    for o in range(octaves):
        dx += amp * value_noise(x * freq, y * freq, z, seed * 2 + o * 101)
        dy += amp * value_noise(x * freq, y * freq, z, seed * 2 + 1 + o * 101)
        total += amp
        freq, amp, z = freq * 2, amp * 0.5, z * 1.5
    return dx / total, dy / total


def displace(points, amount, t=0.0, seed=0, **kw):
    """`points` [(x, y), ...] each pushed `amount` px along the turbulence
    field at time `t`: 0 leaves them where they are, more churns them
    further. `kw` goes to `turbulence`."""
    out = []
    for x, y in points:
        dx, dy = turbulence(x, y, t, seed, **kw)
        out.append((x + dx * amount, y + dy * amount))
    return out


# The demo's subject: a dot-grid picture (a sun over two hills) that the field tears apart.
GRID_W, GRID_H, PITCH = 480, 280, 8
SUN, SKY, HILL_FAR, HILL_NEAR = demo.ACCENT, '#9ea3d6', demo.TEAL, '#3f8f86'


def _picture():
    x0, y0 = (demo.W - GRID_W) / 2, (demo.H - GRID_H) / 2
    cols, rows = GRID_W // PITCH + 1, GRID_H // PITCH + 1
    out = {}
    for j in range(rows):
        for i in range(cols):
            u, v = i / (cols - 1), j / (rows - 1)
            if (u - 0.66) ** 2 + ((v - 0.34) * GRID_H / GRID_W) ** 2 < 0.075 ** 2:
                color = SUN
            elif v > 0.78 + 0.08 * math.sin(u * 5.0 + 1.2):
                color = HILL_NEAR
            elif v > 0.58 + 0.12 * math.cos(u * 4.2 - 2.4):
                color = HILL_FAR
            else:
                color = SKY
            out.setdefault(color, []).append((x0 + i * PITCH, y0 + j * PITCH))
    return out


def draw(n, cv):
    t = n / demo.FPS
    amount = 110 * vb.ease_in_out_quart(demo.phase(n, 0.4, 2.7))
    ctx = cv.ctx
    for color, points in _picture().items():
        ctx.new_path()
        for x, y in displace(points, amount, t, seed=3, scale=150):
            ctx.new_sub_path()
            ctx.arc(x, y, 2.2, 0, 2 * math.pi)
        ctx.set_source_rgba(*vb.rgba(color))
        ctx.fill()
    cv.mark('field', (demo.W - GRID_W) / 2, (demo.H - GRID_H) / 2, GRID_W, GRID_H)


TECHNIQUE = Technique(
    id='turbulence-displacement',
    name='Turbulence field',
    family='particles',
    group='Forces',
    aliases=('turbulence displacement', 'noise displacement', 'jitter field', 'turbulent displace',
             'turbulence warp', 'procedural displace'),
    definition='Each particle is shoved about by a smoothly varying random force that shifts over time, '
               'so the swarm churns wildly yet neighbouring points still drift together.',
    phrasings=('make the dots get blown around by a swirling, chaotic wind',
               'break the picture up into particles and let noise churn them about',
               'add organic turbulence that pushes everything around smoothly'),
    related=('curl-noise-flow', 'flow-field', 'domain-warping', 'fractal-brownian-motion', 'wiggle-path',
             'swirl'),
    api=('videobuilder.techniques.particles.turbulence_displacement.displace',
         'videobuilder.techniques.particles.turbulence_displacement.turbulence',
         'videobuilder.techniques.particles.turbulence_displacement.value_noise'),
    demo=lambda: demo.film(draw),
)
