"""Mandelbrot zoom: the camera dives into the edge of the Mandelbrot set at a
steady exponential rate, filaments and baby bulbs unfolding until a tiny
copy of the whole set fills the frame."""
import math

from PIL import Image as PILImage

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability

# The whole set, comfortably framed: where a dive starts.
WHOLE = (-0.75, 0.0)
# Seahorse valley: a spot on the set's edge where spirals keep unfolding (no
# copy of the set within a double's reach, so a dive here never lands).
SEAHORSE = (-0.743643887037151, 0.131825904205330)
# A copy of the whole set, ~1.5e-4 wide, out on the antenna (the period-5
# copy whose centre is -1.98542425...): centred on the copy, not its nucleus.
# MINI_WIDTH frames it with a margin, ~15,000 times closer than the whole set.
MINI = (-1.985478, 0.0)
MINI_WIDTH = 2.4e-4
STOPS = (demo.BG, '#1d3b5a', demo.TEAL, demo.INK, demo.ACCENT, '#3a1f3a')


def _palette(stops, period, quality, inside):
    """Three 256-entry lookup tables (r, g, b) for Pillow's mandelbrot grey,
    which is `iterations * 255 / quality` (0 inside the set). Colour cycles
    through `stops` every `period` iterations, so bands keep their colour as
    `quality` grows with the zoom."""
    cols = [rgba(c)[:3] for c in stops]
    luts = ([], [], [])
    for v in range(256):
        if v == 0:
            rgb = rgba(inside)[:3]
        else:
            t = (v * quality / 255 / period) % 1 * len(cols)
            i, f = int(t), t - int(t)
            a, b = cols[i], cols[(i + 1) % len(cols)]
            rgb = tuple(a[k] + (b[k] - a[k]) * f for k in range(3))
        for k in range(3):
            luts[k].append(round(rgb[k] * 255))
    return luts


def mandelbrot(px_w, px_h, center, width, quality=None, stops=STOPS, period=48, inside=demo.BG,
               supersample=2):
    """A `vb.Image` of the Mandelbrot set, `px_w` x `px_h` pixels, showing
    `width` units of the complex plane around `center` (re, im). `quality`
    (max iterations) defaults to rising with the magnification, so deep
    frames keep their detail. It is rendered `supersample` times larger and
    averaged down, so hair-thin filaments read as lines, not speckle."""
    if quality is None:
        quality = int(min(1000, 80 + 70 * max(0.0, math.log10(3.5 / width))))
    height = width * px_h / px_w
    cx, cy = center
    k = max(1, int(supersample))
    grey = PILImage.effect_mandelbrot((px_w * k, px_h * k), (cx - width / 2, cy - height / 2,
                                                             cx + width / 2, cy + height / 2), quality)
    r, g, b = _palette(stops, period, quality, inside)
    img = PILImage.merge('RGB', (grey.point(r), grey.point(g), grey.point(b)))
    if k > 1:
        img = img.reduce(k)
    return vb.Image.from_pil(img)


def mandelbrot_zoom(cv, x, y, w, h, p, center=MINI, start_width=3.5, end_width=MINI_WIDTH,
                    start_center=WHOLE, **kw):
    """Draw one frame of a zoom into the set at progress `p` (0 -> 1) in the
    box (x, y, w, h). The view goes from `start_width` plane units around
    `start_center` to `end_width` around `center`, narrowing geometrically,
    so every equal step of `p` magnifies by the same factor: the dive feels
    steady, never slowing as it goes deeper. It is one pure zoom about a
    fixed point, so nothing drifts sideways on the way down. The defaults
    start on the whole set and land on a tiny copy of it; `start_center=None`
    zooms straight in on `center`. Rendered at the canvas's device
    resolution. `kw` goes to `mandelbrot`.

    A film eases `p` for a calm start and stop, e.g.
    `mandelbrot_zoom(cv, 0, 0, W, H, vb.ease_in_out_quart(t))`."""
    p = vb.clamp01(p)
    width = start_width * (end_width / start_width) ** p
    if start_center is not None and start_width != end_width:
        # The point that holds still on screen while the view shrinks from
        # (start_center, start_width) to (center, end_width).
        fx, fy = ((c1 * start_width - c0 * end_width) / (start_width - end_width)
                  for c0, c1 in zip(start_center, center))
        f = width / start_width
        center = (fx + (start_center[0] - fx) * f, fy + (start_center[1] - fy) * f)
    s = cv.scale_factor()
    img = mandelbrot(max(2, round(w * s)), max(2, round(h * s)), center, width, **kw)
    cv.image(img, x, y, w, h)
    cv.mark('fractal', x, y, w, h)


def draw(n, cv):
    p = demo.phase(n, 0.2, 2.8)
    p = p * p * (3 - 2 * p)
    mandelbrot_zoom(cv, 0, 0, demo.W, demo.H, p)
    zoom = (3.5 / MINI_WIDTH) ** p
    cv.rect(demo.W - 330, demo.H - 104, 280, 64, demo.BG, radius=32, alpha=0.8)
    demo.word(cv, f'×{zoom:,.0f}', demo.W - 190, demo.H - 72, font=demo.mono(38, 700))


CAPABILITY = Capability(
    id='mandelbrot-zoom',
    name='Mandelbrot zoom',
    family='particles',
    group='Fractals',
    aliases=('fractal zoom', 'Mandelbrot dive', 'infinite fractal zoom', 'deep zoom'),
    definition='The view plunges steadily into the ragged edge of the Mandelbrot set, '
               'filaments and baby bulbs blooming out of nowhere until a tiny copy of the whole shape appears.',
    phrasings=('keep zooming into a fractal forever',
               'dive into the Mandelbrot set and show all the detail opening up',
               'a psychedelic endless zoom into those swirly math patterns'),
    related=('scale-zoom-through', 'infinite-zoom-tunnel', 'zoom-to-location-map', 'canvas-pan-and-zoom',
             'zoom-through-shape', 'zoom-to-detail-magnifier'),
    api=('videobuilder.capabilities.particles.mandelbrot_zoom.mandelbrot_zoom',
         'videobuilder.capabilities.particles.mandelbrot_zoom.mandelbrot'),
    demo=lambda: demo.film(draw),
)
