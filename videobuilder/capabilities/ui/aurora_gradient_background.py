"""Aurora Gradient Background: the same idea as Gradient Mesh Drift
(`../shapes/gradient_mesh_drift.py`, which keeps the capability) -- soft
pools of colour wandering and blending into one shifting gradient, here
drawn as a few large glows behind the content. This module's own code
stays (a film may still import it), but it is no longer a capability of
its own."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'gradient-mesh-drift'

COLORS = ('#6d6cf0', '#c9a227', '#4fc3b0', '#8a4fd8')


def _glow(ctx, cx, cy, r, color, alpha, squash):
    """One blob: a radial falloff from `color` at `alpha` to nothing, with a
    gentle shoulder so the edge has no visible rim. `squash` < 1 flattens it."""
    cr, cg, cb, _ = vb.rgba(color)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, r)
    for k in range(7):
        s = k / 6
        g.add_color_stop_rgba(s, cr, cg, cb, alpha * math.exp(-2.5 * s * s) * (1 - s * s))
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(1, squash)
    ctx.rectangle(-r, -r, 2 * r, 2 * r)
    ctx.set_source(g)
    ctx.fill()
    ctx.restore()


def aurora(cv, t, box=None, colors=COLORS, blobs=None, size=0.4, drift=0.2, period=6.0,
           alpha=0.9, seed=0, base=None):
    """Draw an aurora backdrop at time `t` seconds into `box` (default: the
    whole canvas). `blobs` soft glows (default one per colour, cycling through
    `colors`) each wander on their own slow looping path; `size` is a blob's
    radius as a fraction of the box's longer side, `drift` how far it strays
    from home as a fraction of the box, `period` roughly how many seconds one
    lap takes. Overlaps are screen-blended so they brighten rather than
    muddy. `base` fills the box first if given. The same `seed` gives the
    same paths, so a film can call it every frame. Draw content on top."""
    x, y, w, h = box if box is not None else (0, 0, cv.width, cv.height)
    ctx = cv.ctx
    ctx.save()
    ctx.rectangle(x, y, w, h)
    ctx.clip()
    if base:
        ctx.set_source_rgba(*vb.rgba(base))
        ctx.paint()
    ctx.set_operator(cairo.OPERATOR_SCREEN)
    rng = random.Random(seed)
    n = blobs or len(colors)
    big = max(w, h)
    for i in range(n):
        hx, hy = rng.uniform(0.2, 0.8), rng.uniform(0.2, 0.8)
        fx, fy = rng.uniform(0.7, 1.3), rng.uniform(0.7, 1.3)
        px, py = rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)
        sign = rng.choice((-1, 1))
        a = 2 * math.pi * t / period
        cx = x + w * (hx + drift * math.sin(sign * fx * a + px))
        cy = y + h * (hy + drift * math.cos(fy * a + py))
        r = big * size * rng.uniform(0.8, 1.15) * (1 + 0.08 * math.sin(a * 0.7 + px))
        _glow(ctx, cx, cy, r, colors[i % len(colors)], alpha, rng.uniform(0.6, 0.9))
    ctx.restore()


def draw(n, cv):
    aurora(cv, n / demo.FPS, blobs=5, period=4.0, seed=2)
    cx, cy, w, h = demo.W / 2, demo.H / 2, 520, 300
    x, y = cx - w / 2, cy - h / 2
    cv.shadow(x, y, w, h, radius=24, dy=14, blur=40, color=(0, 0, 0, 0.5))
    cv.rect(x, y, w, h, '#1d1f26', radius=24, alpha=0.92)
    cv.rect(x + 40, y + 44, 240, 20, demo.INK, radius=10, alpha=0.85)
    cv.rect(x + 40, y + 90, 400, 12, demo.MUTED, radius=6, alpha=0.7)
    cv.rect(x + 40, y + 116, 330, 12, demo.MUTED, radius=6, alpha=0.7)
    cv.rect(x + 40, y + 196, 150, 60, COLORS[0], radius=14)
    cv.mark('card', x, y, w, h)
