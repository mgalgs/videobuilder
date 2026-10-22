"""Screen tearing: the picture is cut by one or two hard horizontal seams, and
each band below a seam still shows an earlier moment, as when a display
swaps frames halfway through drawing one. Anything moving sideways breaks
into offset pieces along the seam, and the seam rolls slowly down the screen."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def tear_seams(t, count=1, speed=0.35, top=0.0, bottom=1.0, start=0.0):
    """Where the seams sit at time `t` seconds, as fractions of the frame
    height (top to bottom): `count` seams evenly spaced through `top` ..
    `bottom`, all rolling down at `speed` frame-heights a second and wrapping
    round, the way a tear drifts when the frame rate and refresh rate don't
    match. `start` shifts where the roll begins."""
    span = bottom - top
    out = [top + ((start + speed * t + i / count) % 1.0) * span for i in range(count)]
    return sorted(out)


def screen_tear(cv, draw_at, t, seams, lag=1 / 15, seam=None, x=0, y=0, w=None, h=None):
    """Draw a torn frame: `draw_at(cv, t)` draws the picture as it is at time
    `t`. `seams` are cut heights as fractions of (y .. y + h) (default the
    whole frame); the band above the first seam shows time `t`, the next one
    `t - lag`, the next `t - 2 * lag`, and so on, so whatever moves splits
    along each cut. `seam`, a colour, draws a faint hairline along each cut.
    With no seams it is `draw_at(cv, t)` untouched. Returns the bands drawn
    as `(top, height, time)`.

    In a film, call it from `draw` with the frame's time and a way to draw any
    moment, e.g. `screen_tear(cv, lambda c, s: scene(c, s), n / fps, tear_seams(n / fps))`."""
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    cuts = sorted(vb.clamp01(s) for s in seams)
    edges = [y, *(y + s * h for s in cuts), y + h]
    bands = []
    for i, (y0, y1) in enumerate(zip(edges, edges[1:])):
        if y1 - y0 > 0.5:
            bands.append((y0, y1 - y0, t - i * lag))
    if len(bands) <= 1:
        draw_at(cv, t)
        return [(y, h, t)]
    for top, bh, when in bands:
        with cv.clip(x, top, w, bh):
            draw_at(cv, when)
    if seam:
        for top, _, _ in bands[1:]:
            cv.rect(x, top - 1, w, 2, seam, alpha=0.35)
    return bands


SWING = 1.2  # seconds for one left-right sweep of the demo subject


def _scene(cv, t):
    """A ring with a dot inside and a tall pillar on each side, swinging
    sideways fast, so a cut through it shows clearly."""
    cx = demo.W / 2 + 170 * math.sin(2 * math.pi * t / SWING)
    cy = demo.H / 2
    cv.arc(cx, cy, 120, 0, 2 * math.pi, demo.TEAL, width=14)
    demo.dot(cv, cx, cy, r=50, color=demo.ACCENT)
    for side in (-1, 1):
        cv.rect(cx + side * 175 - 12, cy - 170, 24, 340, demo.INK, radius=12)
    cv.mark('subject', cx - 187, cy - 170, 374, 340)


def draw(n, cv):
    t = n / demo.FPS
    # Clean at first, then one rolling tear, then two near the end.
    if t < 0.6:
        seams = []
    elif t < 1.9:
        seams = tear_seams(t, count=1, speed=0.3, top=0.15, bottom=0.85, start=0.05)
    else:
        seams = tear_seams(t, count=2, speed=0.3, top=0.12, bottom=0.88, start=0.1)
    screen_tear(cv, _scene, t, seams, lag=0.11, seam=demo.MUTED)


TECHNIQUE = Technique(
    id='screen-tearing',
    name='Screen tearing',
    family='vfx',
    group='Glitch',
    aliases=('frame tear', 'vertical sync tear', 'v-sync tear', 'tear glitch'),
    definition='A hard horizontal seam slices the picture so the part below it lags a moment behind the '
               'part above, and anything moving sideways is broken into offset halves along the line.',
    phrasings=('make it look like the screen is tearing, like a game with v-sync off',
               'split the frame along a line so the bottom half is a beat behind the top',
               'a torn-frame glitch where moving things don\'t line up across a horizontal cut'),
    related=('scanline-tear', 'glitch-transition', 'frame-stutter', 'screen-refresh-flicker',
             'dust-and-scratches', 'light-leak'),
    api=('videobuilder.techniques.vfx.screen_tearing.screen_tear',
         'videobuilder.techniques.vfx.screen_tearing.tear_seams'),
    demo=lambda: demo.film(draw),
)
