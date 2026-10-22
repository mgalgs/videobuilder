"""Bubbles: see-through spheres drift upward on a weaving path, swelling a
little as they climb, and pop in a small ring and spray when they reach the
surface."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def bubbles(t, x, top, w, h, count=14, seed=0, size=(10, 46), rise=(2.2, 4.0), sway=18, pop=0.35):
    """The bubbles of a column `w` wide rising from `top + h` to the surface
    at `top`, at time `t` seconds, as dicts `x, y, r` plus `popping`, 0 while
    rising and 0 -> 1 across its pop. Each bubble loops forever on its own
    seeded radius (in `size`), rise time (in `rise` seconds, bigger is
    faster), start offset and weave of up to `sway` px; it grows a fifth on
    the way up and takes `pop` seconds to pop. Same `seed`, same bubbles."""
    out = []
    for i in range(count):
        rng = random.Random(f'{seed}:{i}')
        r0 = size[0] + (size[1] - size[0]) * rng.random() ** 1.6
        dur = rise[1] - (rise[1] - rise[0]) * (r0 - size[0]) / max(size[1] - size[0], 1e-9)
        cycle = dur + pop
        age = (t + rng.random() * cycle) % cycle
        x0 = x + w * (0.06 + 0.88 * rng.random())
        wob, ph = rng.uniform(1.2, 2.4), rng.uniform(0, 2 * math.pi)
        u = min(age / dur, 1.0)
        r = r0 * (0.85 + 0.2 * u)
        bx = x0 + sway * (r0 / size[1]) ** 0.5 * math.sin(2 * math.pi * wob * u * dur / 2 + ph)
        by = top + h + r - (h + r) * u ** 1.4  # speeding up a little as it climbs
        out.append(dict(x=bx, y=by, r=r, popping=vb.clamp01((age - dur) / pop) if age > dur else 0.0, seed=i))
    return out


def draw_bubble(cv, cx, cy, r, color=demo.INK, alpha=1.0):
    """One bubble at (cx, cy): a faint body, a bright rim, a highlight up-left
    and a softer glint along the lower right edge."""
    cv.sector(cx, cy, r, 0, 2 * math.pi, color, alpha=0.08 * alpha)
    cv.arc(cx, cy, r, 0, 2 * math.pi, color, width=max(1.5, r * 0.07), alpha=0.6 * alpha)
    cv.arc(cx, cy, r * 0.8, 0.15 * math.pi, 0.55 * math.pi, color, width=max(1, r * 0.06), alpha=0.3 * alpha)
    cv.sector(cx - r * 0.38, cy - r * 0.42, max(1.5, r * 0.15), 0, 2 * math.pi, color, alpha=0.9 * alpha)


def draw_pop(cv, cx, cy, r, p, color=demo.INK, seed=0):
    """A bubble of radius `r` popping at progress `p` (0 -> 1): the skin
    flashes into a widening, fading ring and a handful of droplets fly out
    and fall."""
    if p <= 0 or p >= 1:
        return
    e = vb.ease_out_quint(p)
    cv.arc(cx, cy, r * (1 + 0.6 * e), 0, 2 * math.pi, color, width=max(1, r * 0.08 * (1 - p)), alpha=0.7 * (1 - p))
    rng = random.Random(f'pop:{seed}')
    for k in range(8):
        a = -math.pi * (0.1 + 0.8 * k / 7) + rng.uniform(-0.15, 0.15)
        d = r * (1 + 1.4 * e) * rng.uniform(0.8, 1.2)
        cv.sector(cx + d * math.cos(a), cy + d * math.sin(a) + 60 * p * p, max(1.5, r * 0.08), 0, 2 * math.pi,
                  color, alpha=0.9 * (1 - p))


def draw_bubbles(cv, t, x, top, w, h, color=demo.INK, **kw):
    """Draw the column of `bubbles(t, x, top, w, h, **kw)`: rising ones as
    bubbles, those at the surface popping."""
    for b in bubbles(t, x, top, w, h, **kw):
        if b['popping'] > 0:
            draw_pop(cv, b['x'], b['y'], b['r'], b['popping'], color, seed=b['seed'])
        else:
            draw_bubble(cv, b['x'], b['y'], b['r'], color)


def draw(n, cv):
    t = n / demo.FPS
    surface = 230
    for k in range(12):  # the water, darkening with depth
        y0 = surface + (demo.H - surface) * k / 12
        cv.rect(0, y0, demo.W, (demo.H - surface) / 12 + 1, '#2c3a5c', alpha=0.9 - 0.05 * k)
    wave = lambda x: surface + 3 * math.sin(x / 70 + t * 2.4)  # noqa: E731
    for k in range(64):  # a gently moving surface line
        x0, x1 = demo.W * k / 64, demo.W * (k + 1) / 64
        cv.line(x0, wave(x0), x1, wave(x1), demo.INK, width=2, alpha=0.55)
    draw_bubbles(cv, t + 1.5, 120, surface, demo.W - 240, demo.H - surface, count=14, seed=3, size=(14, 64), sway=26)
    cv.mark('water', 0, surface, demo.W, demo.H - surface)


CAPABILITY = Capability(
    id='bubbles',
    name='Bubbles',
    family='particles',
    group='Emitters',
    aliases=('rising bubbles', 'soap bubbles', 'air bubbles'),
    definition='Clear, glinting spheres float upward on a swaying path, swelling slightly as they go, '
               'and burst when they reach the top.',
    phrasings=('bubbles floating up through water and popping at the top',
               'fill the background with rising air bubbles',
               'little fizzy bubbles drifting upward'),
    related=('circle-pop', 'ripple', 'liquid-fill-level', 'wobble', 'height-field-ripples', 'domain-warping'),
    api=('videobuilder.capabilities.particles.bubbles.draw_bubbles',
         'videobuilder.capabilities.particles.bubbles.bubbles',
         'videobuilder.capabilities.particles.bubbles.draw_bubble',
         'videobuilder.capabilities.particles.bubbles.draw_pop'),
    demo=lambda: demo.film(draw),
)
