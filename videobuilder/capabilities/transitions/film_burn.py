"""Film burn: hot orange and yellow light blooms in from the frame's edge as
if the stock were scorching, swells until the picture blows out to near
white, and the next scene emerges as the glow cools away."""
import math
import random

import cairo

from .. import _demo as demo
from ..schema import Capability

# Burn colours from the core outwards: near-white, yellow, orange, deep red.
BURN = ((1.0, 0.97, 0.86), (1.0, 0.80, 0.30), (1.0, 0.45, 0.08), (0.75, 0.10, 0.02))


def _blobs(seed, count):
    """Fixed per-seed blob layout: (start x, start y, drift x, drift y, size, phase), in frame fractions."""
    rnd = random.Random(seed)
    out = []
    for i in range(count):
        out.append((rnd.uniform(0.75, 1.05), rnd.uniform(-0.1, 1.1), -rnd.uniform(0.35, 0.8),
                    rnd.uniform(-0.15, 0.15), rnd.uniform(0.35, 0.7), rnd.uniform(0, 2 * math.pi)))
    return out


def film_burn(cv, a, b, p, seed=7, blobs=6, colors=BURN):
    """Draw the burn at progress `p` (0 -> 1): `a(cv)` under glowing blobs that
    flare in from the right edge and screen-blend brighter until the frame is
    blown out at the midpoint, where the picture cuts to `b(cv)`, which then
    shows through as the glow sweeps on and fades. `seed` fixes the blob
    layout; `colors` is four RGB tuples (0..1) from core to rim.

    In a film, call it while two shots are live in an overlap, e.g.
    `film_burn(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    (a if p < 0.5 else b)(cv)
    heat = math.sin(math.pi * p) ** 1.5      # 0 at both ends, 1 at the cut
    w, h = cv.width, cv.height
    c = cv.ctx
    c.save()
    layout = [(x0 + dx * p, y0 + dy * p, size, ph) for x0, y0, dx, dy, size, ph in _blobs(seed, blobs)]
    # First the scorch: multiply a deep orange cast in, so even a light scene turns fiery, not just pale.
    c.set_operator(cairo.OPERATOR_MULTIPLY)
    rr, rg, rb = colors[2]
    for x, y, size, ph in layout:
        r = max(1.0, size * w * (0.5 + 1.4 * heat))
        g = cairo.RadialGradient(x * w, y * h, 0, x * w, y * h, r)
        g.add_color_stop_rgba(0.0, rr, rg, rb, 0.9 * heat)
        g.add_color_stop_rgba(1.0, rr, rg, rb, 0.0)
        c.set_source(g)
        c.paint()
    # Then the glow: screen-blend the hot blobs over it, white-yellow cores inside orange and red rims.
    c.set_operator(cairo.OPERATOR_SCREEN)
    for x, y, size, ph in layout:
        flicker = 0.85 + 0.15 * math.sin(ph + p * 40)
        cx, cy = x * w, y * h
        r = max(1.0, size * w * (0.2 + 0.9 * heat) * flicker)
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
        k = heat * flicker
        for stop, (cr, cg, cb), al in zip((0.0, 0.25, 0.55, 1.0), colors, (1.0, 0.95, 0.75, 0.0)):
            g.add_color_stop_rgba(stop, cr, cg, cb, al * k)
        c.set_source(g)
        c.paint()
    # The blow-out: a brief warm wash that hides the cut.
    wr, wg, wb = colors[1]
    c.set_source_rgba(wr, wg, wb, 0.9 * heat ** 8)
    c.paint()
    c.restore()


CAPABILITY = Capability(
    id='film-burn',
    name='Film burn',
    family='transitions',
    group='Light and Flash',
    aliases=('film burn transition', 'burn-through', 'light burn', 'celluloid burn'),
    definition='Fiery orange and yellow light floods in from the edge of the frame as if the film '
               'were scorching, blows the picture out to near white, and cools away to reveal the next scene.',
    phrasings=('make it look like the film is burning between the two shots',
               'a hot orange flare that whites out the screen and lands on the next clip',
               'that vintage reel-burning light effect as a transition'),
    related=('pixelate-transition', 'fire-overlay', 'smoke-dissolve', 'ken-burns-effect', 'screen-blend',
             'glitch-transition'),
    api=('videobuilder.capabilities.transitions.film_burn.film_burn',),
    demo=lambda: demo.two_scenes(film_burn),
)
