"""Lens flare: a bright point of light sits in the frame with a soft halo and
a thin horizontal streak, and a chain of faint coloured ghost discs lines up
on the far side of the frame's centre, sliding the opposite way whenever the
light moves."""
import math

import cairo

from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability

# Each ghost: where it sits on the line from the light through the frame
# centre (0 = at the light, 1 = at the centre, 2 = mirrored across it), its
# radius as a fraction of the frame width, colour, and how strong it is.
GHOSTS = (
    (0.55, 0.012, '#9fb2ff', 0.55),
    (1.20, 0.020, '#9fb2ff', 0.50),
    (1.45, 0.032, '#c8d2ff', 0.45),
    (1.65, 0.011, '#ffd27a', 0.65),
    (1.85, 0.055, '#e8b84a', 0.60),
    (2.00, 0.040, '#8f9cff', 0.45),
)


def _radial(ctx, cx, cy, r, color, stops):
    """Paint a radial gradient of `color` with (offset, alpha) `stops`."""
    cr, cg, cb, _ = rgba(color)
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    for off, al in stops:
        g.add_color_stop_rgba(off, cr, cg, cb, al)
    ctx.set_source(g)
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.fill()


def lens_flare(cv, x, y, strength=1.0, color='#fff2c8', tint='#9aa8ff', ghosts=GHOSTS, streak=True,
               centre=None):
    """Paint a lens flare for a light at (x, y) over whatever `cv` holds, all
    screen-blended so it only brightens: a hot core and wide soft halo, a thin
    horizontal (anamorphic) streak in `tint` when `streak`, and `ghosts`
    strung along the line from the light through `centre` (the frame centre
    by default), so they swing to the opposite side as the light moves.
    `strength` (0 -> 1+) scales everything, for flaring up or fading out."""
    if strength <= 0:
        return
    w, h = cv.width, cv.height
    cx, cy = centre or (w / 2, h / 2)
    s = strength
    ctx = cv.ctx
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_SCREEN)
    # Halo: a wide cool glow, then a warm inner bloom, then the white-hot core.
    _radial(ctx, x, y, w * 0.16, tint, ((0, 0.35 * s), (0.4, 0.12 * s), (1, 0)))
    _radial(ctx, x, y, w * 0.045, color, ((0, 0.9 * s), (0.5, 0.35 * s), (1, 0)))
    _radial(ctx, x, y, w * 0.012, '#ffffff', ((0, min(1.0, s)), (0.6, 0.9 * s), (1, 0)))
    if streak:
        tr, tg, tb, _ = rgba(tint)
        for half, thick, al in ((w * 0.55, h * 0.006, 0.9), (w * 0.3, h * 0.02, 0.25)):
            g = cairo.LinearGradient(x - half, y, x + half, y)
            g.add_color_stop_rgba(0, tr, tg, tb, 0)
            g.add_color_stop_rgba(0.5, 1, 1, 1, al * s)
            g.add_color_stop_rgba(1, tr, tg, tb, 0)
            ctx.save()
            ctx.translate(x, y)
            ctx.scale(1, thick / half)
            ctx.arc(0, 0, half, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source(g)
            ctx.fill()
    # Ghosts: reflections of the light, mirrored through the centre.
    dx, dy = cx - x, cy - y
    for t, fr, gcol, al in ghosts:
        gx, gy, r = x + dx * t, y + dy * t, w * fr
        _radial(ctx, gx, gy, r, gcol, ((0, 0.10 * al * s), (0.75, 0.25 * al * s), (0.92, 0.7 * al * s), (1, 0)))
    ctx.restore()


def _draw(n, cv):
    """The light arcs across the top of a dark frame, flaring up on entry and
    dimming on exit, while its ghosts swing across the centre against it."""
    p = demo.phase(n, 0.0, demo.SECONDS)
    cv.fill('#0b0f16')
    # A faint frame for scale, so the ghosts' sweep reads against something still.
    cv.rect(110, 90, demo.W - 220, demo.H - 180, demo.LINE, radius=24, alpha=0.18)
    cv.rect(114, 94, demo.W - 228, demo.H - 188, '#0b0f16', radius=22)
    e = (1 - math.cos(math.pi * p)) / 2
    x = demo.W * (0.86 - 0.72 * e)
    y = demo.H * (0.42 - 0.16 * math.sin(math.pi * e))
    strength = min(1.0, 0.35 + 3 * p, 0.35 + 3 * (1 - p))
    lens_flare(cv, x, y, strength=strength)


CAPABILITY = Capability(
    id='lens-flare',
    name='Lens flare',
    family='camera',
    group='Lighting & surface',
    aliases=('anamorphic flare', 'lens ghosts', 'ghost flares', 'lens reflections', 'anamorphic streak',
             'horizontal streak flare'),
    definition='A bright light in the shot glows with a soft halo and a thin sideways streak, '
               'while a row of faint coloured circles mirrors it across the middle of the frame.',
    phrasings=('make it look like the sun is shining straight into the camera',
               'add that sci-fi blue streak with bubbles of light across the screen',
               'give the bright light a glare with little rings trailing off it'),
    related=('diffraction-spikes', 'lens-dirt-overlay', 'heat-haze', 'refraction-ripple', 'fireflies',
             'fresnel-edge-glow'),
    api=('videobuilder.capabilities.camera.lens_flare.lens_flare',),
    demo=lambda: demo.film(_draw),
)
