"""Ink Splash Spread: a blot bursts out of a point with sharp, spiky arms and
flung droplets, then relaxes into a rounded, lobed splat that stays put."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _smooth(x):
    x = vb.clamp01(x)
    return x * x * (3 - 2 * x)


def _shape(seed, arms):
    """The splat's fixed features for `seed`: lobes, arms, jag phases and droplets."""
    rnd = random.Random(f'ink-splash:{seed}')
    lobes = [(k, rnd.uniform(0.03, 0.08), rnd.uniform(0, 2 * math.pi)) for k in (3, 4, 5, 7)]
    step = 2 * math.pi / arms
    spikes = [(i * step + rnd.uniform(-0.3, 0.3) * step, rnd.uniform(0.25, 0.6)) for i in range(arms)]
    jags = [(k, rnd.uniform(0, 2 * math.pi)) for k in (17, 23, 31)]
    drops = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(1.15, 1.6), rnd.uniform(0.03, 0.07), rnd.uniform(0, 0.25))
             for _ in range(12)]
    return lobes, spikes, jags, drops


def splat_points(cx, cy, radius, p, seed=0, arms=9, samples=240):
    """The splat's outline at progress `p` (0 -> 1) as a closed list of (x, y)
    points around (cx, cy). It grows fast to about `radius` (arms reach past
    it); early on its arms are thin, long and jagged, and by `p = 1` they have
    thickened and pulled in to rounded lobes. The same `seed` gives the same
    splat, frame for frame -- usable as a clip for an ink reveal."""
    p = vb.clamp01(p)
    if p <= 0:
        return []
    lobes, spikes, jags, _ = _shape(seed, arms)
    grow = vb.ease_out_expo(p)
    settle = _smooth((p - 0.25) / 0.75)
    width = 0.06 + 0.16 * settle        # an arm's angular spread, radians
    reach = 1.0 - 0.45 * settle         # arms pull back as the ink settles
    jag = 0.07 * (1 - settle)
    out = []
    for i in range(samples):
        a = 2 * math.pi * i / samples
        r = 1.0 + sum(amp * math.sin(k * a + ph) for k, amp, ph in lobes)
        for at, length in spikes:
            d = (a - at + math.pi) % (2 * math.pi) - math.pi
            r += length * reach * math.exp(-(d / width) ** 2)
        r += jag * sum(math.sin(k * a + ph) for k, ph in jags) / len(jags)
        r *= radius * 0.8 * grow
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def draw_ink_splash(cv, cx, cy, radius, p, color, seed=0, arms=9, droplets=True, alpha=1.0):
    """Draw the ink splash at progress `p` (0 -> 1) centred on (cx, cy): the
    `splat_points` blot plus, if `droplets`, a scatter of drops flung out past
    its edge. Call it every frame with `p` from the film's own timing, e.g.
    `vb.clamp01((t - start) / 1.2)`; hold `p = 1` for the settled splat."""
    pts = splat_points(cx, cy, radius, p, seed, arms)
    if not pts:
        return
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for x, y in pts[1:]:
        c.line_to(x, y)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color, alpha))
    c.fill()
    if droplets:
        fly = vb.ease_out_expo(vb.clamp01(p * 1.4))
        for a, dist, size, delay in _shape(seed, arms)[3]:
            q = vb.clamp01((p - delay) / (1 - delay))
            if q <= 0:
                continue
            d = radius * dist * vb.ease_out_expo(q) * fly
            demo.dot(cv, cx + d * math.cos(a), cy + d * math.sin(a), radius * size, color, alpha)
    cv.mark('splat', cx - radius * 1.6, cy - radius * 1.6, radius * 3.2, radius * 3.2)


def draw(n, cv):
    draw_ink_splash(cv, demo.W / 2, demo.H / 2, 165, demo.phase(n, 0.4, 2.0), demo.ACCENT, seed=3)


CAPABILITY = Capability(
    id='ink-splash-spread',
    name='Ink splash spread',
    family='shapes',
    group='Liquid & organic',
    aliases=('ink blot spread', 'splat reveal', 'paint splat'),
    definition='A ragged blot of ink bursts out from one spot, throwing spiky arms and drops, '
               'then calms into a rounded, uneven splat that stays.',
    phrasings=('a paint splat that bursts out and settles',
               'make it splash out like spilled ink',
               'a blob of ink that splatters open from the middle'),
    related=('ink-spread-reveal', 'ink-bleed', 'ink-in-water', 'ink-outline', 'touch-ripple', 'line-boil'),
    api=('videobuilder.capabilities.shapes.ink_splash_spread.draw_ink_splash',
         'videobuilder.capabilities.shapes.ink_splash_spread.splat_points'),
    demo=lambda: demo.film(draw),
)
