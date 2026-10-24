"""Rotoscope look: whatever the film draws -- a photo, footage, a soft
gradient scene -- is smoothed into a handful of flat fills taken from its own
colours, and every border between two fills is traced in a dark ink line
that boils on twos, so live pictures read as animation traced over by hand.

    with rotoscope_look(cv, t):
        draw_the_footage(n, cv)

Built from the `looks.fx` kit (posterize-and-edge, like the woodblock
filter), but it keeps the picture's own palette instead of a fixed one."""
import math
import random

import cairo
from PIL import Image, ImageChops, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ...looks.fx import Filter, apply, boil, grow, luma, shrink, threshold, work_factor
from ..schema import Capability

INK = '#15131c'


def rotoscope(im, t, age, u, levels=8, ink=INK, thick=3.0, wobble=True):
    """`im` (a PIL RGB image) in the rotoscope look, the same size: smoothed,
    cut to `levels` flat colours picked from the picture itself, and every
    fill border inked `thick` px wide (at 1080) in `ink`. With `wobble` the
    line shifts a pixel on twos, like a fresh tracing every other frame.
    A `looks.fx` treat function: `t`, `age` and `u` as there."""
    k = max(work_factor(u), 3)   # the flattening filters are cheap only well under full res
    small = shrink(im, k).filter(ImageFilter.MedianFilter(5))
    q = small.quantize(colors=levels, method=Image.Quantize.MAXCOVERAGE, kmeans=3, dither=Image.Dither.NONE)
    flat = q.convert('RGB').filter(ImageFilter.ModeFilter(5))    # flat areas, no specks
    lines = threshold(luma(flat).filter(ImageFilter.FIND_EDGES), 6)
    w, h = lines.size
    lines.paste(0, (0, 0, w, h), _rim(w, h))    # FIND_EDGES leaves the outermost pixels unfiltered
    size = int(round(max(1.0, thick * u / k))) | 1
    lines = lines.filter(ImageFilter.MaxFilter(size)) if size > 1 else lines
    lines = grow(lines, im.size, Image.BILINEAR)   # smooth the line mask back up, not blocky NEAREST
    if wobble:
        rnd = random.Random(boil(t))
        lines = ImageChops.offset(lines, rnd.choice((-1, 0, 1)) * k, rnd.choice((-1, 0, 1)) * k)
    out = grow(flat, im.size, Image.BILINEAR)
    out.paste(ink, (0, 0, *im.size), lines)
    return out


def _rim(w, h):
    """An L mask of the one-pixel border of a w x h image."""
    m = Image.new('L', (w, h), 255)
    m.paste(0, (1, 1, w - 1, h - 1))
    return m


ROTOSCOPE = Filter('rotoscope', 'Rotoscope look', 'own colours cut flat, every border traced in ink', rotoscope)


def rotoscope_look(cv, t, age=None, box=None, **opts):
    """A context manager: everything drawn on `cv` inside the block (and what
    was there already) comes out in the rotoscope look -- only inside `box`,
    (x, y, w, h) in frame px, when given. `opts` go to `rotoscope`
    (`levels=`, `ink=`, `thick=`, `wobble=`)."""
    return apply(cv, ROTOSCOPE, t, age, box, opts)


# ---- the demo: a live, softly lit landscape; a scan line sweeps across and
# leaves it traced and flat behind it ----

SKY = ('#2e3466', '#6d7fd8', '#c9cfe6')
HILLS = ('#6a74b8', '#3d4580', '#1d2140')


def _rgb(c):
    return tuple(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _ridge(cv, base, amp, freq, phase, colour):
    pts = [(x, base + amp * math.sin(x * freq + phase) + 0.4 * amp * math.sin(x * freq * 2.3 + phase * 1.7))
           for x in range(0, demo.W + 21, 20)]
    ctx = cv.ctx
    ctx.move_to(0, demo.H)
    for x, y in pts:
        ctx.line_to(x, y)
    ctx.line_to(demo.W, demo.H)
    ctx.close_path()
    ctx.set_source_rgb(*_rgb(colour))
    ctx.fill()


def _live(cv, t):
    """The 'footage': smooth gradients, a soft-edged rising sun, drifting hills."""
    sky = cairo.LinearGradient(0, 0, 0, demo.H * 0.75)
    for stop, c in zip((0, 0.5, 1), SKY):
        sky.add_color_stop_rgb(stop, *_rgb(c))
    cv.ctx.set_source(sky)
    cv.ctx.paint()
    u = demo.H / 1080
    sun_y = (520 - 110 * t) * u
    for i in range(14, 0, -1):    # a blurry glow, not an edge
        demo.dot(cv, 1240 * u, sun_y, (110 + i * 6) * u, color='#f2b705', alpha=0.07)
    demo.dot(cv, 1240 * u, sun_y, 110 * u, color='#f2b705')
    for i, (c, base) in enumerate(zip(HILLS, (560, 720, 880))):
        _ridge(cv, base * u, (70 - 12 * i) * u, (0.004 + 0.0015 * i) / u, t * (0.5 + 0.4 * i) + i, c)


def draw(n, cv):
    t = n / demo.FPS
    _live(cv, t)
    p = vb.ease_in_out_quart(demo.phase(n, 0.5, 1.9))
    x = demo.W * p
    if x > 1:
        with cv.clip(0, 0, x, demo.H), rotoscope_look(cv, t):
            pass
    if 0 < p < 1:
        cv.line(x, 0, x, demo.H, '#ffffff', width=4)


CAPABILITY = Capability(
    id='rotoscope-look',
    name='Rotoscope look',
    family='vfx',
    group='Rotoscope & outline',
    aliases=('animated rotoscope', 'rotoscoping', 'traced animation'),
    definition='Moving pictures are flattened into a few solid colour areas with a dark hand-traced line '
               'around each one, so real footage looks like it was drawn over frame by frame.',
    phrasings=('make the footage look like a cartoon someone traced over it',
               'turn the live video into flat colours with bold ink outlines',
               'that drawn-over-real-video animation style'),
    related=('swirl', 'animated-gradient-sweep', 'look-around', 'whip-pan', 'spin',
             'frame-by-frame-hand-drawn-animation'),
    api=('videobuilder.capabilities.vfx.rotoscope_look.rotoscope_look',
         'videobuilder.capabilities.vfx.rotoscope_look.rotoscope'),
    demo=lambda: demo.film(draw),
)
