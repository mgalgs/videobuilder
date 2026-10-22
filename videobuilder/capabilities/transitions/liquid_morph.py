"""Liquid Morph: drops of the incoming scene well up over the outgoing one,
drift together and fuse like liquid, bridging into one pool that floods the
frame. Each drop is ringed by a band of liquid colour."""
import math
import random

import cairo
from PIL import Image as PILImage, ImageDraw, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

STEP = 4  # the goo field is worked out at 1/STEP of frame px, then smoothed back up


def _a8(m):
    """An 'L' PIL image -> a cairo A8 surface (A8 rows are padded to a stride)."""
    w, h = m.size
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8, w)
    raw = m.tobytes()
    data = bytearray(stride * h)
    for row in range(h):
        data[row * stride:row * stride + w] = raw[row * w:(row + 1) * w]
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_A8, w, h, stride)


def goo_field(balls, width, height, goo=28, step=STEP):
    """The blurred union of `balls` (`(cx, cy, r)` in frame px) as an 'L'
    image at 1/`step` size: high inside, falling off outside. Thresholding it
    gives metaballs -- circles near each other grow a bridge and fuse. `goo`
    is how far (frame px) the blur reaches, so how readily they join."""
    w, h = math.ceil(width / step), math.ceil(height / step)
    m = PILImage.new('L', (w, h), 0)
    d = ImageDraw.Draw(m)
    for cx, cy, r in balls:
        if r > 0:
            d.ellipse(((cx - r) / step, (cy - r) / step, (cx + r) / step, (cy + r) / step), fill=255)
    return m.filter(ImageFilter.GaussianBlur(goo / step / 2))


def goo_mask(field, level=128, soft=10):
    """`field` thresholded at `level` (0-255) with a `soft`-wide ramp: the
    liquid's shape as an alpha image. A lower `level` gives a fatter shape."""
    lo = level - soft / 2
    return field.point(lambda v: max(0, min(255, round((v - lo) * 255 / soft))))


def paint_masked(cv, mask, draw, step=STEP):
    """Run `draw(cv)` into a group and paint it through `mask` (an 'L' image
    at 1/`step` of frame px), smoothed back up to frame size."""
    c = cv.ctx
    c.push_group()
    draw(cv)
    c.pop_group_to_source()
    c.save()
    c.scale(step, step)
    pat = cairo.SurfacePattern(_a8(mask))
    pat.set_filter(cairo.FILTER_GOOD)
    c.mask(pat)
    c.restore()


def metaballs(cv, balls, color, goo=28, alpha=1.0):
    """Draw `balls` (`(cx, cy, r)` in frame px) as one fused blob of `color`:
    the goo / metaball look for a still or moving set of circles."""
    mask = goo_mask(goo_field(balls, cv.width, cv.height, goo))
    paint_masked(cv, mask, lambda c: c.fill(color, alpha=alpha))


def drops(p, width, height, count=16, seed=0):
    """The liquid at progress `p` (0 -> 1) as `(cx, cy, r)` balls. Each drop
    wells up at its own time and spot, swells, and drifts toward the middle
    so neighbours touch and merge; by `p` = 1 they cover the frame."""
    rnd = random.Random(seed)
    cx, cy = width / 2, height / 2
    reach = math.hypot(width, height) / 2
    out = []
    for i in range(count):
        # spread the drops over a jittered grid so they start apart
        cols = math.ceil(math.sqrt(count * width / height))
        gx, gy = i % cols, i // cols
        rows = math.ceil(count / cols)
        x = (gx + 0.5 + rnd.uniform(-0.35, 0.35)) * width / cols
        y = (gy + 0.5 + rnd.uniform(-0.35, 0.35)) * height / rows
        start = rnd.uniform(0.0, 0.3)
        q = vb.clamp01((p - start) / (1 - start))
        grow = 1 - (1 - q) ** 2.2                       # swells fast, then settles
        pull = 0.45 * (q * q * (3 - 2 * q))             # slides a little toward the middle
        bx, by = x + (cx - x) * pull, y + (cy - y) * pull
        r = reach * (grow * rnd.uniform(0.09, 0.15) + 0.9 * q ** 4)  # drops first, then the flood
        out.append((bx, by, r))
    return out


def liquid_morph(cv, a, b, p, color=demo.ACCENT, rim=26, goo=60, count=16, seed=0):
    """Draw the morph at progress `p` (0 -> 1): `a(cv)` underneath, then blobs
    of `b(cv)` welling up, swelling and fusing into one pool that fills the
    frame. Each blob wears a `rim`-wide band of liquid `color` (0 for none);
    `goo` (frame px) is how eagerly neighbouring blobs bridge.

    In a film, call it while two shots are live in an overlap, e.g.
    `liquid_morph(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    a(cv)
    blur = goo * (0.3 + 0.7 * vb.clamp01(p / 0.5))  # less blur early, so the first small drops show
    field = goo_field(drops(p, cv.width, cv.height, count, seed), cv.width, cv.height, blur)
    if rim:
        # the field falls 255 -> 0 across about `goo` px, so a rim of `rim` px is that share of it
        level = max(20, round(128 - 255 * rim / (2 * goo) * (1 - vb.clamp01((p - 0.8) / 0.2))))
        paint_masked(cv, goo_mask(field, level), lambda c: c.fill(color))
    paint_masked(cv, goo_mask(field, 140), b)


TECHNIQUE = Technique(
    id='liquid-morph',
    name='Liquid morph',
    family='transitions',
    group='Organic and Fluid',
    aliases=('liquid transition', 'metaball transition', 'blob merge', 'goo transition', 'metaballs'),
    definition='Blobs of the next scene bubble up over the current one and run together like '
               'drops of liquid, fusing into one pool that takes over the frame.',
    phrasings=('have the next shot ooze in as gooey blobs that join up',
               'a melty, liquid transition where the blobs merge into the new scene',
               'drops that swell and stick together until they fill the screen'),
    related=('metaball-goo-text', 'morphing-blob', 'particle-morph', 'blob-to-icon-morph',
             'liquid-fill-level', 'sphere-to-grid-morph'),
    api=('videobuilder.techniques.transitions.liquid_morph.liquid_morph',
         'videobuilder.techniques.transitions.liquid_morph.metaballs',
         'videobuilder.techniques.transitions.liquid_morph.goo_field',
         'videobuilder.techniques.transitions.liquid_morph.goo_mask'),
    demo=lambda: demo.two_scenes(liquid_morph, start=0.6, length=1.8),
)
