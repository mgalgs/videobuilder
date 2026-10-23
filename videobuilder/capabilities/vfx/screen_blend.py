"""Screen blend: a layer is laid over the picture with the screen operator --
each channel is 1 - (1 - top)(1 - bottom) -- so its black drops out, its
lights brighten whatever is under them, and nothing ever gets darker. The
usual way to put flares, glows, light leaks and sparks shot on black over
footage."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def screen_blend(cv, draw, amount=1.0):
    """Draw `draw(cv)` into its own group and composite it over what `cv`
    already holds with cairo's SCREEN operator, at strength `amount` (0 -> 1).
    Black in the layer leaves the picture untouched, white lifts it to white,
    and everything between lightens it.

    In a film, draw the shot first, then e.g.
    `screen_blend(cv, lambda c: flare(c, f), amount=0.8)` for the light on black."""
    if amount <= 0:
        return
    c = cv.ctx
    c.save()
    c.push_group()
    draw(cv)
    c.pop_group_to_source()
    c.set_operator(cairo.OPERATOR_SCREEN)
    c.paint_with_alpha(min(1.0, amount))
    c.restore()


# ---- demo ----

PANEL = (220, 150, demo.W - 440, demo.H - 300)   # where the overlay layer sits
ORBS = ((0.24, 0.42, 120, '#ff7a3d'), (0.52, 0.52, 135, '#3dd6ff'), (0.78, 0.38, 115, '#ffd23d'))
FEATHER = 70                                       # px over which the glows fade to black at the panel's edges


def _glow(c, cx, cy, r, color):
    red, green, blue, _ = vb.rgba(color)
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    g.add_color_stop_rgba(0, 1, 1, 1, 1)
    g.add_color_stop_rgba(0.18, red, green, blue, 1)
    g.add_color_stop_rgba(1, red, green, blue, 0)
    c.set_source(g)
    c.arc(cx, cy, r, 0, 2 * math.pi)
    c.fill()


def _feather(x0, y0, x1, y1):
    """A mask gradient along (x0, y0) -> (x1, y1) that is clear at both ends and
    solid across the middle, eased so the fade has no visible start."""
    g = cairo.LinearGradient(x0, y0, x1, y1)
    f = FEATHER / math.hypot(x1 - x0, y1 - y0)
    for k in range(9):
        u = k / 8
        a = u * u * (3 - 2 * u)
        g.add_color_stop_rgba(f * u, 0, 0, 0, a)
        g.add_color_stop_rgba(1 - f * u, 0, 0, 0, a)
    return g


def _light_layer(cv, t):
    """The layer being blended: coloured light orbs and a word on solid black.
    The glows are feathered to black well inside the panel's edges, so once
    screened nothing of the panel's outline is left."""
    x, y, w, h = PANEL
    cv.rect(x, y, w, h, '#000000')
    c = cv.ctx
    with cv.clip(x, y, w, h):
        c.push_group()
        for i, (fx, fy, r, color) in enumerate(ORBS):
            dx = 40 * math.sin(t * 1.3 + i * 2.1)
            dy = 25 * math.cos(t * 1.1 + i * 1.7)
            _glow(c, x + w * fx + dx, y + h * fy + dy, r, color)
        glows = c.pop_group()
        c.push_group()                         # fade the sides ...
        c.set_source(glows)
        c.mask(_feather(x, 0, x + w, 0))
        sides = c.pop_group()
        c.set_source(sides)                    # ... then the top and bottom
        c.mask(_feather(0, y, 0, y + h))
        demo.word(cv, 'LIGHT', x + w / 2, y + h * 0.82, size=88, color='#cfcfcf')


def _draw(n, cv):
    t = n / demo.FPS
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    split = PANEL[0] + PANEL[2] * vb.ease_in_out_quart(demo.phase(n, 0.6, 1.9))
    # Left of the divider: the layer blended "screen"; right of it: the same layer laid on normally.
    with cv.clip(0, 0, split, demo.H):
        screen_blend(cv, lambda c: _light_layer(c, t))
    with cv.clip(split, 0, demo.W - split, demo.H):
        _light_layer(cv, t)
    if PANEL[0] < split < PANEL[0] + PANEL[2]:
        cv.line(split, PANEL[1] - 30, split, PANEL[1] + PANEL[3] + 30, demo.INK, width=3)
    lab = demo.font(30, 800)
    if split > PANEL[0] + 40:
        cv.rect(PANEL[0], PANEL[1] - 64, 150, 48, demo.BG, radius=10, alpha=0.8)
        vb.text.draw(cv, ['Screen'], lab, PANEL[0] + 18, PANEL[1] - 58, demo.TEAL)
    if split < PANEL[0] + PANEL[2] - 40:
        rx = PANEL[0] + PANEL[2] - 150
        cv.rect(rx, PANEL[1] - 64, 150, 48, demo.BG, radius=10, alpha=0.8)
        vb.text.draw(cv, ['Normal'], lab, rx + 18, PANEL[1] - 58, demo.MUTED)


CAPABILITY = Capability(
    id='screen-blend',
    name='Screen blend',
    family='vfx',
    group='Blend & composite',
    aliases=('screen mode', 'screen blending mode', 'screen composite'),
    definition='A layer is combined with the picture beneath so that its black vanishes and its bright parts '
               'lighten what shows through, as if two projectors shone on the same wall.',
    phrasings=('lay this flare over the shot so the black background disappears',
               'put the glow on top so it only brightens the footage',
               'overlay the light leak without the dark parts showing'),
    related=('additive-dissolve', 'flash-cut', 'film-dissolve', 'cross-dissolve', 'theme-swap-crossfade',
             'gooch-shading'),
    api=('videobuilder.capabilities.vfx.screen_blend.screen_blend',),
    demo=lambda: demo.film(_draw),
)
