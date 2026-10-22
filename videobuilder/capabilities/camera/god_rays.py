"""God rays: a bright light sits behind something solid, and shafts of light
stream out through every gap around it, as if through haze -- the screen-space
trick: draw the light's glow with the occluder punched out of it in black,
smear that outward from the light, and add the smear over the picture."""
import math

import cairo

from .. import _demo as demo
from ..schema import Technique
from ...canvas import Canvas, rgba


def god_rays(cv, x, y, occluder, color='#ffd58a', glow=90, length=4.0, strength=1.5, passes=3,
             quality=0.25):
    """Add light shafts from a light at (x, y) streaming past `occluder(c)`.

    `occluder` draws the blocking shapes onto the canvas it is given, in any
    colour (only their coverage is used); everything it covers stops the
    light. `glow` is the radius of the light's halo, `length` how far the
    shafts reach (they stretch the halo out to `1 + length` times, fading as
    they go), and `strength` scales the light added (0 adds nothing; above 1
    overexposes).
    The smear runs in `passes` passes of 8 copies each, and at `quality`
    times the frame's resolution, painted back smoothly, which keeps the
    shafts cheap and soft.

    The shafts are light in the air in front of everything, so draw the
    whole scene first -- the light, then the occluder over it -- and call
    this last."""
    if strength <= 0:
        return
    s = cv.scale * quality
    sub = Canvas(cv.width, cv.height, scale=s)
    c = sub.ctx
    r, g, b, _ = rgba(color)
    halo = cairo.RadialGradient(x, y, 0, x, y, glow)
    halo.add_color_stop_rgba(0, r, g, b, 1)
    halo.add_color_stop_rgba(0.3, r, g, b, 0.6)
    halo.add_color_stop_rgba(1, r, g, b, 0)
    c.set_source(halo)
    c.paint()
    c.push_group()
    occluder(sub)
    shape = c.pop_group()
    c.set_source_rgb(0, 0, 0)
    c.mask(shape)                            # the occluder blacks out the light behind it

    surf = sub.surface
    dx, dy = x * s, y * s
    taps = 8
    for j in range(passes):              # fine steps first, then coarser: taps ** passes samples per shaft
        step = math.log1p(length) / taps ** (passes - j)
        surf = _smear(surf, dx, dy, step, taps)

    m = cv.ctx
    m.save()
    m.identity_matrix()
    m.scale(1 / quality, 1 / quality)
    reach = glow * s * (1 + length)
    m.set_operator(cairo.OPERATOR_ADD)
    while strength > 0:                  # past 1, the light is added again: an exposure boost
        fade = cairo.RadialGradient(dx, dy, 0, dx, dy, reach)  # the shafts thin out as they travel
        fade.add_color_stop_rgba(0, 0, 0, 0, min(1.0, strength))
        fade.add_color_stop_rgba(0.4, 0, 0, 0, 0.4 * min(1.0, strength))
        fade.add_color_stop_rgba(1, 0, 0, 0, 0)
        m.set_source_surface(surf, 0, 0)
        m.get_source().set_filter(cairo.FILTER_BILINEAR)
        m.mask(fade)
        strength -= 1
    m.restore()


def _smear(src, dx, dy, step, taps):
    """`src` averaged with `taps` copies of itself scaled up about (dx, dy),
    each `exp(step)` times the last: one pass of the radial smear."""
    src.flush()
    out = cairo.ImageSurface(cairo.FORMAT_ARGB32, src.get_width(), src.get_height())
    o = cairo.Context(out)
    for i in range(taps):
        k = math.exp(step * i)
        o.save()
        o.translate(dx, dy)
        o.scale(k, k)
        o.translate(-dx, -dy)
        o.set_source_surface(src, 0, 0)
        o.get_source().set_filter(cairo.FILTER_BILINEAR)
        o.paint_with_alpha(1 / (i + 1))  # a running average: every copy weighs the same
        o.restore()
    out.flush()
    return out

WALL = '#1b1d24'
COLS, ROWS, PANE, BAR = 4, 3, 40, 20   # a paned window in a dark wall


def _wall(cv):
    """The wall: the whole frame except the window's panes, cut out even-odd."""
    c = cv.ctx
    w, h = COLS * PANE + (COLS - 1) * BAR, ROWS * PANE + (ROWS - 1) * BAR
    x0, y0 = demo.W / 2 - w / 2, demo.H * 0.38 - h / 2
    c.rectangle(0, 0, demo.W, demo.H)
    for i in range(COLS):
        for j in range(ROWS):
            c.rectangle(x0 + i * (PANE + BAR), y0 + j * (PANE + BAR), PANE, PANE)
    c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    c.set_source_rgba(*rgba(WALL))
    c.fill()
    c.set_fill_rule(cairo.FILL_RULE_WINDING)


def draw(n, cv):
    t = demo.phase(n, 0.0, demo.SECONDS)
    x = demo.W / 2 + 85 * math.sin((t - 0.5) * math.pi * 0.9)  # the light drifts behind the window
    y = demo.H * 0.38 - 25 + 35 * math.sin(t * math.pi)
    up = 1 - (1 - demo.phase(n, 0.1, 0.9)) ** 3           # the light comes up, then holds
    cv.fill('#2a3550')                                     # the sky beyond the window
    demo.dot(cv, x, y, r=26, color='#fff4d6')
    _wall(cv)
    god_rays(cv, x, y, _wall, glow=170, length=3.0, strength=1.6 * up, quality=0.5)


TECHNIQUE = Technique(
    id='god-rays',
    name='God rays',
    family='camera',
    group='Lighting & surface',
    aliases=('crepuscular rays', 'light shafts', 'volumetric light', 'volumetric light shafts', 'sunbeams'),
    definition='A bright light hidden behind a solid shape throws visible beams out through every gap '
               'around it, like sunlight cutting through dusty air.',
    phrasings=('make beams of light shine out from behind the title',
               'sunbeams streaming through the gaps',
               'light bursting out around the logo in rays'),
    related=('bokeh-particles', 'heat-haze', 'diffraction-spikes', 'raymarched-sdf-shapes', 'atmospheric-fog',
             'water-caustics'),
    api=('videobuilder.techniques.camera.god_rays.god_rays',),
    demo=lambda: demo.film(draw),
)
