"""Indeterminate Dash Morph: a checkbox's flat "partly selected" dash bends
into a tick. Both marks are the same three-point stroke, so the morph is
just its points moving: the middle point drops to become the tick's elbow
while the ends slide to the tick's tips."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ... import paths

# The two marks in unit-box coordinates (0..1 across the checkbox), left tip, middle, right tip.
DASH = ((0.27, 0.5), (0.5, 0.5), (0.73, 0.5))
CHECK = ((0.26, 0.52), (0.43, 0.69), (0.75, 0.33))


def dash_to_check(x, y, size, p):
    """The mark for a checkbox of side `size` with top-left (x, y), at progress
    `p`: 0 is the dash, 1 the tick, as three film-px points. `p` is not
    clamped, so an overshooting ease (`vb.ease_out_back`) bends it a touch
    past the tick before it settles; run `p` from 1 to 0 to go back."""
    return [(x + size * (dx + (cx - dx) * p), y + size * (dy + (cy - dy) * p))
            for (dx, dy), (cx, cy) in zip(DASH, CHECK)]


def draw_dash_check(cv, x, y, size, p, box=demo.ACCENT, mark=demo.INK, width=None, radius=None):
    """Draw a filled checkbox of side `size` at top-left (x, y) with its mark
    at progress `p` (see `dash_to_check`), stroked with round caps and joins.
    `width` defaults to a ninth of `size`, `radius` to a fifth."""
    cv.rect(x, y, size, size, box, radius=size / 5 if radius is None else radius)
    paths.draw(cv, dash_to_check(x, y, size, p), mark, width=width or size / 9)


SETTLE = vb.bezier(0.5, 0, 0.3, 1.35)  # eases in, then bends a touch past the tick


def draw(n, cv):
    size = 220
    p = SETTLE(demo.phase(n, 0.8, 1.8))
    pop = 1 + 0.08 * math.sin(math.pi * demo.phase(n, 0.8, 1.4))  # a small press as it changes
    s = size * pop
    x, y = (demo.W - s) / 2, (demo.H - s) / 2
    cv.shadow(x, y, s, s, radius=s / 5, dy=10, blur=28, color=(0, 0, 0, 0.45))
    draw_dash_check(cv, x, y, s, p)
    cv.mark('checkbox', x, y, s, s)


CAPABILITY = Capability(
    id='indeterminate-dash-morph',
    name='Indeterminate dash morph',
    family='ui',
    group='Toggles & controls',
    aliases=('partial checkbox morph', 'minus to check', 'mixed-state checkbox'),
    definition='A checkbox showing a flat dash for a partial selection bends that same stroke into a tick '
               'when it becomes fully checked.',
    phrasings=('the minus in the checkbox turns into a checkmark',
               'a half-selected checkbox animates to checked, the line bending into a tick',
               'morph the indeterminate dash into a check'),
    related=('loading-to-success-morph', 'circle-check-draw', 'icon-state-morph', 'text-to-shape-morph',
             'bouncing-dots', 'letter-morph'),
    api=('videobuilder.capabilities.ui.indeterminate_dash_morph.draw_dash_check',
         'videobuilder.capabilities.ui.indeterminate_dash_morph.dash_to_check'),
    demo=lambda: demo.film(draw),
)
