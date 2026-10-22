"""Infinite perspective grid: a floor of grid lines stretching out to a
horizon, sliding toward the viewer without end, so the camera seems to glide
forward over it.

The floor is projected with a plain pinhole camera: a row `z` cells beyond
the near edge appears at scale `depth / (depth + z)`, which places it between
the near edge (scale 1) and the horizon (scale 0). Rows sit one cell apart
and shift by the fractional part of `travel`, so whole-number travel looks
the same and any speed loops seamlessly.
"""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def perspective_grid(cv, travel, horizon=None, near=None, cell=None, depth=4.0, cx=None, shift=0.0,
                     color='#ffffff', width=2.0, fade=(0.03, 0.25), alpha=1.0):
    """Draw a grid floor receding from `near` (screen y, default the frame
    bottom) to `horizon` (screen y, default 45% down), moved `travel` cells
    toward the viewer. Animate `travel` to fly forward over it.

    `cell`: a cell's width in px at the near edge (default a tenth of the
    frame width). `depth`: the camera's distance from the near edge, in
    cells -- smaller looks lower and wider-angle, larger flatter. `cx`: the
    vanishing point's x (default the centre). `shift`: a sideways offset in
    cells, for strafing or banking. Lines are `width` px at the near edge,
    thinning with distance, and fade out toward the horizon between the
    scales in `fade`. The grid extends sideways as far as the frame shows."""
    W, H = cv.width, cv.height
    horizon = H * 0.45 if horizon is None else horizon
    near = H if near is None else near
    cell = W / 10 if cell is None else cell
    cx = W / 2 if cx is None else cx
    f0, f1 = fade
    span = near - horizon

    def y_at(s):
        return horizon + span * s

    def shade(s):
        return alpha * vb.clamp01((s - f0) / (f1 - f0))

    s_bottom = (H - horizon) / span  # scale at the frame's bottom edge (1 when near is the bottom)
    z_bottom = depth / s_bottom - depth
    z_far = depth / f0 - depth
    frac = travel - math.floor(travel)

    # Rows across the floor, nearest last so they draw on top.
    rows = []
    k = math.floor(z_bottom + frac)
    while True:
        z = k - frac
        if z > z_far:
            break
        if z >= z_bottom:
            rows.append(depth / (depth + z))
        k += 1
    for s in reversed(rows):
        a = shade(s)
        if a > 0:
            cv.line(0, y_at(s), W, y_at(s), color, width=max(0.5, width * s), alpha=a)

    # Columns run from the frame bottom to the horizon, in bands so each
    # stretch thins and fades with its own depth.
    reach = max(cx, W - cx) / (cell * s_bottom) + 1
    off = shift - math.floor(shift)
    bands = [s_bottom] + [s for s in rows if s < s_bottom] + [f0]
    for i in range(-math.ceil(reach), math.ceil(reach) + 1):
        x = (i - off) * cell
        for sa, sb in zip(bands, bands[1:]):
            s = (sa + sb) / 2
            a = shade(s)
            if a > 0:
                cv.line(cx + x * sa, y_at(sa), cx + x * sb, y_at(sb), color,
                        width=max(0.5, width * s), alpha=a)


def _sky(cv, horizon):
    """A dark sky warming to a soft glow just above the horizon."""
    for j in range(24):
        t = j / 23
        h = 90 * (1 - t) + 4
        cv.rect(0, horizon - h, demo.W, h, demo.ACCENT, alpha=0.025)
    cv.line(0, horizon, demo.W, horizon, demo.ACCENT, width=2, alpha=0.8)


def draw(n, cv):
    horizon = demo.H * 0.42
    _sky(cv, horizon)
    travel = 1.8 * n / demo.FPS  # a steady glide, about five rows over the demo
    perspective_grid(cv, travel, horizon=horizon, depth=3.5, color=demo.TEAL, width=3)
    cv.mark('grid', 0, horizon, demo.W, demo.H - horizon)


CAPABILITY = Capability(
    id='infinite-perspective-grid',
    name='Infinite perspective grid',
    family='camera',
    group='3D motion',
    aliases=('synthwave grid', 'retro grid', 'outrun grid', 'vaporwave grid', 'perspective floor grid',
             'perspective grid'),
    definition='A floor of grid lines runs out to a far horizon and keeps sliding toward the camera, '
               'so it feels like gliding forward over it forever.',
    phrasings=('a neon grid floor racing toward us like an 80s arcade intro',
               'fly low over an endless glowing grid that stretches to the horizon',
               'make the background a retro grid that scrolls into the screen'),
    related=('infinite-zoom-tunnel', 'perspective-tunnel-type', 'perspective-crawl', 'tile-flip',
             'swiss-grid-slide', 'bento-grid-reveal'),
    api=('videobuilder.capabilities.camera.infinite_perspective_grid.perspective_grid',),
    demo=lambda: demo.film(draw),
)
