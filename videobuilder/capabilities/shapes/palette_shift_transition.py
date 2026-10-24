"""Palette Shift Transition: a graphic keeps its shapes and layout while every
colour in it moves, together, from one palette to another -- the scene change
is carried by colour alone."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...canvas import rgba


def palette_at(a, b, p, ease=vb.ease_in_out_quart, stagger=0.0):
    """The palette part-way from `a` to `b` at progress `p` (0 -> 1).

    `a` and `b` map the same role names ('bg', 'panel', 'accent', ...) to
    colours (hex strings or (r, g, b) tuples); the result maps each role to
    an (r, g, b) tuple any canvas call takes. `ease` shapes the move. With
    `stagger` > 0 the roles shift one after another in `a`'s order, each
    starting `stagger` of the way later than the first; 0 moves them as one.

    In a film, draw the graphic with `pal = palette_at(day, night, p)` and
    `cv.rect(..., pal['panel'])` instead of fixed colours."""
    if set(a) != set(b):
        raise ValueError(f'palettes need the same roles: {sorted(set(a) ^ set(b))} differ')
    roles = list(a)
    span = 1 - stagger
    out = {}
    for i, role in enumerate(roles):
        start = stagger * i / max(1, len(roles) - 1)
        t = ease(vb.clamp01((p - start) / span)) if span > 0 else float(p >= start)
        ca, cb = rgba(a[role]), rgba(b[role])
        out[role] = tuple(round(255 * (ca[k] + (cb[k] - ca[k]) * t)) for k in range(3))
    return out


COOL = {'bg': '#14151a', 'panel': '#30323a', 'shape': '#7c86f2', 'light': '#e3e5e8', 'shadow': '#0a0b0e'}
WARM = {'bg': '#2b1a0b', 'panel': '#f0b31c', 'shape': '#1a1c2a', 'light': '#4a3a22', 'shadow': '#3a2306'}


def _composition(cv, pal):
    cv.fill(pal['bg'])
    k = 0.6  # the layout below is drawn on a 640 px panel, scaled to fit the frame
    cx, cy, w, h = demo.W / 2, demo.H / 2 - 30, 640 * k, 560 * k
    x, y = cx - w / 2, cy - h / 2
    cv.shadow(x, y, w, h, radius=26 * k, dy=14 * k, blur=40 * k, color=pal['shadow'] + (0.6,))
    cv.rect(x, y, w, h, pal['panel'], radius=26 * k)
    # top row: a disc with a crescent, a thin bar and a tall block
    demo.dot(cv, x + 170 * k, y + 170 * k, r=100 * k, color=pal['shape'])
    cv.arc(x + 170 * k, y + 170 * k, 62 * k, -math.pi / 2, math.pi / 2, pal['light'], width=26 * k)
    cv.rect(x + 330 * k, y + 70 * k, 36 * k, 200 * k, pal['light'])
    cv.rect(x + 400 * k, y + 70 * k, 150 * k, 200 * k, pal['shape'])
    # bottom row: a slab and a triangle
    cv.rect(x + 70 * k, y + 340 * k, 190 * k, 130 * k, pal['light'])
    c = cv.ctx
    c.new_path()
    c.move_to(x + 330 * k, y + 470 * k)
    c.line_to(x + 440 * k, y + 340 * k)
    c.line_to(x + 550 * k, y + 470 * k)
    c.close_path()
    c.set_source_rgba(*rgba(pal['shape']))
    c.fill()
    # the live palette as chips under the panel
    roles = ('bg', 'panel', 'shape', 'light')
    for i, role in enumerate(roles):
        sx = cx - (len(roles) * 56 - 14) / 2 + i * 56
        cv.rect(sx, y + h + 26, 42, 24, pal[role], radius=6)
        cv.outline(sx, y + h + 26, 42, 24, demo.MUTED, width=1.5, radius=6, alpha=0.5)


def draw(n, cv):
    _composition(cv, palette_at(COOL, WARM, demo.phase(n, 0.8, 2.2)))


CAPABILITY = Capability(
    id='palette-shift-transition',
    name='Palette shift transition',
    family='shapes',
    group='Gradients & color',
    aliases=('color swap transition', 'theme shift', 'palette crossfade', 'dark mode fade',
             'light/dark mode transition'),
    definition='Every colour in a graphic slides over to a new colour scheme in one timed move, '
               'while the shapes themselves stay exactly where they are.',
    phrasings=('recolour the whole layout from the cool scheme to the warm one',
               'keep the design but swap its colours over smoothly to mark the next section',
               'shift everything from the dark theme to the yellow theme in one go'),
    related=('theme-swap-crossfade', 'cross-processing', 'view-transition', 'gradient-shift-button',
             'scroll-linked-background-shift', 'shared-element-transition'),
    api=('videobuilder.capabilities.shapes.palette_shift_transition.palette_at',),
    demo=lambda: demo.film(draw),
)
