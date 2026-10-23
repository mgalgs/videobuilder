"""Smoke puffs: an emitter that releases soft, see-through blobs which swell,
drift upward and fade, stacking into a billowing column of smoke."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def puffs(t, rate=9.0, life=2.2, rise=420, spread=40, drift=0.0, size=(22, 120), seed=0):
    """The live puffs of an emitter at time `t` seconds, oldest first, as
    `(dx, dy, r, alpha)`: offset from the emitter (dy negative is up), radius
    and opacity. One puff leaves every `1 / rate` seconds and lives `life`
    seconds; over its life it rises `rise` (slowing as it goes), wanders
    sideways up to `spread` plus a steady lean of `drift` per second, grows
    from `size[0]` to `size[1]`, and fades in fast then out slowly. The same
    `seed` gives the same plume, frame for frame."""
    out = []
    first = math.floor((t - life) * rate) + 1
    for k in range(max(first, 0), math.floor(t * rate) + 1):
        age = (t - k / rate) / life
        if not 0 <= age < 1:
            continue
        rnd = random.Random(f'{seed}:{k}')
        jit, phase = rnd.uniform(-1, 1), rnd.uniform(0, 2 * math.pi)
        wob, grow = rnd.uniform(0.6, 1.4), rnd.uniform(0.8, 1.2)
        lift = 1 - (1 - age) ** 1.6  # quick off the emitter, slowing as it climbs
        dx = spread * (0.35 * jit + 0.65 * age * math.sin(phase + age * 3.2 * wob)) + drift * age * life
        dy = -rise * lift
        r = (size[0] + (size[1] - size[0]) * math.sqrt(age)) * grow
        alpha = min(1.0, age / 0.12) * (1 - age) ** 1.4
        out.append((dx, dy, r, alpha))
    return out


def draw_puff(cv, x, y, r, color, alpha=1.0):
    """One smoke blob centred at (x, y): a near-even body of `color` at
    `alpha` out to about 0.6 `r`, then a soft fall to clear at radius `r`, so
    each blob keeps a readable edge where it overlaps others."""
    red, green, blue, a = vb.rgba(color, alpha)
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0.0, red, green, blue, a)
    g.add_color_stop_rgba(0.6, red, green, blue, a * 0.85)
    g.add_color_stop_rgba(1.0, red, green, blue, 0)
    ctx = cv.ctx
    ctx.save()
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


def smoke_puffs(cv, x, y, t, color='#c9ccd6', strength=0.45, **kw):
    """Draw a smoke-puff emitter at (x, y) as it is `t` seconds after it
    started: every live puff from `puffs(t, **kw)` as a soft blob, oldest
    (highest, faintest) first so new puffs billow over the old. `strength`
    is a fresh puff's peak opacity. Returns the plume's bounding Box."""
    live = puffs(t, **kw)
    for dx, dy, r, a in live:
        draw_puff(cv, x + dx, y + dy, r, color, strength * a)
    if not live:
        return vb.Box(x, y, 0, 0)
    x0 = min(x + dx - r for dx, dy, r, a in live)
    y0 = min(y + dy - r for dx, dy, r, a in live)
    x1 = max(x + dx + r for dx, dy, r, a in live)
    y1 = max(y + dy + r for dx, dy, r, a in live)
    return vb.Box(x0, y0, x1 - x0, y1 - y0)


def draw(n, cv):
    x, y = demo.W / 2, demo.H - 80
    t = n / demo.FPS
    box = smoke_puffs(cv, x, y, t, rate=2.75, life=2.6, rise=300, spread=80, drift=16, size=(24, 110),
                      strength=0.7, seed=3)
    cv.rect(x - 46, y, 92, 18, demo.MUTED, radius=6)  # the vent the smoke leaves from
    cv.mark('plume', *box)


CAPABILITY = Capability(
    id='smoke-puffs',
    name='Smoke puffs',
    family='particles',
    group='Emitters',
    aliases=('puff particles', 'smoke sprites'),
    definition='A source keeps releasing soft, half-transparent blobs that swell, float upward and fade '
               'away, piling over each other into a rolling column of smoke.',
    phrasings=('little clouds of smoke puffing out and drifting up',
               'a chimney giving off soft puffs that grow and vanish',
               'billowy smoke made of overlapping fuzzy blobs'),
    related=('smoke-dissolve', 'smoke-overlay', 'smoke-simulation', 'curl-noise-flow', 'particle-morph',
             'layered-fog-bands'),
    api=('videobuilder.capabilities.particles.smoke_puffs.smoke_puffs',
         'videobuilder.capabilities.particles.smoke_puffs.puffs',
         'videobuilder.capabilities.particles.smoke_puffs.draw_puff'),
    demo=lambda: demo.film(draw),
)
