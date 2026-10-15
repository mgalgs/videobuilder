"""Shared look for the seed components: a palette, generic font families (no
bundled font file -- fontconfig's own sans-serif/monospace, so the compendium
ships no binary asset and no new dependency), the preview formats, and a
couple of small drawing helpers. A component is free to ignore all of this;
it's here so the seed set reads as one family.
"""
import random

from PIL import Image as PILImage

import videobuilder as vb

BG = '#14151a'
INK = '#f4f4f2'
MUTED = '#9397a1'
ACCENT = '#ef5b4c'
TEAL = '#4fc3b0'
LINE = '#2a2c33'

SANS = 'sans-serif'
MONO = 'monospace'

# All three share a short side of 540px, so one set of pixel constants reads
# the same in every format (the showcase does the same trick at 720px).
F16 = vb.Format('16x9', 960, 540)
F9 = vb.Format('9x16', 540, 960)
F1 = vb.Format('1x1', 540, 540)
FORMATS = {'16x9': F16, '9x16': F9, '1x1': F1}

# The tempo a lone component previews at, absent a recipe's own.
GRID = vb.Grid(fps=30, bpm=120)


def font(size, weight=400, **kw):
    return vb.Font(SANS, size, weight=weight, **kw)


def mono(size, weight=500, **kw):
    return vb.Font(MONO, size, weight=weight, **kw)


def safe(cv, pad=48):
    return vb.Box.of(cv).pad(pad)


def mix(c0, c1, t):
    a, b = vb.rgba(c0), vb.rgba(c1)
    return tuple(255 * (x + (y - x) * t) for x, y in zip(a[:3], b[:3]))


def _sample_photo(w=640, h=420, seed=11):
    """A seeded procedural 'photo' -- a sky gradient, a sun and a couple of
    hills -- drawn in code so no binary image asset ships with the package."""
    rnd = random.Random(seed)
    top, bottom = (31, 94, 86), (233, 142, 88)
    grad = PILImage.new('RGB', (1, h))
    for y in range(h):
        t = y / (h - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    img = grad.resize((w, h)).convert('RGBA')

    from PIL import ImageDraw
    overlay = PILImage.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    sx, sy, sr = w * 0.72, h * 0.3, w * 0.11
    d.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=(255, 219, 168, 190))
    img = PILImage.alpha_composite(img, overlay)

    d = ImageDraw.Draw(img)
    for cx_f, base_r, tone in ((0.18, 0.3, (18, 48, 44)), (0.55, 0.34, (23, 60, 55)), (0.88, 0.26, (15, 40, 38))):
        jitter = 1 + 0.08 * (rnd.random() - 0.5)
        cx, r = w * cx_f, w * base_r * jitter
        cy = h * 0.86
        d.ellipse((cx - r, cy - r * 0.6, cx + r, cy + r * 1.4), fill=tone)
    return img.convert('RGB')


_PHOTO = None


def sample_photo():
    """A shared `vb.Image` sample, built once and reused by every preview."""
    global _PHOTO
    if _PHOTO is None:
        _PHOTO = vb.Image.from_pil(_sample_photo())
    return _PHOTO
