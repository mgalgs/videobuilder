"""Lava lamp: soft blobs of warm wax lift off a pool at the bottom of a glass,
drift up, cool against the cap and sink again, pinching off and rejoining as
they pass. The fusing is `liquid_morph.metaballs`; what this adds is the
convection (each blob's slow rise-and-fall cycle) and the lamp it lives in."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ..transitions.liquid_morph import metaballs


def lava_blobs(t, x, y, w, h, count=6, period=7.0, seed=0):
    """The wax at time `t` (seconds) inside the box (x, y, w, h), as
    `(cx, cy, r)` balls for `metaballs`. A pool sits along the bottom and a
    thin cap under the top; `count` blobs each ride a slow loop between them
    (about `period` seconds round, eased at both ends so they linger to heat
    and cool), sway sideways, and stretch tall while they travel fastest.
    Deterministic for a given `seed`."""
    rnd = random.Random(seed)
    unit = min(w, h * 0.45)
    bottom, top = y + h, y
    out = []
    # the warm pool: a row of wide, gently heaving balls sunk below the bottom edge
    for k in range(5):
        px = x + w * (0.1 + 0.8 * k / 4)
        out.append((px, bottom + unit * 0.12 + unit * 0.05 * math.sin(t * 1.1 + k * 1.7), unit * 0.3))
    # the cooled cap, hanging just under the top
    for k in range(3):
        out.append((x + w * (0.3 + 0.2 * k), top - unit * 0.08 + unit * 0.03 * math.sin(t * 0.9 + k),
                    unit * 0.14))
    for i in range(count):
        size = unit * rnd.uniform(0.14, 0.2)
        per = period * rnd.uniform(0.8, 1.25)
        ph = (i / count + rnd.uniform(-0.08, 0.08)) * 2 * math.pi
        a = 2 * math.pi * t / per + ph
        lift = 0.5 - 0.5 * math.cos(a)                 # 0 at the pool, 1 at the cap, slow at both
        speed = abs(math.sin(a))                       # fastest mid-journey
        lane = rnd.uniform(0.22, 0.78)
        cx = x + w * (lane + 0.08 * math.sin(a * 1.5 + i))
        cy = bottom - size * 0.6 - (h - size * 1.6) * lift
        r = size * (1 + 0.12 * speed)
        # a travelling blob is a short stack of balls, so it reads tall rather than round
        out.append((cx, cy - r * 0.35 * speed, r * (1 - 0.15 * speed)))
        out.append((cx, cy + r * 0.35 * speed, r * (1 - 0.15 * speed)))
    return out


def lamp_glass(cx, top, bottom, top_w, bottom_w, curve=0.12, n=24):
    """The outline of a tapered lamp glass centred on `cx`: `top_w` wide at
    `top`, `bottom_w` at `bottom`, the sides bowing out by `curve` of the
    height. A closed point list."""
    h = bottom - top
    left, right = [], []
    for j in range(n + 1):
        s = j / n
        half = (top_w + (bottom_w - top_w) * s) / 2 + h * curve * 0.25 * math.sin(math.pi * s)
        left.append((cx - half, top + h * s))
        right.append((cx + half, top + h * s))
    return right + left[::-1]


def draw_lava_lamp(cv, cx, top, bottom, t, width=None, wax=demo.ACCENT, glass='#1d2433', metal='#2c3444',
                   count=6, period=7.0, seed=0, goo=40):
    """Draw a whole lava lamp, glass from `top` to `bottom` on centre `cx`,
    its wax at time `t` (seconds): cap, glass, convecting wax (clipped to the
    glass) and base. `width` is the glass's widest point (default half its
    height). Returns the glass's Box."""
    h = bottom - top
    width = width or h * 0.5
    top_w, bottom_w = width * 0.5, width
    pts = lamp_glass(cx, top, bottom, top_w, bottom_w)
    xs = [p[0] for p in pts]
    # cap and base
    cv.rect(cx - top_w * 0.55, top - h * 0.05, top_w * 1.1, h * 0.07, metal, radius=h * 0.015)
    vb.paths.draw(cv, [(cx - bottom_w * 0.5, bottom), (cx + bottom_w * 0.5, bottom),
                       (cx + bottom_w * 0.68, bottom + h * 0.13), (cx - bottom_w * 0.68, bottom + h * 0.13)],
                  metal, fill=True)
    vb.paths.draw(cv, pts, glass, fill=True)
    c = cv.ctx
    c.save()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.clip()
    wide = max(xs) - min(xs)
    metaballs(cv, lava_blobs(t, min(xs), top, wide, h, count, period, seed), wax, goo=goo)
    # a soft highlight down the glass
    cv.rect(cx - wide * 0.32, top + h * 0.08, wide * 0.05, h * 0.75, '#ffffff', radius=wide * 0.025, alpha=0.07)
    c.restore()
    vb.paths.draw(cv, pts, '#3a4458', width=3)
    box = vb.Box(min(xs), top, wide, h)
    cv.mark('lamp', *box)
    return box


def draw(n, cv):
    # start mid-cycle so blobs are already in flight; a quick period keeps 3 s lively
    draw_lava_lamp(cv, demo.W / 2, demo.H * 0.14, demo.H * 0.8, 4.0 + n / demo.FPS, width=demo.H * 0.4,
                   period=4.0, seed=3)


TECHNIQUE = Technique(
    id='lava-lamp',
    name='Lava lamp',
    family='particles',
    group='Metaballs & blobs',
    aliases=('blob convection', 'wax blobs', 'lava blobs'),
    definition='Gooey blobs of glowing wax swell off a pool, float slowly up, then sink back down, '
               'stretching, splitting and merging with each other as they go.',
    phrasings=('make it look like the inside of a lava lamp',
               'slow wax blobs drifting up and down and melting into each other',
               'a groovy retro lamp with goo rising and falling'),
    related=('morphing-blob', 'blob-to-icon-morph', 'liquid-morph', 'bloom', 'heat-haze', 'shape-morph-loader'),
    api=('videobuilder.techniques.particles.lava_lamp.draw_lava_lamp',
         'videobuilder.techniques.particles.lava_lamp.lava_blobs',
         'videobuilder.techniques.particles.lava_lamp.lamp_glass',
         'videobuilder.techniques.transitions.liquid_morph.metaballs'),
    demo=lambda: demo.film(draw),
)
