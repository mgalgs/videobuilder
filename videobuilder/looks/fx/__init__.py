"""Filter looks: an art style laid over whatever a film has already drawn
-- a photo, a screen capture, footage -- every pixel, frame by frame.

    with looks.filter(cv, 'pop-art', t):    # everything drawn inside gets the look
        draw_the_video_as_usual(n, cv)
    # copy that must stay readable goes here, outside the filter

A scene look (looks.paint) repaints shapes the video describes; a filter
treats pixels, so it works on any picture. Each filter is a `Filter`: a
name shared with the scene look of the same style where there is one, and a
`treat(im, t, age, u, **opts)` that takes the frame as a PIL RGB image (at
the canvas's device size; `u` is its short side over 1080) and returns the
treated image, the same size. Pillow and cairo only, no numpy: the helpers
below are what the five built-in filters are made of, and anything that
doesn't depend on the frame (screens, grids, paper) is made once and cached.
"""
import math
import random
from contextlib import contextmanager
from functools import lru_cache

import cairo
from PIL import Image, ImageChops, ImageFilter

from ..look import _key


class Filter:
    """A named filter look: `treat(im, t, age, u, **opts)` returns `im` (a
    PIL RGB image) in this style.

    - `t`: film time in seconds -- the filter's own motion runs on it.
    - `age`: seconds since the filter came on screen, for one-off moves;
      defaults to `t`.
    - `u`: the frame's short side over 1080, in device pixels, so strokes
      and dots size the same at every size and preview scale.

    `fps`: the rate the filter steps its own motion at (pixel: 8), or None
    for smooth; `step(t)` is the time to draw the picture underneath at so
    it steps with it."""

    def __init__(self, name, title, line, treat, aliases=(), fps=None):
        if _key(name) != name:
            raise ValueError(f'filter name {name!r} must be lowercase words joined by hyphens')
        self.name, self.title, self.line, self.treat = name, title, line, treat
        self.aliases = tuple(aliases)
        self.fps = fps

    def step(self, t):
        """`t` held to this filter's step rate (unchanged for a smooth filter)."""
        return t if not self.fps else math.floor(t * self.fps + 1e-9) / self.fps

    def __repr__(self):
        return f'<filter look {self.name}: {self.title}>'


# ---- between cairo and PIL ----

def surface_image(surface, x=0, y=0, w=None, h=None):
    """The device pixels of `surface` in (x, y, w, h) as a PIL RGB image."""
    surface.flush()
    sw, sh = surface.get_width(), surface.get_height()
    im = Image.frombuffer('RGBA', (sw, sh), bytes(surface.get_data()), 'raw', 'BGRA', surface.get_stride(), 1)
    if (x, y, w, h) != (0, 0, None, None):
        im = im.crop((x, y, x + (sw if w is None else w), y + (sh if h is None else h)))
    return im.convert('RGB')


def image_surface(im):
    """A PIL RGB image as an opaque cairo surface."""
    data = bytearray(im.convert('RGB').tobytes('raw', 'BGRX'))
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_RGB24, im.width, im.height, im.width * 4)


@contextmanager
def apply(cv, flt, t, age=None, box=None, opts=None):
    """`looks.filter`: see there."""
    saved_surface, saved_ctx = cv.surface, cv.ctx
    sw, sh = saved_surface.get_width(), saved_surface.get_height()
    off = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
    copy = cairo.Context(off)
    copy.set_source_surface(saved_surface, 0, 0)    # start from what the film has drawn so far
    copy.set_operator(cairo.OPERATOR_SOURCE)
    copy.paint()
    ctx = cairo.Context(off)
    ctx.set_matrix(saved_ctx.get_matrix())
    ctx.set_antialias(saved_ctx.get_antialias())
    cv.surface, cv.ctx = off, ctx
    try:
        yield cv
    finally:
        cv.surface, cv.ctx = saved_surface, saved_ctx
    if box is None:
        x0, y0, x1, y1 = 0, 0, sw, sh
    else:
        bx, by, bw, bh = box
        pts = [saved_ctx.user_to_device(px, py) for px, py in ((bx, by), (bx + bw, by), (bx, by + bh), (bx + bw, by + bh))]
        x0 = max(0, math.floor(min(p[0] for p in pts)))
        y0 = max(0, math.floor(min(p[1] for p in pts)))
        x1 = min(sw, math.ceil(max(p[0] for p in pts)))
        y1 = min(sh, math.ceil(max(p[1] for p in pts)))
        if x1 - x0 < 2 or y1 - y0 < 2:
            return
    im = surface_image(off, x0, y0, x1 - x0, y1 - y0)
    out = flt.treat(im, t, t if age is None else age, min(sw, sh) / 1080, **(opts or {}))
    c = saved_ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(image_surface(out), x0, y0)
    c.rectangle(x0, y0, x1 - x0, y1 - y0)
    c.fill()
    c.restore()


# ---- the kit the filters are made of ----

def luma(im):
    return im.convert('L')


def work_factor(u, full=1.0):
    """How many device px one working px covers: a filter whose style can
    take it treats a 1080 frame at half size (`full` px of detail at 1080),
    a small preview at full size."""
    return max(1, round(2 * u / full))


def shrink(im, k):
    return im if k == 1 else im.reduce(k)


def grow(im, size, resample=Image.NEAREST):
    return im if im.size == size else im.resize(size, resample)


def threshold(im, level):
    """An L image: 255 where `im` is above `level`, else 0."""
    return im.point([0] * (level + 1) + [255] * (255 - level))


def edges(gray, level=28, blur=1.0, thick=3):
    """An L mask of the strong edges in `gray`: softened by `blur`, found,
    cut at `level` and thickened to about `thick` px (rounded to an odd
    MaxFilter size; 1 or less leaves the found edge as it is)."""
    if blur:
        gray = gray.filter(ImageFilter.GaussianBlur(blur))
    m = threshold(gray.filter(ImageFilter.FIND_EDGES), level)
    size = int(round(thick)) | 1
    if size > 1:
        m = m.filter(ImageFilter.MaxFilter(size))
    return m


def palette_image(colours):
    """A P image carrying `colours` ('#rrggbb'), for Image.quantize(palette=)."""
    flat = []
    for c in colours:
        flat += [int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)]
    pal = Image.new('P', (1, 1))
    pal.putpalette(flat + flat[:3] * (256 - len(colours)))
    return pal


def posterize(im, pal, dither=False):
    """`im` mapped to the nearest colours of `pal` (palette_image): a P image."""
    return im.quantize(palette=pal, dither=Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE)


def recolour(q, colours):
    """The P image `q` with its palette swapped for `colours`, as RGB: the
    same areas in other inks (a dot colour per fill, say)."""
    q = q.copy()
    flat = []
    for c in colours:
        flat += [int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)]
    q.putpalette(flat + flat[:3] * (256 - len(colours)))
    return q.convert('RGB')


@lru_cache(maxsize=16)
def _screen_cell(pitch):
    """One cell of a 45-degree halftone screen: dots at the corners and the
    centre of a square `pitch` * sqrt 2 wide, each pixel's value its distance
    from the nearest dot centre (0 at a centre, 255 at the farthest point)."""
    p = max(2, round(pitch * math.sqrt(2)))
    far = p / 2
    data = bytearray(p * p)
    for y in range(p):
        for x in range(p):
            d = min(math.hypot(x + 0.5 - cx, y + 0.5 - cy) for cx, cy in ((0, 0), (p, 0), (0, p), (p, p), (p / 2, p / 2)))
            data[y * p + x] = min(255, int(255 * d / far))
    return Image.frombytes('L', (p, p), bytes(data))


@lru_cache(maxsize=8)
def _tiled_screen(pitch, w, h):
    cell = _screen_cell(pitch)
    p = cell.width
    out = Image.new('L', (w + p, h + p))
    for y in range(0, h + p, p):
        for x in range(0, w + p, p):
            out.paste(cell, (x, y))
    return out


def screen(w, h, pitch, dx=0.0, dy=0.0):
    """A w x h halftone screen (see _screen_cell), slid by (dx, dy) px: the
    dots drift as it slides. Tiled once per size and cached."""
    big = _tiled_screen(max(4, round(pitch)), w, h)
    p = big.width - w
    ox, oy = int(dx) % p, int(dy) % p
    return big.crop((ox, oy, ox + w, oy + h))


def halftone(tone, pitch, dx=0.0, dy=0.0):
    """An L mask of halftone dots for the L image `tone` (255: a solid
    cell, 0: no dot), each dot as big as its cell's tone: a printed screen."""
    s = screen(tone.width, tone.height, pitch, dx, dy)
    return threshold(ImageChops.subtract(tone, s), 0)


@lru_cache(maxsize=12)
def noise(w, h, seed, stretch=1, blur=0.0):
    """Seeded grey noise, w x h, cached: `stretch` draws it that many times
    longer along x (grain, fibres), `blur` softens it."""
    rnd = random.Random(seed)
    nw = max(1, w // stretch)
    im = Image.frombytes('L', (nw, h), rnd.randbytes(nw * h))
    if stretch > 1:
        im = im.resize((w, h), Image.BICUBIC)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im


@lru_cache(maxsize=8)
def wave_band(w, h, period, lo, hi):
    """A grey image (w + period) x h: a soft vertical band from `lo` to `hi`
    and back every `period` px along x. Crop it at a moving offset for a
    shimmer that travels across the frame."""
    period = max(2, int(period))
    row = bytes(int(lo + (hi - lo) * (0.5 + 0.5 * math.cos(2 * math.pi * x / period))) for x in range(w + period))
    return Image.frombytes('L', (w + period, 1), row).resize((w + period, h), Image.NEAREST)


def boil(t, per_second=15):
    """The step a hand-drawn texture is on: a new one every 1/`per_second`
    s (15: on twos at 30 fps)."""
    return math.floor(t * per_second + 1e-9)
