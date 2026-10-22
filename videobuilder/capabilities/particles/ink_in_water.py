"""Ink in Water: a drop of dye sinks through still water, its head rolling
out into a curling ring of plumes while a wispy stem trails behind it."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ink_plume(t, seed=0, count=900, depth=300, spread=1.0):
    """The ink `t` seconds after the drop enters the water, as `(dx, dy, r,
    alpha)` blobs relative to the entry point (y grows downwards). The head
    sinks `depth` px, slowing as it goes, and rolls out into a vortex ring
    seen slightly from above, `spread` times as wide as the default; the rest
    of the blobs are shed behind it as a stem. Every blob is a pure function
    of `t` and `seed`, so any frame draws on its own."""
    rnd = random.Random(seed)
    t = max(0.0, t)
    head = depth * (1 - math.exp(-t / 1.1))            # how far down the head has sunk
    ring = spread * (70 * (1 - math.exp(-t / 0.9)) + 14 * t)  # ring radius about the sinking axis
    core = 4 + 0.32 * ring                              # thickness of the rolling ring
    roll = 7 * (1 - math.exp(-t / 1.4))                 # how far the ring has rolled, radians
    out = []
    for i in range(count):
        p1, p2, p3 = (rnd.uniform(0, 2 * math.tau) for _ in range(3))
        if i % 5 < 3:   # the head: a torus whose cross-section turns outer-edge-up
            psi = rnd.uniform(0, math.tau)
            phi = rnd.uniform(0, math.tau) - roll * rnd.uniform(0.7, 1.3)
            rho = core * rnd.uniform(0.35, 1.0)
            radial = ring + rho * math.cos(phi)
            x = radial * math.cos(psi)
            y = head + rho * math.sin(phi) + 0.28 * radial * math.sin(psi)
            age = t
            r0, a0 = rnd.uniform(3, 7), rnd.uniform(0.07, 0.16)
        else:           # the stem: shed from the head on the way down, then left to drift
            born = rnd.uniform(0, 1) ** 1.4 * 2.6
            if born > t:
                continue
            age = t - born
            x = rnd.gauss(0, 3 + 7 * age) * spread
            y = depth * (1 - math.exp(-born / 1.1)) + 6 * age
            r0, a0 = rnd.uniform(3, 7), rnd.uniform(0.05, 0.13)
        # Turbulence: a few slow travelling waves bend everything into tendrils, more with age.
        amp = 18 * (1 - math.exp(-age / 0.9)) * spread
        x += amp * (math.sin(0.045 * y + 1.6 * t + p1) + 0.5 * math.sin(0.11 * y - 2.1 * t + p2))
        y += 0.6 * amp * math.sin(0.05 * x + 1.3 * t + p3)
        fade_in = vb.clamp01(t / 0.12)
        out.append((x, y, r0 * (1 + 0.8 * age), a0 * fade_in / (1 + 0.5 * age)))
    return out


def draw_ink_in_water(cv, x, y, t, color, **kw):
    """Draw the ink `t` seconds after a drop enters the water at (x, y) as
    soft blobs of `color`, densest where the dye is thickest. `kw` goes to
    `ink_plume`. Returns the Box the ink covers."""
    r, g, b, _ = vb.canvas.rgba(color)
    c = cv.ctx
    blobs = ink_plume(t, **kw)
    for dx, dy, rad, a in blobs:
        cx, cy = x + dx, y + dy
        grad = cairo.RadialGradient(cx, cy, 0, cx, cy, rad)
        grad.add_color_stop_rgba(0, r, g, b, a)
        grad.add_color_stop_rgba(0.5, r, g, b, a * 0.6)
        grad.add_color_stop_rgba(1, r, g, b, 0)
        c.set_source(grad)
        c.new_path()
        c.arc(cx, cy, rad, 0, math.tau)
        c.fill()
    if not blobs:
        return vb.Box(x, y, 0, 0)
    x0 = min(dx - rad for dx, _, rad, _ in blobs)
    x1 = max(dx + rad for dx, _, rad, _ in blobs)
    y0 = min(dy - rad for _, dy, rad, _ in blobs)
    y1 = max(dy + rad for _, dy, rad, _ in blobs)
    return vb.Box(x + x0, y + y0, x1 - x0, y1 - y0)


ENTER = 0.35  # when the demo's drop reaches the water


def draw(n, cv):
    t = n / demo.FPS
    surface, cx = 120, demo.W / 2
    tank = vb.Box(cx - 300, surface - 30, 600, 420)
    cv.rect(tank.x, surface, tank.w, tank.y + tank.h - surface, '#1b2a36', radius=0, alpha=0.55)
    cv.outline(*tank, demo.LINE, width=3, radius=14)
    cv.line(tank.x, surface, tank.x + tank.w, surface, '#3d5a6e', width=2)
    color = '#7b7cff'
    if t < ENTER:   # the drop falling towards the surface
        dy = surface - 90 + 90 * (t / ENTER) ** 2
        cv.rect(cx - 6, dy - 12, 12, 20, color, radius=6)
    else:
        ripple = demo.phase(n, ENTER, ENTER + 0.8)
        if ripple < 1:
            cv.outline(cx - 160 * ripple, surface - 6 * ripple, 320 * ripple, 12 * ripple, '#7fa6c0',
                       width=2, radius=6 * ripple, alpha=0.8 * (1 - ripple))
        with cv.clip(tank.x, surface, tank.w, tank.y + tank.h - surface):
            box = draw_ink_in_water(cv, cx, surface, t - ENTER, color, seed=3)
        cv.mark('ink', *box)


TECHNIQUE = Technique(
    id='ink-in-water',
    name='Ink in water',
    family='particles',
    group='Fluids',
    aliases=('dye diffusion', 'ink drop', 'ink plume'),
    definition='A drop of dye falls into still water and sinks, its leading edge rolling outward '
               'into curling, smoky plumes while a thin wispy trail hangs behind it.',
    phrasings=('drop some ink into a glass of water and let it swirl out',
               'colored dye billowing and curling as it sinks through water',
               'that slow-motion ink cloud blooming underwater'),
    related=('ink-bleed', 'ink-splash-spread', 'watercolor-bleed', 'ink-spread-reveal', 'touch-ripple',
             'ink-outline'),
    api=('videobuilder.techniques.particles.ink_in_water.draw_ink_in_water',
         'videobuilder.techniques.particles.ink_in_water.ink_plume'),
    demo=lambda: demo.film(draw),
)
