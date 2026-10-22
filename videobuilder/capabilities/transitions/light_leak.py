"""Light leak: soft blooms of warm orange, magenta and gold light drift in
across the frame, build to a near-white burn that hides the cut, then drift
on and fade off the incoming scene."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# Each bloom: colour, vertical centre (fraction of height), radius (fraction
# of width), how far it lags behind the sweep, and how fast it drifts.
LEAK_COLORS = (
    ('#ff6a1a', 0.30, 0.55, 0.00, 1.00),
    ('#ff2d78', 0.75, 0.50, 0.10, 0.85),
    ('#ffc23d', 0.50, 0.42, 0.18, 1.15),
    ('#ff8a3a', 0.15, 0.35, 0.28, 0.90),
)


def _bloom(cv, cx, cy, r, color, alpha):
    """One soft disc of light: tinted over what is already drawn (so its colour
    holds even on a bright scene), then screened on to brighten it."""
    rr, gg, bb, _ = vb.canvas.rgba(color)
    for op, k in ((cairo.OPERATOR_OVER, 0.55), (cairo.OPERATOR_SCREEN, 0.8)):
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
        g.add_color_stop_rgba(0.0, rr, gg, bb, alpha * k)
        g.add_color_stop_rgba(0.45, rr, gg, bb, alpha * k * 0.6)
        g.add_color_stop_rgba(1.0, rr, gg, bb, 0.0)
        cv.ctx.set_operator(op)
        cv.ctx.set_source(g)
        cv.ctx.paint()


def light_leak_overlay(cv, p, strength=1.0, blooms=LEAK_COLORS, from_left=True):
    """Paint the leak alone at progress `p` (0 -> 1) over whatever `cv` already
    holds: warm blooms sweep across the frame (left to right, or right to left
    with `from_left=False`), brightest at `p` = 0.5, where a warm wash nearly
    whites the frame out. `strength` scales it all, so a film can also use it
    as a gentle drifting glow without a cut."""
    w, h = cv.width, cv.height
    peak = math.sin(math.pi * vb.clamp01(p))          # 0 -> 1 -> 0
    ctx = cv.ctx
    ctx.save()
    for color, fy, fr, lag, speed in blooms:
        t = vb.clamp01((p - lag * 0.5) / (1 - lag * 0.5)) * speed
        x = -0.4 * w + t * 1.8 * w
        if not from_left:
            x = w - x
        y = h * (fy + 0.08 * math.sin(6 * p + fy * 7))
        r = w * fr * (0.8 + 0.5 * peak)
        _bloom(cv, x, y, r, color, strength * min(1.0, 0.25 + 0.95 * peak))
    # The burn: a warm wash that is nearly opaque at the cut.
    burn = strength * peak ** 4
    ctx.set_operator(cairo.OPERATOR_SCREEN)
    ctx.set_source_rgba(1.0, 0.72, 0.42, 0.7 * burn)
    ctx.paint()
    ctx.restore()


def light_leak(cv, a, b, p, strength=1.0, from_left=True):
    """The transition at progress `p` (0 -> 1): `a(cv)` until the leak peaks at
    the midpoint, `b(cv)` after it, with `light_leak_overlay` on top so the
    cut lands under the brightest moment. In a film, call it inside the
    overlap: `light_leak(cv, lambda c: shot_a(c), lambda c: shot_b(c), f / overlap_frames)`."""
    (a if p < 0.5 else b)(cv)
    light_leak_overlay(cv, p, strength=strength, from_left=from_left)


CAPABILITY = Capability(
    id='light-leak',
    name='Light leak',
    family='transitions',
    group='Light and Flash',
    aliases=('film light leak', 'lens leak', 'warm leak transition', 'camera light leak'),
    definition='Glowing patches of warm orange and pink light slide across the picture, flare up '
               'almost to white, and the next scene is waiting when they clear.',
    phrasings=('switch scenes with a warm film-burn glow sweeping over',
               'let some orange light bleed across the shot to cover the cut',
               'a vintage camera flare between the two clips'),
    related=('lens-dirt-overlay', 'screen-tearing', 'dust-and-scratches', 'thin-film-iridescence',
             'heat-haze', 'luma-wipe'),
    api=('videobuilder.capabilities.transitions.light_leak.light_leak',
         'videobuilder.capabilities.transitions.light_leak.light_leak_overlay'),
    demo=lambda: demo.two_scenes(light_leak, start=0.6, length=1.8),
)
