"""What the type styles share: the room a style lays its lines out in per
frame shape, fitting given lines to it, where each letter of a line sits,
colour mixing, a soft blur, and a seeded random per letter."""
import math
import random
from functools import lru_cache

import cairo

from .. import text
from ..canvas import Canvas, rgba
from ..layout import Box


def shape(box):
    """'tall', 'wide' or 'square': which layout a box gets."""
    if box.h > box.w * 1.2:
        return 'tall'
    if box.w > box.h * 1.2:
        return 'wide'
    return 'square'


def room(box, tall=(0.86, 0.56), wide=(0.78, 0.66), square=(0.84, 0.64)):
    """(inner box, the width and height the lines may take, shape): `box`
    less a margin of 7% of its short side, and the share of that the copy
    gets in each shape -- a tall frame's lines run nearly edge to edge and
    stack higher, a wide frame's leave air at the sides."""
    inner = box.pad(0.07 * min(box.w, box.h))
    k = shape(box)
    fw, fh = {'tall': tall, 'wide': wide, 'square': square}[k]
    return inner, inner.w * fw, inner.h * fh, k


def fit(lines, make_font, w, h, hi=None, lo=10, measure=None):
    """The largest font `make_font(size)` at which every one of `lines` fits
    `w` and the stack of them fits `h`. `measure(line, font)` is a line's
    width (default its advance)."""
    measure = measure or text.measure
    hi = int(hi or h)
    best = make_font(lo)
    a, b = lo, max(lo, hi)
    while a <= b:                  # widths and heights grow with size: bisect it
        mid = (a + b) // 2
        f = make_font(mid)
        if max(measure(ln, f) for ln in lines) <= w and text.line_height(f) * len(lines) <= h:
            best, a = f, mid + 1
        else:
            b = mid - 1
    return best


@lru_cache(maxsize=512)
def advances(line, font):
    """The x of each character of `line` from its start, and the line's width."""
    xs = [text.measure(line[:i], font) for i in range(len(line))]
    return tuple(xs), text.measure(line, font)


def glyph_w(ch, font):
    return text.measure(ch, font)


def mix(a, b, k):
    """`a` toward `b` by `k`, as an (r, g, b) tuple in 0-255."""
    ca, cb = rgba(a), rgba(b)
    return tuple(255 * (x + (y - x) * k) for x, y in zip(ca[:3], cb[:3]))


def ground(p, fallback='#111216'):
    """The paper, or a near-black stand-in when the style goes over a picture."""
    return p.paper if p.paper is not None else fallback


def rng(*seed):
    return random.Random(':'.join(map(str, seed)))


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def drift(t, hold_t, k=0.08, period=8.0):
    """The hold's slow camera: a push-in toward 1 + `k` that starts at 1%
    a second and eases off, so a held title is never a still. 1.0 before
    the hold starts."""
    if t <= hold_t:
        return 1.0
    return 1.0 + k * (1 - math.exp(-(t - hold_t) / period))


def camera(t, hold_t, cx, cy, box, k=0.08, sway=0.01):
    """`cv.layer` arguments for the hold's camera about (cx, cy): `drift`'s
    push-in, and a slow sway of `sway` of the box's short side on two
    periods that never line up, so even a long hold never comes to rest."""
    s = drift(t, hold_t, k)
    held = max(0.0, t - hold_t)
    a = sway * min(box.w, box.h) * min(1.0, held)
    dx = a * math.sin(2 * math.pi * held / 7.0)
    dy = a * math.sin(2 * math.pi * held / 11.0 + 1.0) - a * math.sin(1.0) * min(1.0, held)
    return {'dx': cx * (1 - s) + dx, 'dy': cy * (1 - s) + dy, 'scale': s}


def blurred(cv, box, radius, paint, alpha=1.0):
    """Draws `paint(sub)` blurred by `radius` px (frame px) into `cv`,
    within `box` (grown by the blur). `sub` is a Canvas in the same frame
    coordinates; it is drawn small and blurred with a Gaussian, so a wide
    blur costs little. A radius under half a pixel draws sharp."""
    s = cv.scale_factor()
    if radius * s < 0.5:
        with cv.layer(opacity=alpha):
            paint(cv)
        return
    from PIL import Image, ImageFilter
    pad = radius * 2.5
    x0, y0, w, h = box.x - pad, box.y - pad, box.w + 2 * pad, box.h + 2 * pad
    k = max(1.0, radius * s / 3)                  # draw at 1/k device resolution: the blur hides it
    sc = s / k
    sub = Canvas(w, h, scale=sc)
    sub.ctx.translate(-x0, -y0)
    paint(sub)
    sub.surface.flush()
    W, H = sub.surface.get_width(), sub.surface.get_height()
    im = Image.frombuffer('RGBA', (W, H), bytes(sub.surface.get_data()), 'raw', 'RGBA', sub.surface.get_stride(), 1)
    im = im.filter(ImageFilter.GaussianBlur(radius * sc))
    data = bytearray(im.tobytes('raw', 'RGBA'))
    out = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, W, H, W * 4)
    ctx = cv.ctx
    ctx.save()
    ctx.translate(x0, y0)
    ctx.scale(1 / sc, 1 / sc)
    ctx.set_source_surface(out, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def line_box(x, y, line, font):
    return Box(x, y, text.measure(line, font), text.line_height(font))


@lru_cache(maxsize=2048)
def _outline(s, font):
    """`s`'s glyph outlines as a cairo path, drawn as text.draw would at (0, 0)."""
    from gi.repository import PangoCairo
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
    content, _ = text._content(font)
    ctx.move_to(0, (text.line_height(font) - content) / 2)
    PangoCairo.layout_path(ctx, text._layout(ctx, s, font))
    return ctx.copy_path()


def glyphs(cv, s, font, x, y, colour, alpha=1.0):
    """`text.draw(cv, [s], font, x, y, colour)` from cached outlines: the
    same letters, but cheap under any rotation or squash, where drawing
    text would make a new scaled font for every transform."""
    ctx = cv.ctx
    ctx.save()
    ctx.translate(x, y)
    ctx.new_path()
    ctx.append_path(_outline(s, font))
    ctx.set_source_rgba(*rgba(colour, alpha))
    ctx.fill()
    ctx.restore()
