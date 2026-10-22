"""Pollen Drift: a steady trickle of tiny soft specks that float on a light
breeze, each wobbling lazily as it rises, fading in when it appears and out
before it goes, the near ones bigger, brighter and quicker than the far."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def pollen(t, w, h, count=90, seed=0, wind=(60.0, -35.0), life=(4.0, 8.0), wobble=26.0):
    """The specks of a pollen field `w` x `h` at `t` seconds, as
    `(x, y, depth, alpha)` tuples drawn far to near. `depth` runs 0 (far) to
    1 (near) and scales speed; `alpha` fades each speck in and out over its
    life. Each of `count` slots respawns at a fresh random spot when its
    speck's life (seconds, picked from `life`) runs out, so the field never
    empties or bunches. `wind` is the breeze in px/s for a near speck;
    `wobble` the sideways sway in px. The same arguments give the same
    field, frame for frame, so it can start mid-flow at any `t`."""
    out = []
    for i in range(count):
        slot = random.Random(f'{seed}:{i}')
        span = slot.uniform(*life)
        t0 = t + slot.uniform(0, span)          # stagger the slots so they don't all respawn together
        cycle, age = divmod(t0, span)
        rnd = random.Random(f'{seed}:{i}:{int(cycle)}')
        depth = rnd.random() ** 1.6             # mostly far, a few close
        speed = 0.35 + 0.65 * depth
        x0, y0 = rnd.uniform(-0.15, 1.15) * w, rnd.uniform(-0.1, 1.1) * h
        freq, ph = rnd.uniform(0.25, 0.6), rnd.uniform(0, 2 * math.pi)
        sway = wobble * (0.4 + 0.6 * depth)
        x = x0 + wind[0] * speed * age + sway * math.sin(2 * math.pi * freq * age + ph)
        y = y0 + wind[1] * speed * age + sway * 0.6 * math.sin(2 * math.pi * freq * 1.7 * age + ph * 1.3)
        u = age / span
        alpha = min(1.0, u / 0.2, (1 - u) / 0.25) * (0.35 + 0.65 * depth)
        out.append((x, y, depth, alpha))
    out.sort(key=lambda s: s[2])
    return out


def draw_pollen(cv, t, w=None, h=None, color='#ffd27a', size=(2.0, 9.0), glow=3.2, **kw):
    """Draw a pollen field over the canvas (or `w` x `h` from its top-left)
    at `t` seconds: each speck a bright core in a soft halo `glow` times its
    radius, its radius running across `size` from far to near. `kw` goes to
    `pollen`. Returns the specks drawn."""
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    specks = pollen(t, w, h, **kw)
    ctx = cv.ctx
    for x, y, depth, alpha in specks:
        if alpha <= 0.01:
            continue
        r = size[0] + (size[1] - size[0]) * depth
        halo = r * glow
        g = cairo.RadialGradient(x, y, 0, x, y, halo)
        g.add_color_stop_rgba(0, *vb.rgba(color, alpha))
        g.add_color_stop_rgba(r / halo, *vb.rgba(color, alpha * 0.55))
        g.add_color_stop_rgba(1, *vb.rgba(color, 0))
        ctx.set_source(g)
        ctx.arc(x, y, halo, 0, 2 * math.pi)
        ctx.fill()
    return specks


def draw(n, cv):
    t = n / demo.FPS + 6.0     # start mid-flow so the first frame is already full
    # A warm shaft of light from the top left for the specks to drift through.
    g = cairo.LinearGradient(0, 0, demo.W * 0.7, demo.H)
    g.add_color_stop_rgba(0, *vb.rgba('#3a2f1c', 1))
    g.add_color_stop_rgba(0.55, *vb.rgba(demo.BG, 1))
    g.add_color_stop_rgba(1, *vb.rgba(demo.BG, 1))
    cv.ctx.set_source(g)
    cv.ctx.paint()
    draw_pollen(cv, t, demo.W, demo.H, count=110, seed=3)
    cv.mark('field', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='pollen-drift',
    name='Pollen drift',
    family='particles',
    group='Emitters',
    aliases=('floating dust', 'dust motes', 'floating particles', 'ambient particles', 'fairy dust'),
    definition='A constant scatter of tiny glowing specks floats across the frame on a gentle breeze, '
               'each swaying on its own path and fading in and out, the closer ones larger and faster.',
    phrasings=('little bits of dust floating in the sunlight',
               'soft glowing particles drifting slowly through the background',
               'pollen hanging in the air and drifting on the wind'),
    related=('spiral-bloom', 'wander-steering', 'voronoi-relaxation', 'turbulence-displacement', 'wind-field',
             'phyllotaxis'),
    api=('videobuilder.capabilities.particles.pollen_drift.draw_pollen',
         'videobuilder.capabilities.particles.pollen_drift.pollen'),
    demo=lambda: demo.film(draw),
)
