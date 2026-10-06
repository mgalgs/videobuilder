"""Layers and compositing on cairo: rects, images, clips, shadows, groups.

Immediate mode: a frame function draws into a fresh Canvas, back to front.
Groups (`layer`) carry opacity and a transform, like a CSS stacking context.
"""
import math
from contextlib import contextmanager
from functools import lru_cache

import cairo
from PIL import Image as PILImage, ImageChops, ImageDraw, ImageFilter


def rgba(color, alpha=1.0):
    """'#RRGGBB' or an (r, g, b[, a]) tuple of 0-255 / 0-1 alpha -> cairo floats."""
    if isinstance(color, str):
        h = color.lstrip('#')
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        a = 1.0
    else:
        r, g, b, *rest = color
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
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8, W)
    raw = m.tobytes()
    data = bytearray(stride * H)
    for row in range(H):
        data[row * stride:row * stride + W] = raw[row * W:(row + 1) * W]
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_A8, W, H, stride), pad


class Canvas:
    """A frame to draw on, `width` x `height` in film px.

    `scale` shrinks the pixels, not the coordinates: a preview at 0.5 draws
    the same calls into a half-size surface. `format` is the film format being
    drawn (see `videobuilder.film.Format`), for per-format layout.
    """

    def __init__(self, width, height, background=None, scale=1.0, format=None):
        self.width, self.height = width, height
        self.format = format
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

    def scale_factor(self):
        """Current user->device scale (for mip selection under a scaled layer)."""
        xx, yx, xy, yy, _, _ = self.ctx.get_matrix()
        return math.sqrt(abs(xx * yy - xy * yx))

    # ---- structure ----
    @contextmanager
    def layer(self, opacity=1.0, dx=0.0, dy=0.0, scale=1.0):
        """A group: children draw translated/scaled, then composite at `opacity`."""
        c = self.ctx
        if opacity <= 0:
            # Invisible: run the body against an empty clip, which cairo skips cheaply.
            c.save()
            c.rectangle(0, 0, 0, 0)
            c.clip()
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

    # ---- output ----
    def bgra(self):
        self.surface.flush()
        return bytes(self.surface.get_data())

    def save_png(self, path):
        self.surface.write_to_png(path)
