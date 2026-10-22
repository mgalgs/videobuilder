"""Atkinson dithering: a picture turned into two inks by error diffusion that
passes on only three quarters of each pixel's rounding error. Midtones become
a fine, even stipple, while highlights blow out clean and shadows fill solid.
The result is the crisp, high-contrast 1-bit look of early desktop computers.
`looks.fx.posterize(dither=True)` diffuses all of the error (Floyd-Steinberg);
this one keeps Atkinson's lighter, punchier pattern."""
from PIL import Image, ImageOps

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# Atkinson's kernel: 1/8 of the error to each of six neighbours (x, y offsets),
# so 2/8 of it is simply dropped.
KERNEL = ((1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2))


def atkinson(im, cell=4, threshold=128, dark='#1b1b1f', light='#f1ede4'):
    """`im` (a PIL image) Atkinson-dithered to two colours, as a PIL RGB image
    the same size. The picture is sampled on a grid of `cell`-px squares, so
    each dither dot is `cell` px wide and stays hard-edged; `threshold` (0-255
    grey) splits dark from light, and `dark` / `light` are the two inks."""
    w, h = im.size
    gw, gh = max(1, round(w / cell)), max(1, round(h / cell))
    grey = list(im.convert('L').resize((gw, gh), Image.Resampling.BOX).getdata())
    px = [float(v) for v in grey]
    out = bytearray(gw * gh)
    for y in range(gh):
        row = y * gw
        for x in range(gw):
            i = row + x
            old = px[i]
            new = 255 if old >= threshold else 0
            out[i] = new
            err = (old - new) / 8
            for dx, dy in KERNEL:
                nx, ny = x + dx, y + dy
                if 0 <= nx < gw and ny < gh:
                    px[ny * gw + nx] += err
    q = Image.frombytes('L', (gw, gh), bytes(out)).resize((w, h), Image.Resampling.NEAREST)
    return ImageOps.colorize(q, dark, light)


_CACHE = {}  # (id of the source, size, options) -> (source, original, dithered)


def draw_atkinson(cv, pil, x, y, w, h, p=1.0, line=demo.ACCENT, **kw):
    """Draw the PIL image `pil` in the box (x, y, w, h) with its Atkinson-dithered
    version (`kw` goes to `atkinson`) sweeping in from the left behind a
    vertical wipe at progress `p`: all original at 0, all dithered at 1. `line`
    (None for none) marks the wipe's edge. The dither is worked out at the
    drawn size, so dots stay `cell` px on screen, and is made once per image,
    size and options. Returns the box."""
    key = (id(pil), round(w), round(h), tuple(sorted(kw.items())))
    if key not in _CACHE:
        if len(_CACHE) >= 8:
            _CACHE.clear()
        sized = pil.convert('RGB').resize(key[1:3], Image.Resampling.LANCZOS)
        _CACHE[key] = pil, vb.Image.from_pil(pil), vb.Image.from_pil(atkinson(sized, **kw))
    _, original, dithered = _CACHE[key]
    p = vb.clamp01(p)
    if p < 1:
        cv.image(original, x, y, w, h)
    if p > 0:
        edge = x + w * p
        with cv.clip(x, y, edge - x, h):
            cv.image(dithered, x, y, w, h)
        if line and p < 1:
            cv.rect(edge - 3, y, 6, h, line)
    return vb.Box(x, y, w, h)


_PHOTO = []


def _photo():
    if not _PHOTO:
        from ...compendium import kit
        _PHOTO.append(kit._sample_photo())
    return _PHOTO[0]


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.5, 2.2))
    photo = _photo()
    draw_atkinson(cv, photo, *vb.Box.of(cv).cover(*photo.size), p, cell=6)
    cv.mark('photo', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='atkinson-dithering',
    name='Atkinson dithering',
    family='vfx',
    group='Dithering & quantization',
    aliases=('Atkinson dither', '1-bit dither', 'classic Mac dither', 'bitmap dither'),
    definition='A picture is reduced to just two colours by scattering black and white dots whose density '
               'follows its tones, with bright areas washing out clean and dark ones going solid.',
    phrasings=('make the photo look like an old black-and-white Macintosh screen',
               'turn the image into crisp 1-bit dots, retro computer style',
               'a dithered two-tone version of the picture with chunky pixels'),
    related=('blur-up-image-load', 'gradient-wipe', 'desaturation', 'blur-dissolve', 'unsharp-mask',
             'gradient-mesh-drift'),
    api=('videobuilder.capabilities.vfx.atkinson_dithering.atkinson',
         'videobuilder.capabilities.vfx.atkinson_dithering.draw_atkinson'),
    demo=lambda: demo.film(draw),
)
