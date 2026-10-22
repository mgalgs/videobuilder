"""Gradient mesh drift: a field of soft colour pools, each wandering on its own
slow orbit, so the blended gradient they make keeps reshaping itself."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

COLORS = ('#ff5e7e', '#ffb347', '#5b8cff', '#2ec4b6', '#a86bff')


def mesh_points(t, count, seed=0, reach=0.32, speed=1.0):
    """Where `count` colour points sit at time `t` (seconds), as (u, v) pairs in
    0..1 of the box. Each orbits its own seeded home on a Lissajous path of
    radius `reach`, at `speed` radians a second or so; the same seed gives the
    same paths, frame for frame."""
    out = []
    for i in range(count):
        r = random.Random(f'{seed}:{i}')
        hu, hv = r.uniform(0.15, 0.85), r.uniform(0.15, 0.85)
        fu, fv = r.uniform(0.6, 1.1) * speed, r.uniform(0.5, 1.0) * speed
        pu, pv = r.uniform(0, 2 * math.pi), r.uniform(0, 2 * math.pi)
        out.append((hu + reach * math.sin(fu * t + pu), hv + reach * 0.8 * math.cos(fv * t + pv)))
    return out


def draw_mesh_drift(cv, x, y, w, h, t, colors=COLORS, base='#1b1530', seed=0, reach=0.32, speed=1.0,
                    size=0.5, radius=0):
    """Fill the box (x, y, w, h) with a drifting mesh gradient at time `t`
    (seconds): a `base` fill under one soft radial pool per colour in `colors`,
    each centred on its `mesh_points` path and fading out `size` times the box's
    long side away. Call it every frame with the film's time; a background is the box
    of the whole frame. `radius` rounds the box's corners. Returns its Box."""
    c = cv.ctx
    span = max(w, h) * size
    with cv.clip(x, y, w, h, radius=radius):
        cv.rect(x, y, w, h, base)
        for (u, v), color in zip(mesh_points(t, len(colors), seed, reach, speed), colors):
            cx, cy = x + u * w, y + v * h
            g = cairo.RadialGradient(cx, cy, 0, cx, cy, span)
            r, gr, b, _ = vb.rgba(color)
            for stop, a in ((0, 1.0), (0.3, 0.75), (0.65, 0.25), (1, 0.0)):
                g.add_color_stop_rgba(stop, r, gr, b, a)
            c.set_source(g)
            c.rectangle(x, y, w, h)
            c.fill()
    return vb.Box(x, y, w, h)


def draw(n, cv):
    t = n / demo.FPS
    m = 60
    box = draw_mesh_drift(cv, m, m, demo.W - 2 * m, demo.H - 2 * m, t, seed=3, speed=1.4, radius=28)
    cv.mark('mesh', *box)


CAPABILITY = Capability(
    id='gradient-mesh-drift',
    name='Gradient mesh drift',
    family='shapes',
    group='Gradients & color',
    aliases=('mesh gradient', 'animated mesh gradient', 'fluid gradient', 'blob gradient'),
    definition='Several soft pools of colour blend into one smooth gradient and slowly wander about, '
               'so the colours keep flowing into new shapes.',
    phrasings=('a colourful blurry gradient background that slowly moves around',
               'soft blobs of colour drifting and blending into each other',
               'a liquid, shifting gradient like a modern app wallpaper'),
    related=('aurora-gradient-background', 'gradient-shift-button', 'gradient-sweep-across-text',
             'perlin-noise-field', 'turbulence-displacement', 'gradient-border-spin'),
    api=('videobuilder.capabilities.shapes.gradient_mesh_drift.draw_mesh_drift',
         'videobuilder.capabilities.shapes.gradient_mesh_drift.mesh_points'),
    demo=lambda: demo.film(draw),
)
