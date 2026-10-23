"""Lens dirt overlay: smudges, specks and smears sitting on the lens, invisible
over a flat picture but lighting up as soft blotches whenever a bright light
comes near them in frame. The dirt is fixed to the lens, so it stays put while
the light moves; only how strongly each blotch glows changes."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def dirt_spots(w, h, count=70, seed=0, sizes=(6, 90)):
    """The dirt on a `w` x `h` lens, fixed by `seed`, as dicts: `x`, `y`,
    radius `r`, `strength` (0 -> 1, how much light it catches), `stretch`
    (1 for a round blotch, more for a wiped smear) and `angle` of the smear.
    Most spots are small specks; a few are big soft smudges."""
    rnd = random.Random(seed)
    lo, hi = sizes
    out = []
    for _ in range(count):
        big = rnd.random() < 0.3
        r = lo + (hi - lo) * (rnd.uniform(0.35, 1.0) if big else rnd.random() ** 3 * 0.25)
        smear = big and rnd.random() < 0.4
        out.append(dict(x=rnd.uniform(0, w), y=rnd.uniform(0, h), r=r,
                        strength=rnd.uniform(0.35, 1.0) * (0.6 if big else 1.0),
                        stretch=rnd.uniform(1.8, 3.2) if smear else rnd.uniform(1.0, 1.25),
                        angle=rnd.uniform(0, math.pi)))
    return out


def dirt_glow(px, py, light, reach):
    """How lit the dirt at (px, py) is by a light at `light` (x, y): 1 at the
    light, falling smoothly to near 0 by `reach` px away."""
    d = math.hypot(px - light[0], py - light[1])
    return math.exp(-(d / (reach * 0.5)) ** 2)


def lens_dirt(cv, light, intensity=1.0, seed=0, count=70, reach=700, color='#ffe9c4', base=0.0,
              sizes=(6, 90)):
    """Draw lens dirt over everything already on `cv`, lit by a light source at
    `light` (x, y) in frame px, which may lie outside the frame. `intensity`
    (0 -> 1) is how bright that light is: fade it with the light, and the dirt
    vanishes with it. Each spot glows by its `dirt_glow` within `reach` px of
    the light, plus `base` everywhere (a faint always-there grime). Spots
    blend as light (add), so they only ever brighten the picture. The same
    `seed` gives the same dirt every frame, as real dirt would."""
    if intensity <= 0:
        return
    c = cv.ctx
    cr, cg, cb, _ = vb.rgba(color)
    c.save()
    c.set_operator(cairo.OPERATOR_ADD)
    for s in dirt_spots(cv.width, cv.height, count, seed, sizes):
        a = intensity * s['strength'] * (base + (1 - base) * dirt_glow(s['x'], s['y'], light, reach))
        if a < 0.004:
            continue
        a *= 0.32 if s['r'] > 30 else 0.6  # big smudges are a faint veil, specks a sharper glint
        c.save()
        c.translate(s['x'], s['y'])
        c.rotate(s['angle'])
        c.scale(s['stretch'], 1)
        g = cairo.RadialGradient(0, 0, 0, 0, 0, s['r'])
        g.add_color_stop_rgba(0, cr, cg, cb, a)
        g.add_color_stop_rgba(0.55, cr, cg, cb, a * 0.75)  # a flat-ish core, like a smudge out of focus
        g.add_color_stop_rgba(0.8, cr, cg, cb, a * 0.3)
        g.add_color_stop_rgba(1, cr, cg, cb, 0)
        c.arc(0, 0, s['r'], 0, 2 * math.pi)
        c.set_source(g)
        c.fill()
        c.restore()
    c.restore()


# ---- demo: a sun crossing a still dusk landscape ----

def _hill(cv, base, amp, freq, phase, color):
    c = cv.ctx
    c.move_to(0, demo.H)
    for i in range(0, 65):
        x = demo.W * i / 64
        c.line_to(x, base - amp * math.sin(freq * x / demo.W * math.pi + phase))
    c.line_to(demo.W, demo.H)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color))
    c.fill()


def _sun(cv, x, y, r=34):
    c = cv.ctx
    g = cairo.RadialGradient(x, y, 0, x, y, r * 9)
    for stop, a in ((0, 0.55), (0.12, 0.3), (0.4, 0.08), (1, 0)):
        g.add_color_stop_rgba(stop, *vb.rgba('#ffe2a8', a))
    c.arc(x, y, r * 9, 0, 2 * math.pi)
    c.set_source(g)
    c.fill()
    demo.dot(cv, x, y, r, color='#fffaf0')


def draw(n, cv):
    sky = cairo.LinearGradient(0, 0, 0, demo.H)
    sky.add_color_stop_rgba(0, *vb.rgba('#2a3157'))
    sky.add_color_stop_rgba(1, *vb.rgba('#8a90c4'))
    cv.ctx.rectangle(0, 0, demo.W, demo.H)
    cv.ctx.set_source(sky)
    cv.ctx.fill()
    p = demo.phase(n, 0.0, demo.SECONDS)
    sun = (demo.W * (-0.08 + 1.16 * p), demo.H * (0.42 - 0.22 * math.sin(math.pi * p)))
    _sun(cv, *sun)
    _hill(cv, demo.H * 0.66, 70, 1.3, 0.4, '#5d6596')
    _hill(cv, demo.H * 0.76, 55, 2.1, 2.0, '#3e4470')
    _hill(cv, demo.H * 0.88, 40, 1.7, 4.1, '#262a45')
    # a tight reach and no base glow keep the dirt hidden away from the sun; few, big spots read as
    # grime on the glass rather than snow, and a light brighter than 1 makes the lit ones glow clearly
    lens_dirt(cv, sun, intensity=1.8 * math.sin(math.pi * p) ** 0.5, seed=33, count=30, reach=290,
              sizes=(36, 140))
    cv.mark('dirt', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='lens-dirt-overlay',
    name='Lens dirt overlay',
    family='vfx',
    group='Lens effects',
    aliases=('lens smudge', 'dust on lens', 'lens grime', 'dirty lens'),
    definition='Specks and smudges stuck to the camera lens stay hidden until a bright light comes near, '
               'then glow up as soft blurry patches that fade again as the light moves away.',
    phrasings=('make it look like the lens is a bit dirty when the sun hits it',
               'add smudges on the glass that light up near the bright light',
               'give the shot that grimy lens glow when it points at the sun'),
    related=('dust-and-scratches', 'lens-flare', 'heat-haze', 'dust-motes', 'smoke-overlay', 'light-leak'),
    api=('videobuilder.capabilities.vfx.lens_dirt_overlay.lens_dirt',
         'videobuilder.capabilities.vfx.lens_dirt_overlay.dirt_spots',
         'videobuilder.capabilities.vfx.lens_dirt_overlay.dirt_glow'),
    demo=lambda: demo.film(draw),
)
