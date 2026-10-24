"""Bokeh highlights: small bright lights, thrown out of focus, swell into
soft translucent discs shaped like the lens aperture, glowing brighter where
they overlap."""
import math
import random

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability

GOLD = '#f2b636'


def _aperture(ctx, x, y, r, blades, rotation):
    """The aperture outline as the current path: a circle, or a regular
    polygon with `blades` sides (3 or more)."""
    ctx.new_path()
    if blades < 3:
        ctx.arc(x, y, r, 0, math.tau)
        return
    for k in range(blades):
        a = rotation + k * math.tau / blades
        ctx.line_to(x + r * math.cos(a), y + r * math.sin(a))
    ctx.close_path()


def bokeh_disc(cv, x, y, r, color, alpha=1.0, blades=0, rotation=0.0, rim=0.5):
    """One out-of-focus highlight centred at (x, y): an aperture-shaped disc of
    radius `r`, a flat translucent fill with a brighter rim (`rim` is the rim's
    extra strength, 0 for none), added onto what is below so overlaps glow.
    `blades` 0 is a round aperture; 5, 6 or 8 give the polygon of a bladed lens,
    turned by `rotation` radians."""
    ctx = cv.ctx
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_ADD)
    _aperture(ctx, x, y, r, blades, rotation)
    ctx.set_source_rgba(*rgba(color, alpha * 0.45))
    ctx.fill()
    if rim > 0 and r > 3:
        w = max(1.0, r * 0.07)
        _aperture(ctx, x, y, r - w / 2, blades, rotation)
        ctx.set_line_width(w)
        ctx.set_source_rgba(*rgba(color, alpha * 0.45 * rim))
        ctx.stroke()
    ctx.restore()


def bokeh_highlights(cv, lights, defocus, max_radius=110, blades=0, rotation=0.0, rim=0.5):
    """Draw point `lights` thrown out of focus by `defocus` (0 sharp -> 1 fully soft).

    Each light is `(x, y, size, color, depth)`: `size` is its radius when in
    focus, `depth` (0 -> 1) how far it sits from the focal plane, which scales
    its circle of confusion up to `max_radius` px. As a light spreads its glow
    thins (a big disc is fainter than a small one), and a sharp light keeps a
    hot white core that fades as it defocuses. `blades`, `rotation` and `rim`
    pass to `bokeh_disc`. Animate `defocus` for a focus pull, e.g.
    `bokeh_highlights(cv, lights, vb.ease_in_out_quart(p))`."""
    d = vb.clamp01(defocus)
    for x, y, size, color, depth in lights:
        r = size + d * depth * max_radius
        alpha = min(1.0, 1.6 * (size / r) ** 0.5)
        bokeh_disc(cv, x, y, r, color, alpha=alpha, blades=blades, rotation=rotation, rim=rim * d)
        core = (1 - d) ** 2
        if core > 0.01:
            cv.sector(x, y, size * 0.55, 0, math.tau, demo.INK, alpha=core)


def _lights():
    """A seeded field of small lights across the frame, like a night street."""
    rnd = random.Random('bokeh-highlights')
    out = []
    for i in range(60):
        color = (GOLD, GOLD, demo.ACCENT, demo.TEAL, demo.INK)[i % 5]
        out.append((rnd.uniform(-40, demo.W + 40), rnd.uniform(-40, demo.H + 40), rnd.uniform(5, 9),
                    color, rnd.uniform(0.1, 1.0) ** 1.4, rnd.uniform(0, math.tau)))
    return out


LIGHTS = _lights()


def draw(n, cv):
    t = n / demo.FPS
    d = vb.ease_in_out_quart(demo.phase(n, 0.5, 1.9))
    lights = [(x + 6 * math.sin(t * 0.8 + ph), y - 10 * t * depth, s, c, depth)
              for x, y, s, c, depth, ph in LIGHTS]
    bokeh_highlights(cv, lights, d, max_radius=80)
    cv.mark('lights', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='bokeh-highlights',
    name='Bokeh highlights',
    family='camera',
    group='Depth',
    aliases=('bokeh', 'out-of-focus highlights', 'lens blur', 'circle of confusion blur',
             'bokeh lights', 'bokeh field'),
    definition='Tiny points of light melt out of focus into soft, see-through discs in the shape of the '
               'lens opening, the farther from focus the bigger and fainter each one grows.',
    phrasings=('blur the background lights into those soft glowing circles',
               'make the city lights go dreamy and out of focus like a fast lens',
               'turn the sparkles into big blurry orbs'),
    related=('bokeh-particles', 'focus-blur-out', 'gooey-filter', 'blur-dissolve', 'character-blur-in',
             'gaussian-blur'),
    api=('videobuilder.capabilities.camera.bokeh_highlights.bokeh_highlights',
         'videobuilder.capabilities.camera.bokeh_highlights.bokeh_disc'),
    demo=lambda: demo.film(draw),
)
