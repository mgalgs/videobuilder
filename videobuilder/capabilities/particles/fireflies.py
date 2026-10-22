"""Fireflies: a scatter of small warm lights drifting on wandering paths, each
one glowing up and going dark again on its own uneven beat."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _glow(cv, x, y, r, color, alpha):
    cr, cg, cb, _ = vb.rgba(color)
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, cr, cg, cb, alpha)
    g.add_color_stop_rgba(0.25, cr, cg, cb, alpha * 0.45)
    g.add_color_stop_rgba(1, cr, cg, cb, 0)
    cv.ctx.arc(x, y, r, 0, 2 * math.pi)
    cv.ctx.set_source(g)
    cv.ctx.fill()


def _blink(rnd_seed, t, period):
    """Brightness 0..1 at time `t`: a sequence of flashes whose timing, length
    and strength change from one cycle to the next, so no two flies (and no
    two flashes) keep the same rhythm."""
    k = math.floor(t / period)
    out = 0.0
    for c in (k - 1, k):        # a long flash can spill into the next cycle
        r = random.Random(f'{rnd_seed}:{c}')
        if r.random() < 0.25:   # some cycles stay dark
            continue
        start = (c + r.uniform(0.0, 0.6)) * period
        length = period * r.uniform(0.35, 0.8)
        u = (t - start) / length
        if 0 <= u <= 1:
            out = max(out, r.uniform(0.6, 1.0) * math.sin(math.pi * u) ** 2)
    return out


def fireflies(cv, t, box=None, count=24, seed=0, color='#e8f27a', core='#f8ffb0', size=7.0,
              wander=0.12, speed=1.0, alpha=1.0):
    """Draw a swarm of fireflies at time `t` (seconds) inside `box` (default:
    the whole canvas). Each fly drifts along its own smooth, wandering path
    (about `wander` of the box's shorter side from its home) and flashes on
    and off at an irregular pace. `size` is a fly's lit core radius; the glow
    around it spreads several times wider. `speed` scales both drift and
    blinking. The same `seed` gives the same swarm, frame for frame, so a film
    just passes its own clock: `fireflies(cv, f / fps, seed=3)`."""
    x0, y0, w, h = box if box is not None else (0, 0, cv.width, cv.height)
    m = min(w, h)
    rnd = random.Random(f'fireflies:{seed}')
    tt = t * speed
    for i in range(count):
        hx, hy = rnd.uniform(0.05, 0.95), rnd.uniform(0.05, 0.95)
        waves = [(rnd.uniform(0.15, 0.6), rnd.uniform(0, 2 * math.pi), rnd.uniform(0.3, 1.0)) for _ in range(6)]
        period = rnd.uniform(0.9, 2.2)
        s = size * rnd.uniform(0.7, 1.2)
        dx = sum(a * math.sin(2 * math.pi * f * tt + ph) for f, ph, a in waves[:3]) / 2.2
        dy = sum(a * math.sin(2 * math.pi * f * tt + ph) for f, ph, a in waves[3:]) / 2.2
        x = x0 + hx * w + dx * wander * m
        y = y0 + hy * h + dy * wander * m
        b = _blink(f'{seed}:{i}', tt + i * 0.37, period) * alpha
        if b < 0.02:
            continue
        _glow(cv, x, y, s * 6, color, 0.35 * b)
        _glow(cv, x, y, s * 1.6, color, 0.9 * b)
        cv.sector(x, y, s * 0.55, 0, 2 * math.pi, core, alpha=b)


def draw(n, cv):
    cv.fill('#0b1018')
    fireflies(cv, n / demo.FPS, count=30, seed=4, size=8)


CAPABILITY = Capability(
    id='fireflies',
    name='Fireflies',
    family='particles',
    group='Emitters',
    aliases=('firefly swarm', 'blinking lights', 'firefly glow'),
    definition='Little points of warm light drift around on loose, wandering paths, '
               'each one fading up and going dark again on its own uneven timing.',
    phrasings=('glowing specks floating around and blinking like fireflies on a summer night',
               'tiny lights that wander about and twinkle on and off at random',
               'a dark background with a few soft lights drifting and pulsing'),
    related=('bloom', 'neon-flicker', 'lens-flare', 'kuramoto-synchronization', 'diffraction-spikes',
             'glow-button'),
    api=('videobuilder.capabilities.particles.fireflies.fireflies',),
    demo=lambda: demo.film(draw),
)
