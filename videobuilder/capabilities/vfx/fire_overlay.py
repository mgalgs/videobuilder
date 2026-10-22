"""Fire overlay: a band of flickering flames burns along one edge of the
frame, laid over the picture, with their warm light spilling onto it.

`flame_profile` is stateless: the flame tops at any moment are worked out
from the time alone, so any frame renders on its own and the fire loops on
forever. `draw_fire_overlay` draws the stacked flame layers and the glow."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..particles.embers import draw_embers, embers
from ..schema import Capability

# back to front: deep red-orange, orange, yellow, pale core -- (rgb top, rgb base, height share, alpha)
LAYERS = (((0.75, 0.12, 0.02), (0.95, 0.30, 0.04), 1.00, 0.85),
          ((1.00, 0.42, 0.05), (1.00, 0.62, 0.10), 0.82, 0.92),
          ((1.00, 0.72, 0.15), (1.00, 0.88, 0.40), 0.62, 0.95),
          ((1.00, 0.93, 0.62), (1.00, 0.99, 0.88), 0.36, 1.00))


def flame_profile(t, length, height, tongues=10, seed=0, samples=160):
    """The flame tops along an edge `length` px long at time `t` seconds, as
    `samples + 1` (along, up) pairs: `up` is how far the flames reach out
    from the edge, at most about `height`. Pointed tongues, about `tongues`
    of them, sway sideways and leap and drop at their own rates over a low
    rolling bed of fire. The same `seed` gives the same fire every time."""
    r = random.Random(seed)
    spacing = length / tongues
    tips = []
    for i in range(tongues + 2):
        base = (i - 0.5 + r.uniform(-0.3, 0.3)) * spacing
        sway = r.uniform(0.15, 0.35) * spacing
        f1, f2 = r.uniform(2.0, 4.5), r.uniform(5.0, 9.0)
        p1, p2 = r.uniform(0, 2 * math.pi), r.uniform(0, 2 * math.pi)
        c = base + sway * math.sin(f1 * 0.6 * t + p1)
        leap = 0.72 + 0.18 * math.sin(f1 * t + p2) + 0.1 * math.sin(f2 * t + p1)
        tips.append((c, r.uniform(0.7, 1.1) * spacing, height * r.uniform(0.65, 1.0) * leap))
    out = []
    for k in range(samples + 1):
        x = length * k / samples
        bed = height * (0.22 + 0.06 * math.sin(x / length * 13 + t * 3.1) + 0.04 * math.sin(x / length * 31 - t * 5.3))
        up = bed
        for c, w, h in tips:
            d = abs(x - c) / w
            if d < 1:
                up = max(up, bed + (h - bed) * (1 - d) ** 1.6)
        out.append((x, up))
    return out


def _edge_transform(c, edge, w, h):
    """Map local (along, up-from-edge) coordinates onto the frame for `edge`."""
    if edge == 'bottom':
        c.translate(0, h)
        c.scale(1, -1)
    elif edge == 'top':
        pass
    elif edge == 'left':
        c.rotate(math.pi / 2)
        c.scale(1, -1)
    elif edge == 'right':
        c.translate(w, 0)
        c.rotate(math.pi / 2)
    else:
        raise ValueError(f'edge must be bottom, top, left or right, not {edge!r}')


def draw_fire_overlay(cv, t, edge='bottom', height=None, tongues=10, glow=1.0, seed=0, alpha=1.0):
    """Draw a fire burning along `edge` ('bottom', 'top', 'left', 'right') of
    the canvas at time `t` seconds, over whatever is already there. Flames
    reach about `height` px out from the edge (default: a third of the frame
    across that axis). `glow` scales the warm light thrown onto the picture,
    which flickers with the fire; `alpha` fades the whole effect, so ramping
    it ignites or dies the fire down. Returns the Box the flames occupy."""
    W, H = cv.width, cv.height
    length = W if edge in ('bottom', 'top') else H
    depth = H if edge in ('bottom', 'top') else W
    height = depth / 3 if height is None else height
    if alpha <= 0:
        return vb.Box(0, 0, 0, 0)
    c = cv.ctx
    c.save()
    _edge_transform(c, edge, W, H)
    # the light the fire throws: a flickering additive wash fading out from the edge
    if glow > 0:
        flick = 0.85 + 0.1 * math.sin(t * 11.0) + 0.05 * math.sin(t * 23.0 + 1.3)
        reach = height * 2.6
        g = cairo.LinearGradient(0, 0, 0, reach)
        g.add_color_stop_rgba(0, 1.0, 0.45, 0.08, 0.55 * glow * flick * alpha)
        g.add_color_stop_rgba(0.4, 1.0, 0.35, 0.05, 0.2 * glow * flick * alpha)
        g.add_color_stop_rgba(1, 1.0, 0.3, 0.0, 0)
        c.save()
        c.set_operator(cairo.OPERATOR_ADD)
        c.rectangle(0, 0, length, reach)
        c.set_source(g)
        c.fill()
        c.restore()
    for i, (top, base, share, a) in enumerate(LAYERS):
        prof = flame_profile(t * (1 + 0.15 * i), length, height * share, tongues + 2 * i, seed=seed * 31 + i)
        c.new_path()
        c.move_to(0, -2)
        for x, up in prof:
            c.line_to(x, up)
        c.line_to(length, -2)
        c.close_path()
        g = cairo.LinearGradient(0, 0, 0, height * share)
        g.add_color_stop_rgba(0, *base, a * alpha)
        g.add_color_stop_rgba(1, *top, a * alpha)
        c.set_source(g)
        c.fill()
    c.restore()
    if edge == 'bottom':
        return vb.Box(0, H - height, W, height)
    if edge == 'top':
        return vb.Box(0, 0, W, height)
    return vb.Box(0, 0, height, H) if edge == 'left' else vb.Box(W - height, 0, height, H)


def _scene(cv):
    """A dim, cool-toned photo for the fire to burn over."""
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    cv.fill('#0b1030', alpha=0.45)


def draw(n, cv):
    t = n / demo.FPS
    _scene(cv)
    ignite = vb.ease_out_quint(demo.phase(n, 0.0, 0.6))  # the fire flares up, then burns steadily
    box = draw_fire_overlay(cv, t + 2.0, height=demo.H * 0.5 * (0.4 + 0.6 * ignite), seed=5, alpha=ignite)
    draw_embers(cv, embers(t + 3.0, 0, demo.W, demo.H - 40, count=40, life=1.8, rise=260, sway=40,
                           size=3.5, seed=5), alpha=ignite)
    cv.mark('fire', *box)


CAPABILITY = Capability(
    id='fire-overlay',
    name='Fire overlay',
    family='vfx',
    group='Particle & weather overlays',
    aliases=('flame overlay', 'fire plate', 'flame layer'),
    definition='A strip of licking flames burns along one edge of the shot, layered on top of the picture, '
               'with their flickering orange light washing over everything nearby.',
    phrasings=('put flames burning along the bottom of the video',
               'make it look like the scene is on fire from below',
               'add a fire layer over the footage with a warm glow'),
    related=('doom-style-fire', 'camcorder-timecode-overlay', 'film-burn', 'heat-haze', 'lens-dirt-overlay',
             'fireflies'),
    api=('videobuilder.capabilities.vfx.fire_overlay.draw_fire_overlay',
         'videobuilder.capabilities.vfx.fire_overlay.flame_profile'),
    demo=lambda: demo.film(draw),
)
