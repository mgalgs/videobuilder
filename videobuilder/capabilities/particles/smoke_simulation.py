"""Smoke Simulation: a small grid fluid solver (semi-Lagrangian advection, a
pressure projection, buoyancy and vorticity confinement) carries a density
field that rises from a source and rolls into curling eddies. Pure Python and
Pillow, so it runs anywhere videobuilder does; the grid is coarse and the
field is smoothed up to the frame."""
import math
import random
from functools import lru_cache

from PIL import Image as PILImage
from PIL import ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


class Smoke:
    """A 2-D smoke field on a `cols` x `rows` grid (row 0 at the top).

    Each `step(dt)` adds buoyancy (dense smoke rises), swirls the flow with
    vorticity confinement (`swirl`), makes it divergence-free, then carries
    velocity and density along it; `fade` is the share of density kept per
    second. `emit` puffs smoke into it; `density` is the field, row-major,
    clamped 0..1 when drawn. Seeded jitter breaks the symmetry, so the same
    `seed` gives the same plume."""

    def __init__(self, cols=64, rows=36, buoyancy=40.0, swirl=16.0, fade=0.75, wind=0.0, seed=0,
                 iterations=12):
        self.cols, self.rows = cols, rows
        self.buoyancy, self.swirl, self.fade, self.wind = buoyancy, swirl, fade, wind
        self.iterations = iterations
        self.rnd = random.Random(seed)
        n = cols * rows
        self.u, self.v, self.density = [0.0] * n, [0.0] * n, [0.0] * n

    def emit(self, x, y, radius, amount=1.0, vx=0.0, vy=-8.0):
        """Puff smoke in at (x, y), in grid cells, over a soft disc of
        `radius` cells, pushing it with velocity (vx, vy) cells/second."""
        cols, rows = self.cols, self.rows
        for j in range(max(0, int(y - radius)), min(rows, int(y + radius) + 2)):
            for i in range(max(0, int(x - radius)), min(cols, int(x + radius) + 2)):
                d = math.hypot(i + 0.5 - x, j + 0.5 - y) / radius
                if d < 1:
                    k, w = j * cols + i, (1 - d * d)
                    self.density[k] = min(1.5, self.density[k] + amount * w)
                    self.u[k] += (vx - self.u[k]) * w
                    self.v[k] += (vy - self.v[k]) * w

    def _sample(self, f, x, y):
        cols, rows = self.cols, self.rows
        x = min(max(x - 0.5, 0.0), cols - 1.001)
        y = min(max(y - 0.5, 0.0), rows - 1.001)
        i, j = int(x), int(y)
        fx, fy = x - i, y - j
        k = j * cols + i
        top = f[k] + (f[k + 1] - f[k]) * fx
        bot = f[k + cols] + (f[k + cols + 1] - f[k + cols]) * fx
        return top + (bot - top) * fy

    def step(self, dt):
        cols, rows = self.cols, self.rows
        u, v, rho = self.u, self.v, self.density
        jitter = self.rnd.uniform
        # Forces: buoyancy lifts dense smoke (y grows downward), a little wind and noise.
        for k in range(cols * rows):
            if rho[k] > 0.002:
                v[k] -= self.buoyancy * rho[k] * dt
                u[k] += (self.wind + jitter(-3, 3)) * rho[k] * dt
        self._confine(dt)
        self._project()
        # Carry velocity and density back along the flow (semi-Lagrangian).
        nu, nv, nr = [0.0] * len(u), [0.0] * len(u), [0.0] * len(u)
        keep = self.fade ** dt
        for j in range(rows):
            for i in range(cols):
                k = j * cols + i
                x, y = i + 0.5 - u[k] * dt, j + 0.5 - v[k] * dt
                nu[k] = self._sample(u, x, y)
                nv[k] = self._sample(v, x, y)
                nr[k] = self._sample(rho, x, y) * keep
        for k in range(2 * cols):  # smoke leaving through the top thins out instead of pooling there
            nr[k] *= 0.5 if k < cols else 0.8
        self.u, self.v, self.density = nu, nv, nr

    def _confine(self, dt):
        """Vorticity confinement: push the flow round its own eddies so the
        coarse grid keeps its curls instead of smearing them out."""
        cols, rows, u, v = self.cols, self.rows, self.u, self.v
        w = [0.0] * (cols * rows)
        for j in range(1, rows - 1):
            for i in range(1, cols - 1):
                k = j * cols + i
                w[k] = (v[k + 1] - v[k - 1] - u[k + cols] + u[k - cols]) * 0.5
        for j in range(2, rows - 2):
            for i in range(2, cols - 2):
                k = j * cols + i
                gx = (abs(w[k + 1]) - abs(w[k - 1])) * 0.5
                gy = (abs(w[k + cols]) - abs(w[k - cols])) * 0.5
                m = math.hypot(gx, gy) + 1e-5
                u[k] += self.swirl * (gy / m) * w[k] * dt
                v[k] -= self.swirl * (gx / m) * w[k] * dt

    def _project(self):
        """Make the flow divergence-free (Jacobi pressure solve), walls closed
        at the sides and bottom, free at the top."""
        cols, rows, u, v = self.cols, self.rows, self.u, self.v
        n = cols * rows
        div = [0.0] * n
        for j in range(1, rows - 1):
            for i in range(1, cols - 1):
                k = j * cols + i
                div[k] = (u[k + 1] - u[k - 1] + v[k + cols] - v[k - cols]) * 0.5
        p = [0.0] * n
        for _ in range(self.iterations):
            q = [0.0] * n
            for j in range(1, rows - 1):
                for i in range(1, cols - 1):
                    k = j * cols + i
                    q[k] = (p[k - 1] + p[k + 1] + p[k - cols] + p[k + cols] - div[k]) * 0.25
            for i in range(cols):  # closed bottom; the top row stays 0, so smoke leaves upward
                q[(rows - 1) * cols + i] = q[(rows - 2) * cols + i]
            for j in range(rows):
                q[j * cols] = q[j * cols + 1]
                q[j * cols + cols - 1] = q[j * cols + cols - 2]
            p = q
        for j in range(1, rows - 1):
            for i in range(1, cols - 1):
                k = j * cols + i
                u[k] -= (p[k + 1] - p[k - 1]) * 0.5
                v[k] -= (p[k + cols] - p[k - cols]) * 0.5

    def mask(self, blur=0.5):
        """The density as a Pillow L image, one pixel per cell, lightly blurred."""
        data = bytes(min(255, int(max(0.0, d) * 255)) for d in self.density)
        return PILImage.frombytes('L', (self.cols, self.rows), data).filter(ImageFilter.GaussianBlur(blur))


@lru_cache(maxsize=4)
def plume(frames, fps=30, cols=64, rows=36, source=(0.5, 0.9), radius=3.2, rate=1.0, seed=0, **kw):
    """Run a rising plume from `source` (fractions of the grid) for `frames`
    frames and return one density mask per frame (`Smoke.mask`). Cached, so a
    film's `draw(n, cv)` can index it in any frame order. `kw` goes to `Smoke`."""
    sim = Smoke(cols, rows, seed=seed, **kw)
    rnd = random.Random(seed + 1)
    out, dt = [], 1.0 / fps
    for _ in range(frames):
        sx = source[0] * cols + math.sin(len(out) * 0.21) * 0.6
        sim.emit(sx, source[1] * rows, radius, amount=rate * dt * 6, vx=rnd.uniform(-2, 2), vy=-14)
        sim.step(dt)
        out.append(sim.mask())
    return tuple(out)


def draw_smoke(cv, mask, x, y, w, h, color='#e8e6e1', alpha=1.0, softness=3):
    """Draw a density `mask` (from `plume` or `Smoke.mask`) stretched over the
    box (x, y, w, h) as `color` smoke, smoothed by `softness` px."""
    sw, sh = max(2, round(w / 4)), max(2, round(h / 4))
    a = mask.resize((sw, sh), PILImage.BICUBIC).filter(ImageFilter.GaussianBlur(softness / 4))
    rgba = PILImage.new('RGBA', (sw, sh), color)
    rgba.putalpha(a)
    cv.image(vb.Image.from_pil(rgba), x, y, w, h, alpha=alpha)


FRAMES = round(demo.SECONDS * demo.FPS)


def draw(n, cv):
    masks = plume(FRAMES, demo.FPS, seed=3, wind=4.0)
    nx, ny = demo.W / 2, demo.H * 0.9
    cv.rect(nx - 46, ny - 6, 92, demo.H - ny + 6, demo.MUTED, radius=8)  # the vent the smoke comes from
    draw_smoke(cv, masks[n], 0, 0, demo.W, demo.H)
    cv.mark('smoke', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='smoke-simulation',
    name='Smoke simulation',
    family='particles',
    group='Fluids',
    aliases=('fluid smoke', 'smoke sim', 'gas simulation', 'stable fluids'),
    definition='Soft smoke pours out of a source and rises, rolling into curls and eddies as a computed '
               'fluid carries it and it thins away.',
    phrasings=('real-looking smoke billowing up from a vent',
               'a plume of smoke that swirls and drifts like an actual fluid',
               'simulate rising smoke instead of faking it with sprites'),
    related=('curl-noise-flow', 'smoke-puffs', 'smoke-dissolve', 'turbulence-displacement',
             'doom-style-fire', 'smoke-overlay'),
    api=('videobuilder.capabilities.particles.smoke_simulation.Smoke',
         'videobuilder.capabilities.particles.smoke_simulation.plume',
         'videobuilder.capabilities.particles.smoke_simulation.draw_smoke'),
    demo=lambda: demo.film(draw),
)
