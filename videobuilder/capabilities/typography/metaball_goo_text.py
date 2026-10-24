"""Metaball Goo Text: the same idea as Gooey filter
(`../particles/gooey_filter.py`), which keeps the capability -- both call
`goo` to blur shapes together and cut them back to a hard edge so nearby
ones fuse, this one flowing letters into one liquid word with a stretching
neck between them. This module's own code stays (a film may still import
it), but it is no longer a capability of its own."""
import math

import cairo
from PIL import Image as PILImage, ImageFilter

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'gooey-filter'


def _a8(m):
    """An 'L' PIL image -> a cairo A8 surface (A8 rows are padded to a stride)."""
    w, h = m.size
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8, w)
    raw = m.tobytes()
    data = bytearray(stride * h)
    for row in range(h):
        data[row * stride:row * stride + w] = raw[row * w:(row + 1) * w]
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_A8, w, h, stride)


def goo(cv, shapes, color, blur=12, cut=0.5, soft=0.06, box=None, alpha=1.0, quality=0.5):
    """Paint whatever `shapes(sub)` draws as one gooey mass in `color`.
    `shapes` draws into a scratch Canvas `sub` (same film coordinates, any
    colour, only coverage counts); the coverage is blurred by `blur` film px,
    and everything above `cut` (0 -> 1) is filled, its edge `soft` wide.
    Shapes within about `blur` of each other fuse; a larger `blur` makes
    rounder letters and longer necks, a higher `cut` thinner ones. `box`
    limits the work to (x, y, w, h) (default the whole frame); `quality` is
    the scratch resolution relative to the frame."""
    x, y, w, h = box if box is not None else (0, 0, cv.width, cv.height)
    s = max(0.05, cv.scale_factor() * quality)
    sub = vb.Canvas(w, h, scale=s)
    sub.ctx.translate(-x, -y)
    shapes(sub)
    sub.surface.flush()
    sw, sh = sub.surface.get_width(), sub.surface.get_height()
    cover = PILImage.frombuffer('RGBA', (sw, sh), bytes(sub.surface.get_data()), 'raw', 'BGRA',
                                sub.surface.get_stride(), 1).getchannel('A')
    if blur > 0:
        cover = cover.filter(ImageFilter.GaussianBlur(blur * s / 2))
    lo, hi = 255 * (cut - soft / 2), 255 * (cut + soft / 2)
    lut = [round(255 * vb.clamp01((v - lo) / max(1e-6, hi - lo))) for v in range(256)]
    mask = _a8(cover.point(lut))
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.scale(1 / s, 1 / s)
    c.set_source_rgba(*vb.rgba(color, alpha))
    c.mask_surface(mask, 0, 0)
    c.restore()


def goo_text(cv, letters, font, color, blur=12, cut=0.5, **kw):
    """Draw `letters`, a list of `(char, cx, cy)` placed by their centres, as
    gooey type: letters that come close melt together. Move the centres
    from frame to frame to make them flow. `kw` goes to `goo`. Returns the
    Box around the letters' centres padded by the font size."""
    def shapes(sub):
        for ch, cx, cy in letters:
            demo.word(sub, ch, cx, cy, font=font, color='#ffffff')
    goo(cv, shapes, color, blur=blur, cut=cut, **kw)
    xs, ys = [cx for _, cx, _ in letters], [cy for _, _, cy in letters]
    pad = font.size * 0.6
    return vb.Box(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)


TEXT = 'GOOEY'


def _smooth(x):
    """Ease in and out, 0 -> 1."""
    return x * x * (3 - 2 * x)


def draw(n, cv):
    f = demo.font(118, 900)
    t = n / demo.FPS
    advs = [vb.text.measure(ch, f) for ch in TEXT]
    total = sum(advs)
    # Spread far apart, flow together until they touch and fuse into one
    # word, then tug the word in two between the O and the E: a neck forms,
    # thins and snaps, and the halves flow back and fuse again.
    gather = vb.ease_in_out_quart(demo.phase(n, 0.1, 1.1))
    spread = 1.6 * (1 - gather) + 0.97 * gather
    gap = 72 * (_smooth(demo.phase(n, 1.55, 2.4)) - _smooth(demo.phase(n, 2.45, 2.92)))
    letters, left = [], demo.W / 2 - total * spread / 2
    for i, (ch, adv) in enumerate(zip(TEXT, advs)):
        cx = left + adv * spread / 2 + (gap / 2 if i >= 3 else -gap / 2)
        cy = demo.H / 2 + 26 * math.sin(2.4 * t + i * 1.7) * (1 - 0.75 * gather) + 6 * math.sin(4.1 * t + i)
        letters.append((ch, cx, cy))
        left += adv * spread
    # Two droplets are drawn in, stretch toward the word and are swallowed.
    blobs = [(demo.W / 2 - 90, demo.H / 2 - 190 + 160 * _smooth(demo.phase(n, 0.6, 1.4)), 17),
             (demo.W / 2 + 150, demo.H / 2 + 180 - 150 * _smooth(demo.phase(n, 0.9, 1.7)), 13)]
    # The neck between the O and the E: a strand of goo that thins in the
    # middle as the halves pull apart, pinches off, and its two stubs recoil
    # into the letters.
    neck = []
    if 1.55 < t < 2.45:
        k = gap / 72
        (_, ox, oy), (_, ex, ey) = letters[2], letters[3]
        a, b = ox + 0.3 * advs[2], ex - 0.25 * advs[3]
        mid, edge = 13 * vb.clamp01(1 - k / 0.9), 13 * vb.clamp01((1 - k) / 0.1)
        for j in range(17):
            u = j / 16
            r = mid + (edge - mid) * (2 * abs(u - 0.5)) ** 2
            if r > 0.5:
                neck.append((a + (b - a) * u, oy + (ey - oy) * u, r))

    def shapes(sub):
        for ch, cx, cy in letters:
            demo.word(sub, ch, cx, cy, font=f, color='#ffffff')
        for bx, by, r in blobs + neck:
            demo.dot(sub, bx, by, r, color='#ffffff')
    goo(cv, shapes, demo.ACCENT, blur=13, cut=0.5)
    cv.mark('text', demo.W / 2 - total * spread / 2 - gap / 2, demo.H / 2 - 70, total * spread + gap, 140)
