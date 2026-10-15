"""Layers and compositing on cairo: rects, images, clips, shadows, groups.

Immediate mode: a frame function draws into a fresh Canvas, back to front.
Groups (`layer`) carry opacity and a transform, like a CSS stacking context.
"""
import math
import os
import random
from contextlib import contextmanager
from functools import lru_cache

import cairo
from PIL import Image as PILImage, ImageChops, ImageDraw, ImageFilter, ImageStat

from .layout import Box


def rgba(color, alpha=1.0):
    """A colour -> cairo's (r, g, b, a) floats. Takes '#rgb', '#rgba', '#rrggbb',
    '#rrggbbaa', or an (r, g, b[, a]) tuple of 0-255 channels and 0-1 alpha.
    `alpha` multiplies the colour's own."""
    if isinstance(color, str):
        h = color[1:] if color.startswith('#') else color
        if len(h) in (3, 4):
            h = ''.join(ch * 2 for ch in h)
        try:
            if len(h) not in (6, 8):
                raise ValueError
            r, g, b, *rest = (int(h[i:i + 2], 16) for i in range(0, len(h), 2))
        except ValueError:
            raise ValueError(f"bad colour {color!r}: use '#rgb', '#rgba', '#rrggbb' or '#rrggbbaa'") from None
        a = rest[0] / 255 if rest else 1.0
    else:
        try:
            r, g, b, *rest = color
            if len(rest) > 1:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError(f'bad colour {color!r}: use a hex string or an (r, g, b[, a]) tuple') from None
        a = rest[0] if rest else 1.0
    return r / 255, g / 255, b / 255, a * alpha


def _rounded(ctx, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    if r == 0:
        ctx.rectangle(x, y, w, h)
        return
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


class Image:
    """A decoded bitmap with a mip pyramid, so big captures shrink without aliasing."""

    def __init__(self, path):
        self.path = path
        self._set(PILImage.open(path))

    _cache = {}  # absolute path -> (mtime, Image): one decode per file

    @classmethod
    def load(cls, path):
        """The Image of `path`, decoded once per process and shared after that.
        Call it freely inside `draw`: a big capture is decoded on first use (the
        renderer draws a frame of each chunk before it forks, so workers share
        the pixels), not on every frame. A changed file is decoded again, and
        its old decode dropped."""
        path = os.path.abspath(path)
        stamp = os.stat(path).st_mtime_ns
        hit = cls._cache.get(path)
        if hit is None or hit[0] != stamp:
            hit = cls._cache[path] = stamp, cls(path)
        return hit[1]

    @classmethod
    def from_pil(cls, pil):
        """An Image from a PIL image already in memory (one generated in code, say)."""
        img = cls.__new__(cls)
        img.path = None
        img._set(pil)
        return img

    def _set(self, pil):
        self.w, self.h = pil.size
        self._pil = pil.convert('RGBA' if pil.mode in ('RGBA', 'LA', 'P') else 'RGB')
        self._levels = {}

    def level(self, k):
        """Surface at 1/2^k size (k = 0 is the original)."""
        if k not in self._levels:
            pil = self._pil
            if k:
                pil = pil.reduce(2 ** k)  # box filter: each level averages whole pixel blocks
            self._levels[k] = _surface(pil)
        return self._levels[k]

    def for_scale(self, s):
        """(surface, factor) for drawing at `s` display px per image px."""
        k = 0
        while s * 2 ** (k + 1) <= 1.0 and min(self.w, self.h) >> (k + 1) >= 8:
            k += 1
        return self.level(k), 2 ** k


def _surface(pil):
    w, h = pil.size
    if pil.mode == 'RGBA':
        # cairo wants premultiplied BGRA.
        r, g, b, a = pil.split()
        premul = [ImageChops.multiply(ch, a) for ch in (r, g, b)]
        data = bytearray(PILImage.merge('RGBA', (*premul, a)).tobytes('raw', 'BGRA'))
        fmt = cairo.FORMAT_ARGB32
    else:
        data = bytearray(pil.tobytes('raw', 'BGRX'))
        fmt = cairo.FORMAT_RGB24
    return cairo.ImageSurface.create_for_data(data, fmt, w, h, w * 4)


@lru_cache(maxsize=64)
def _dot_tile(pitch, radius, color):
    size = max(1, round(pitch))
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surf)
    ctx.set_source_rgba(*rgba(color))
    ctx.arc(size / 2, size / 2, radius, 0, 2 * math.pi)
    ctx.fill()
    return surf


def halftone_pattern(pitch, radius, angle=0.0, color='#000'):
    """A cairo pattern of repeating dots (a Ben-Day halftone fill): `pitch` px
    between dot centres, `radius` px dot radius, `angle` radians of rotation,
    `color`. Use it as raw cairo source: `cv.ctx.set_source(vb.halftone_pattern(...))`
    then `cv.ctx.fill()` or `.paint()` within a clip -- there is no image-to-halftone
    conversion, only this generated dot fill."""
    pat = cairo.SurfacePattern(_dot_tile(pitch, radius, color))
    pat.set_extend(cairo.EXTEND_REPEAT)
    pat.set_filter(cairo.FILTER_GOOD)
    if angle:
        m = cairo.Matrix()
        m.rotate(angle)
        pat.set_matrix(m)
    return pat


@lru_cache(maxsize=8)
def _grain_surface(width, height, seed):
    rnd = random.Random(seed)

    def noise(w, h):
        return PILImage.frombytes('L', (w, h), rnd.randbytes(w * h))
    fine = noise(width, height).filter(ImageFilter.GaussianBlur(0.6))
    # Fibres: noise stretched along x, then turned, so short streaks run both ways.
    fx = noise(max(1, width // 7), height).resize((width, height), PILImage.BICUBIC)
    fy = noise(width, max(1, height // 7)).resize((width, height), PILImage.BICUBIC)
    fibres = PILImage.blend(fx, fy, 0.5)
    mottle = noise(max(2, width // 90), max(2, height // 90)).resize((width, height), PILImage.BICUBIC)
    mottle = mottle.filter(ImageFilter.GaussianBlur(12))
    g = PILImage.blend(PILImage.blend(fine, fibres, 0.3), mottle, 0.12)
    # Blending flattens the spread; stretch it back out about its own mean, re-centred on 128.
    mean = ImageStat.Stat(g).mean[0]
    g = g.point(lambda v: max(0, min(255, round(128 + (v - mean) * 3.0))))
    return _surface(PILImage.merge('RGB', (g, g, g)))


def paper_grain(width, height, seed=0):
    """A cairo pattern of paper texture -- fine grain, short fibres and a soft
    mottle -- as grey centred on mid-grey (128), so it brightens and darkens
    whatever it lands on. Paint it with a light-blending operator, within a
    clip for one piece: `cv.ctx.set_source(vb.paper_grain(cv.width, cv.height,
    seed=1))`, `cv.ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)`,
    `cv.ctx.paint_with_alpha(0.5)`, then set `cairo.OPERATOR_OVER` back. The
    texture is generated once per (width, height, seed) and cached; it tiles
    beyond its size."""
    pat = cairo.SurfacePattern(_grain_surface(int(width), int(height), seed))
    pat.set_extend(cairo.EXTEND_REPEAT)
    pat.set_filter(cairo.FILTER_GOOD)
    return pat


def _a8(m):
    """An 'L' PIL image -> a cairo A8 surface (A8 rows are padded to a stride)."""
    W, H = m.size
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8, W)
    raw = m.tobytes()
    data = bytearray(stride * H)
    for row in range(H):
        data[row * stride:row * stride + W] = raw[row * W:(row + 1) * W]
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_A8, W, H, stride)


@lru_cache(maxsize=128)
def _shape_shadow_mask(points, blur):
    """Blurred alpha of a closed polygon, padded so the blur has room. Returns
    (surface, x, y): where the surface's top-left corner goes."""
    sigma = blur / 2  # CSS: blur radius = 2 sigma
    pad = int(math.ceil(3 * sigma)) + 2
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, y0 = math.floor(min(xs)) - pad, math.floor(min(ys)) - pad
    W, H = math.ceil(max(xs)) - x0 + pad, math.ceil(max(ys)) - y0 + pad
    m = PILImage.new('L', (W * 2, H * 2), 0)
    ImageDraw.Draw(m).polygon([((x - x0) * 2, (y - y0) * 2) for x, y in points], fill=255)
    m = m.resize((W, H), PILImage.BOX)  # 2x supersampled edge
    if sigma > 0:
        m = m.filter(ImageFilter.GaussianBlur(sigma))
    return _a8(m), x0, y0


@lru_cache(maxsize=256)
def _shadow_mask(w, h, radius, blur, spread):
    """Blurred alpha of a rounded box, padded so the blur has room. Returns (surface, pad)."""
    sigma = blur / 2  # CSS: blur radius = 2 sigma
    pad = int(math.ceil(3 * sigma + max(0, spread))) + 2
    W, H = int(w) + 2 * pad, int(h) + 2 * pad
    m = PILImage.new('L', (W * 4, H * 4), 0)
    x0, y0 = (pad - spread) * 4, (pad - spread) * 4
    x1, y1 = (pad + w + spread) * 4, (pad + h + spread) * 4
    r = max(0, radius + spread) * 4
    ImageDraw.Draw(m).rounded_rectangle((x0, y0, x1 - 1, y1 - 1), radius=r, fill=255)
    m = m.resize((W, H), PILImage.BOX)  # 4x supersampled edge
    if sigma > 0:
        m = m.filter(ImageFilter.GaussianBlur(sigma))
    return _a8(m), pad


class Canvas:
    """A frame to draw on, `width` x `height` in film px.

    `scale` shrinks the pixels, not the coordinates: a preview at 0.5 draws
    the same calls into a half-size surface. `format` is the film format being
    drawn (see `videobuilder.film.Format`), for per-format layout.
    """

    def __init__(self, width, height, background=None, scale=1.0, format=None):
        self.width, self.height = width, height
        self.format = format
        self.scale = scale
        self.marks = []  # (name, Box) pairs from `mark`, in frame px
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, max(1, round(width * scale)),
                                          max(1, round(height * scale)))
        self.ctx = cairo.Context(self.surface)
        if scale != 1:
            self.ctx.scale(scale, scale)
        if background:
            self.fill(background)

    # ---- primitives ----
    def fill(self, color, alpha=1.0):
        self.ctx.set_source_rgba(*rgba(color, alpha))
        self.ctx.paint()

    def rect(self, x, y, w, h, color, radius=0, alpha=1.0):
        c = self.ctx
        _rounded(c, x, y, w, h, radius)
        c.set_source_rgba(*rgba(color, alpha))
        c.fill()

    def outline(self, x, y, w, h, color, width=1, radius=0, alpha=1.0):
        """Stroke the edge of the box (x, y, w, h), `width` px wide and centred on
        it (half inside, half out), with corner `radius`."""
        c = self.ctx
        _rounded(c, x, y, w, h, radius)
        c.set_source_rgba(*rgba(color, alpha))
        c.set_line_width(width)
        c.stroke()

    def line(self, x0, y0, x1, y1, color, width=1, alpha=1.0):
        """A straight line from (x0, y0) to (x1, y1), with butt ends."""
        c = self.ctx
        c.move_to(x0, y0)
        c.line_to(x1, y1)
        c.set_source_rgba(*rgba(color, alpha))
        c.set_line_width(width)
        c.stroke()

    def arc(self, cx, cy, r, a0, a1, color, width=1, alpha=1.0):
        """Stroke a circular arc with butt ends; angles in radians, increasing
        clockwise in canvas coordinates, from the positive x axis."""
        c = self.ctx
        c.new_path()
        c.arc(cx, cy, r, a0, a1)
        c.set_source_rgba(*rgba(color, alpha))
        c.set_line_width(width)
        c.stroke()

    def sector(self, cx, cy, r, a0, a1, color, alpha=1.0):
        """Fill a pie sector; angles use the same convention as `arc`."""
        c = self.ctx
        c.new_path()
        c.move_to(cx, cy)
        c.arc(cx, cy, r, a0, a1)
        c.close_path()
        c.set_source_rgba(*rgba(color, alpha))
        c.fill()

    def image(self, img, x, y, w, h, alpha=1.0):
        """Draw `img` stretched to the box (x, y, w, h). Mip level picked by scale."""
        c = self.ctx
        s = min(w / img.w, h / img.h) * self.scale_factor()
        surf, f = img.for_scale(s)
        c.save()
        c.translate(x, y)
        c.scale(w / img.w * f, h / img.h * f)
        c.set_source_surface(surf, 0, 0)
        pat = c.get_source()
        pat.set_filter(cairo.FILTER_GOOD)
        pat.set_extend(cairo.EXTEND_PAD)
        c.rectangle(0, 0, surf.get_width(), surf.get_height())
        c.clip()
        c.paint_with_alpha(alpha)
        c.restore()

    def shadow(self, x, y, w, h, radius=0, dx=0, dy=0, blur=0, spread=0, color=(0, 0, 0, 0.5)):
        """CSS box-shadow of the box (x, y, w, h), drawn under it."""
        mask, pad = _shadow_mask(round(w), round(h), radius, blur, spread)
        c = self.ctx
        c.set_source_rgba(*rgba(color))
        c.mask_surface(mask, x + dx - pad, y + dy - pad)

    def shape_shadow(self, points, dx=0, dy=0, blur=0, color=(0, 0, 0, 0.5)):
        """A soft drop shadow that follows the closed point list `points` (a
        torn scrap, a cut-out's outline) instead of a box: `shadow`'s free-form
        sibling, drawn under the shape. The blurred mask is made once per
        shape and `blur` and cached, so a piece that only moves -- inside a
        `layer` or a cairo transform -- blurs once, not every frame."""
        if len(points) < 3:
            return
        key = tuple((round(x * 4) / 4, round(y * 4) / 4) for x, y in points)
        mask, x0, y0 = _shape_shadow_mask(key, float(blur))
        c = self.ctx
        c.set_source_rgba(*rgba(color))
        c.mask_surface(mask, x0 + dx, y0 + dy)

    def scale_factor(self):
        """Current user->device scale (for mip selection under a scaled layer)."""
        xx, yx, xy, yy, _, _ = self.ctx.get_matrix()
        return math.sqrt(abs(xx * yy - xy * yx))

    def mark(self, name, x, y, w, h):
        """Tag the box (x, y, w, h) as content named `name`, for checks run on the
        finished frame (a safe area, overlaps). The box is recorded where it lands
        in the frame, through any `layer` moves and scales, and only if it can be
        seen: a mark inside an invisible layer or an empty clip is skipped.
        Returns the recorded Box, or None. Drawing nothing, it costs nothing."""
        c = self.ctx
        x0, y0, x1, y1 = c.clip_extents()
        if x1 <= x0 or y1 <= y0:
            return None
        pts = [c.user_to_device(px, py) for px, py in ((x, y), (x + w, y), (x, y + h), (x + w, y + h))]
        xs, ys = [p[0] / self.scale for p in pts], [p[1] / self.scale for p in pts]
        box = Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
        self.marks.append((name, box))
        return box

    def view(self, img, box, center=None, scale=None, radius=0, background=None):
        """Show `img` through the window `box` with a camera: the image point
        `center` (image px; default the image's centre) at the box's centre,
        `scale` display px per image px (default: cover the box). Pan by moving
        `center`, zoom by changing `scale`. Clipped to the box, with corner
        `radius`; `background` fills the box first. Returns the `View`, whose
        `pin` places a part of this or another image in the same window."""
        box = Box(*box)
        cx, cy = center if center is not None else (img.w / 2, img.h / 2)
        s = scale if scale is not None else max(box.w / img.w, box.h / img.h)
        v = View(self, img, box, cx, cy, s, radius)
        with self.clip(*box, radius):
            if background is not None:
                self.rect(*box, background)
            self.image(img, v.left, v.top, img.w * s, img.h * s)
        return v

    # ---- structure ----
    @contextmanager
    def layer(self, opacity=1.0, dx=0.0, dy=0.0, scale=1.0):
        """A group: children draw translated/scaled, then composite at `opacity`."""
        c = self.ctx
        if opacity <= 0:
            # Invisible: run the body against an empty clip, which cairo skips cheaply,
            # but with the same transform, so code that asks where things are still knows.
            c.save()
            c.rectangle(0, 0, 0, 0)
            c.clip()
            c.translate(dx, dy)
            if scale != 1:
                c.scale(scale, scale)
            try:
                yield self
            finally:
                c.restore()
            return
        group = opacity < 1
        c.save()
        if group:
            c.push_group()
        c.translate(dx, dy)
        if scale != 1:
            c.scale(scale, scale)
        try:
            yield self
        finally:
            if group:
                c.pop_group_to_source()
                c.paint_with_alpha(opacity)
            c.restore()

    @contextmanager
    def clip(self, x, y, w, h, radius=0):
        c = self.ctx
        c.save()
        _rounded(c, x, y, w, h, radius)
        c.clip()
        try:
            yield self
        finally:
            c.restore()

    @contextmanager
    def pixelated(self, factor, x=0.0, y=0.0, w=None, h=None, background=None):
        """A group drawn at 1/`factor` resolution over the region (x, y, w, h)
        (default the whole frame) and painted back with nearest-neighbour
        filtering: a blocky pixel-art look. The body draws with the *yielded*
        Canvas (not `self`), in the same logical coordinates as that region,
        so a film not using this draws exactly as before; any text or image
        drawn into it pixelates along with everything else. `factor` need
        not be a whole number."""
        w = self.width if w is None else w
        h = self.height if h is None else h
        # Oversize the sub-canvas to a whole number of device pixels (ceil, not
        # round) so it fully covers (w, h) after scaling back up -- a plain
        # round can land short, leaving an unpainted strip at the right/bottom
        # edge when w/factor or h/factor isn't a whole number.
        from . import text as _text  # deferred: text imports from this module
        px_w, px_h = math.ceil(w / factor), math.ceil(h / factor)
        sub = Canvas(px_w * factor, px_h * factor, background=background, scale=1.0 / factor, format=self.format)
        sub.ctx.set_antialias(cairo.ANTIALIAS_NONE)
        try:
            with _text.antialias(cairo.ANTIALIAS_NONE):
                yield sub
        finally:
            sub.surface.flush()
            c = self.ctx
            c.save()
            c.translate(x, y)
            c.scale(factor, factor)
            c.set_source_surface(sub.surface, 0, 0)
            c.get_source().set_filter(cairo.FILTER_NEAREST)
            # Clip to the requested region, not the (possibly oversized) sub-canvas.
            c.rectangle(0, 0, w / factor, h / factor)
            c.clip()
            c.paint()
            c.restore()

    # ---- output ----
    def bgra(self):
        self.surface.flush()
        return bytes(self.surface.get_data())

    def save_png(self, path):
        self.surface.write_to_png(path)


class View:
    """A camera on an image in a window (see `Canvas.view`). `left`, `top`: where
    the image's top-left corner lands; `to_screen` maps any image point."""

    def __init__(self, canvas, img, box, cx, cy, scale, radius=0):
        self.canvas, self.img, self.box, self.scale, self.radius = canvas, img, box, scale, radius
        self.center = cx, cy
        self.left = box.x + box.w / 2 - cx * scale
        self.top = box.y + box.h / 2 - cy * scale

    def to_screen(self, px, py):
        """Where the image point (px, py) lands, in canvas px."""
        return self.left + px * self.scale, self.top + py * self.scale

    def image_box(self):
        """Where the whole image lands (most of it clipped away, usually)."""
        return Box(self.left, self.top, self.img.w * self.scale, self.img.h * self.scale)

    def pin(self, src, img=None, x=None, y=None):
        """Draw the part `src` (a Box in image px) of `img` (default: this view's
        image) at the view's scale, inside the window. Its top-left goes to (x, y)
        in canvas px; either left as None stays where the camera puts that point
        of the page, so `y=view.box.y` alone pins a strip (a navbar, say) to the
        window's top while it still pans sideways with the page."""
        img = img or self.img
        s = self.scale
        sx, sy = self.to_screen(src.x, src.y)
        x = sx if x is None else x
        y = sy if y is None else y
        cv = self.canvas
        with cv.clip(*self.box, self.radius), cv.clip(x, y, src.w * s, src.h * s):
            cv.image(img, x - src.x * s, y - src.y * s, img.w * s, img.h * s)
