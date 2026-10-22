"""Metaball Goo Text: letters drawn as soft blobs that fuse into one liquid
shape where they come close and pull apart with a stretching neck. The look
is the classic blur-then-threshold trick: the shapes are blurred together,
and only the part above a cut-off is painted, with a crisp edge."""
import math

import cairo
from PIL import Image as PILImage, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


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


def draw(n, cv):
    f = demo.font(118, 900)
    t = n / demo.FPS
    advs = [vb.text.measure(ch, f) for ch in TEXT]
    total = sum(advs)
    # Spread far apart, flow together until they overlap and fuse, then ease
    # back to a snug word that keeps wobbling, so necks form and break.
    gather = vb.ease_in_out_quart(demo.phase(n, 0.2, 1.4))
    squeeze = math.sin(math.pi * demo.phase(n, 1.1, 2.3))
    spread = 1.6 * (1 - gather) + 0.9 * gather - 0.22 * squeeze
    letters, left = [], demo.W / 2 - total * spread / 2
    for i, (ch, adv) in enumerate(zip(TEXT, advs)):
        cx = left + adv * spread / 2
        cy = demo.H / 2 + 26 * math.sin(2.4 * t + i * 1.7) * (1 - 0.6 * gather) + 8 * math.sin(4.1 * t + i)
        letters.append((ch, cx, cy))
        left += adv * spread
    # Two droplets fall into the word and are swallowed.
    drop = demo.phase(n, 1.3, 2.4)
    blobs = [(demo.W / 2 - 90, demo.H / 2 - 190 + 160 * vb.ease_in_expo(drop), 17),
             (demo.W / 2 + 130, demo.H / 2 + 180 - 150 * vb.ease_in_expo(demo.phase(n, 1.5, 2.6)), 13)]

    def shapes(sub):
        for ch, cx, cy in letters:
            demo.word(sub, ch, cx, cy, font=f, color='#ffffff')
        for bx, by, r in blobs:
            demo.dot(sub, bx, by, r, color='#ffffff')
    goo(cv, shapes, demo.ACCENT, blur=13, cut=0.5)
    cv.mark('text', demo.W / 2 - total * spread / 2, demo.H / 2 - 70, total * spread, 140)


TECHNIQUE = Technique(
    id='metaball-goo-text',
    name='Metaball goo text',
    family='typography',
    group='Liquid and organic',
    aliases=('gooey text', 'metaball merge', 'liquid merge text', 'goo effect'),
    definition='Letters behave like drops of thick liquid, so when two drift close their outlines '
               'bulge and fuse into one blob, and stretch a neck before snapping apart.',
    phrasings=('make the letters gloopy so they melt into each other when they touch',
               'liquid blobby type where the characters merge together like droplets',
               'the word flows together like goo and the letters stick to each other'),
    related=('liquid-morph', 'particle-text-formation', 'dissolve-to-particles', 'gooey-filter',
             'type-explosion', 'noise-dissolve'),
    api=('videobuilder.techniques.typography.metaball_goo_text.goo_text',
         'videobuilder.techniques.typography.metaball_goo_text.goo'),
    demo=lambda: demo.film(draw),
)
