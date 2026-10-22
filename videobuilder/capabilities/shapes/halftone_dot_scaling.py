"""Halftone dot scaling: a fixed grid of dots whose radii follow a tone field,
so a soft shape or gradient appears in the dot sizes alone and moves as the
field does. `vb.halftone_pattern` makes a fill of equal dots; this scales each
dot on its own."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def draw_halftone(cv, x, y, w, h, pitch, tone, color, alpha=1.0, min_r=0.0, max_r=None):
    """Fill the box (x, y, w, h) with a grid of dots `pitch` px apart, centred
    in the box. `tone(u, v)` gives each dot's ink 0 -> 1 from its position as
    fractions of the box (0 -> 1 across, 0 -> 1 down); the dot's area follows
    the tone, as on a printed screen, from `min_r` up to `max_r` (default half
    the pitch, where neighbours just touch). Dots under 0.3 px are skipped.
    All dots are filled as one path. Returns the box."""
    max_r = pitch / 2 if max_r is None else max_r
    cols, rows = max(1, int(w // pitch)), max(1, int(h // pitch))
    x0 = x + (w - (cols - 1) * pitch) / 2
    y0 = y + (h - (rows - 1) * pitch) / 2
    c = cv.ctx
    c.new_path()
    for j in range(rows):
        cy = y0 + j * pitch
        v = j / (rows - 1) if rows > 1 else 0.5
        for i in range(cols):
            u = i / (cols - 1) if cols > 1 else 0.5
            r = min_r + (max_r - min_r) * math.sqrt(vb.clamp01(tone(u, v)))
            if r >= 0.3:
                cx = x0 + i * pitch
                c.new_sub_path()
                c.arc(cx, cy, r, 0, 2 * math.pi)
    c.set_source_rgba(*vb.rgba(color, alpha))
    c.fill()
    return vb.Box(x, y, w, h)


def blob_tone(cx, cy, radius, aspect=1.0, floor=0.0):
    """A tone field for `draw_halftone`: full ink at (cx, cy) (box fractions),
    falling smoothly to `floor` at `radius` and beyond; `aspect` stretches the
    distance across so a blob stays round in a wide box (pass w / h)."""
    def tone(u, v):
        k = 1 - vb.clamp01(math.hypot((u - cx) * aspect, v - cy) / radius)
        return floor + (1 - floor) * k * k * (3 - 2 * k)
    return tone


def draw(n, cv):
    t = n / demo.FPS
    pitch = 28
    bw, bh = demo.W - 160, demo.H - 160
    aspect = bw / bh
    p = vb.ease_in_out_quart(demo.phase(n, 0.2, 2.8))
    # Two soft blobs crossing the screen, plus a gentle diagonal wave underneath.
    a = blob_tone(0.15 + 0.7 * p, 0.3 + 0.4 * p, 0.5, aspect)
    b = blob_tone(0.85 - 0.7 * p, 0.75 - 0.35 * p, 0.38, aspect)

    def tone(u, v):
        wave = 0.18 + 0.12 * math.sin(2 * math.pi * (u * aspect * 0.8 + v * 0.8 - t * 0.6))
        return max(wave, a(u, v), b(u, v))

    box = draw_halftone(cv, 80, 80, bw, bh, pitch, tone, demo.ACCENT)
    cv.mark('halftone', *box)


CAPABILITY = Capability(
    id='halftone-dot-scaling',
    name='Halftone dot scaling',
    family='shapes',
    group='Repeaters & patterns',
    aliases=('dot screen morph', 'halftone pulse', 'dot size wave'),
    definition='Dots on an evenly spaced grid each grow or shrink with the brightness beneath them, '
               'so a gradient or shape shows up only in their sizes and drifts as those sizes change.',
    phrasings=('a grid of dots where the sizes swell and shrink to make a moving shape',
               'animated halftone, like a newspaper print that moves',
               'dot pattern whose dots get bigger where the image is bright'),
    related=('halftone', 'radio-dot-scale', 'dot-density-map', 'dot-grid-displacement', 'circle-pop',
             'dither-reveal'),
    api=('videobuilder.capabilities.shapes.halftone_dot_scaling.draw_halftone',
         'videobuilder.capabilities.shapes.halftone_dot_scaling.blob_tone'),
    demo=lambda: demo.film(draw),
)
