"""Touch Ripple: tapping a button sends a circle of ink out from the exact
point that was touched, filling the button up to its edges and fading away."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ripple_reach(x, y, w, h, tx, ty):
    """The radius a ripple from (tx, ty) needs to cover the box (x, y, w, h):
    the distance to its farthest corner."""
    return max(math.hypot(cx - tx, cy - ty) for cx in (x, x + w) for cy in (y, y + h))


def touch_ripple(cv, x, y, w, h, tx, ty, p, color, radius=0, alpha=0.35, fade=0.45):
    """Draw a touch ripple at progress `p` (0 -> 1) inside the box (x, y, w, h)
    with corner `radius`, spreading from the touch point (tx, ty). The circle
    grows quickly then eases, clipped to the box, and fades out over the last
    `fade` of the run. Draw it over the button's fill and under its label."""
    if not 0 < p < 1:
        return
    r = ripple_reach(x, y, w, h, tx, ty) * (1 - (1 - p) ** 2)
    a = alpha * min(1.0, (1 - p) / fade) if fade > 0 else alpha
    with cv.clip(x, y, w, h, radius=radius):
        cv.sector(tx, ty, max(r, 1.0), 0, 2 * math.pi, color, alpha=a)


# The demo: one wide button tapped twice, at two different points, by a
# fingertip that presses down for each tap.
BW, BH = 760, 190
BX, BY = (demo.W - BW) / 2, (demo.H - BH) / 2
TAPS = ((0.5, BX + BW * 0.13, BY + BH * 0.62), (1.7, BX + BW * 0.86, BY + BH * 0.4))
RUN = 1.1


def draw(n, cv):
    t = n / demo.FPS
    cv.shadow(BX, BY, BW, BH, radius=24, dy=10, blur=30, color=(0, 0, 0, 0.45))
    cv.rect(BX, BY, BW, BH, demo.TEAL, radius=24)
    for start, tx, ty in TAPS:
        touch_ripple(cv, BX, BY, BW, BH, tx, ty, demo.phase(n, start, start + RUN), demo.INK, radius=24)
    demo.word(cv, 'CONTINUE', demo.W / 2, demo.H / 2, size=64, color=demo.BG)
    cv.mark('button', BX, BY, BW, BH)

    # The fingertip: drifts to each touch point and shrinks a little as it presses.
    (s0, x0, y0), (s1, x1, y1) = TAPS
    move = vb.interpolate(t, [s0 + 0.35, s1 - 0.1], [0, 1], ease=vb.ease_in_out_quart)
    fx, fy = x0 + (x1 - x0) * move, y0 + (y1 - y0) * move
    press = max(max(0.0, 1 - abs(t - s) / 0.12) for s, _, _ in TAPS)
    show = vb.interpolate(t, [0.1, 0.35, 2.55, 2.8], [0, 1, 1, 0])
    if show > 0:
        r = 30 - 8 * press
        demo.dot(cv, fx, fy, r=r, color=demo.INK, alpha=(0.35 + 0.3 * press) * show)
        cv.arc(fx, fy, r, 0, 2 * math.pi, demo.INK, width=3, alpha=0.9 * show)


TECHNIQUE = Technique(
    id='touch-ripple',
    name='Touch ripple',
    family='ui',
    group='Buttons',
    aliases=('ink ripple', 'material ripple', 'tap ripple', 'ripple effect'),
    definition='When a button is tapped, a soft circle spreads out from the spot the finger touched until '
               'it fills the button, then fades away.',
    phrasings=('a ripple that spreads from where you tap the button',
               'the button shows a circle of ink growing out of the press point',
               'tap feedback like on an Android button'),
    related=('click-ripple-indicator', 'ripple', 'ink-splash-spread', 'location-ripple-pulse',
             'highlighter-swipe', 'spotlight-hover'),
    api=('videobuilder.techniques.ui.touch_ripple.touch_ripple',
         'videobuilder.techniques.ui.touch_ripple.ripple_reach'),
    demo=lambda: demo.film(draw),
)
