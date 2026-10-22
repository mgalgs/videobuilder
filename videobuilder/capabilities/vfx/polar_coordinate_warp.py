"""Polar coordinate warp: a flat, wide picture bends round until its two side
edges meet, turning it into a disc -- the bottom edge squeezed to a point in
the middle and the top edge stretched round the rim (a "little planet"), or
the other way out (a tunnel).

It is a per-pixel inverse remap. At `amount` k the picture is a ring sector
spanning 2*pi*k radians, its top edge growing from the flat width to the
disc's circumference and its height from the flat height to the disc's
radius, so k = 0 is the picture untouched and k = 1 the closed disc, and
every step between is a clean bend. Pillow only, worked out at a small size
the canvas scales up.
"""
import math
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _lerp(a, b, t):
    return a + (b - a) * t


def polar_warp_image(src, size, amount, flat=None, center=None, radius=None, spin=0.0, inside_out=False):
    """`src` (a PIL image, ideally a panorama that wraps left to right) warped
    towards polar coordinates, as a PIL RGBA image of `size` (w, h) with
    transparency wherever the picture doesn't reach.

    `amount`: 0 is the picture flat in the `flat` box (x, y, w, h; default
    the full width, centred), 1 the closed disc of `radius` (default 0.45 of
    the height) about `center` (default the middle), bottom edge at the
    centre. `spin`: turns the picture runs round the disc (it scrolls
    sideways while still flat). `inside_out`: the top edge goes to the
    centre and the bottom round the rim, and the picture bends upwards."""
    w, h = size
    if inside_out:
        src = src.transpose(Image.FLIP_TOP_BOTTOM)
    src = src.convert('RGB')
    sw, sh = src.size
    pix = src.load()
    k = vb.clamp01(amount)
    if flat is None:
        fh = w * sh / sw
        flat = (0, (h - fh) / 2, w, fh)
    fx, fy, fw, fh = flat
    cx, cy = center or (w / 2, h / 2)
    if inside_out:
        fy, cy = h - fy - fh, h - cy
    R = radius or 0.45 * h
    span = 2 * math.pi * k
    top = _lerp(fy, cy - R, k)
    tall = _lerp(fh, R, k)
    mid = _lerp(fx + fw / 2, cx, k)
    bent = span > 1e-3
    if bent:
        rho_top = _lerp(fw, 2 * math.pi * R, k) / span
        by = top + rho_top
    out = bytearray(w * h * 4)
    for y in range(h):
        py = y + 0.5
        row = y * 4 * w
        for x in range(w):
            px = x + 0.5
            if bent:
                dx, dy = px - mid, py - by
                rho = math.hypot(dx, dy)
                a = math.atan2(dx, -dy)
                u = a / span + 0.5
                v = (rho_top - rho) / tall
                edge_u = (span / 2 - abs(a)) * rho  # px to the side edges
            else:
                u = (px - fx) / fw
                v = (py - top) / tall
                edge_u = min(u, 1 - u) * fw
            edge_v = min(v, 1 - v) * tall
            cover = min(edge_u, edge_v) + 0.5
            if cover <= 0:
                continue
            uu = (u + spin) % 1.0
            vv = min(max(v, 0.0), 0.999999)
            r, g, b = pix[int(uu * sw) % sw, int(vv * sh)]
            i = row + 4 * x
            out[i:i + 4] = bytes((r, g, b, 255 if cover >= 1 else int(255 * cover)))
    im = Image.frombytes('RGBA', (w, h), bytes(out))
    if inside_out:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    return im


def polar_warp(cv, src, amount, box=None, res=640, **kw):
    """Draw `src` (a PIL image or `vb.Image`) polar-warped by `amount` (0 flat
    -> 1 a closed disc) into `box` (x, y, w, h; default the whole canvas),
    worked out `res` pixels wide and scaled up smoothly. `kw` goes to
    `polar_warp_image` (`spin`, `inside_out`, `radius`, `center`, `flat`, all
    in `res`-wide pixels). Returns the Box drawn."""
    x, y, w, h = box or (0, 0, cv.width, cv.height)
    res = max(16, min(res, round(w * cv.scale)))
    size = (res, max(2, round(res * h / w)))
    pil = src._pil if isinstance(src, vb.Image) else src
    f = res / w
    for key in ('radius',):
        if kw.get(key) is not None:
            kw[key] = kw[key] * f
    for key in ('center', 'flat'):
        if kw.get(key) is not None:
            kw[key] = tuple(c * f for c in kw[key])
    img = vb.Image.from_pil(polar_warp_image(pil, size, amount, **kw))
    cv.image(img, x, y, w, h)
    return vb.Box(x, y, w, h)


@lru_cache(maxsize=1)
def panorama(w=1024, h=300):
    """A wide landscape that wraps left to right, for the demo: dusk sky,
    a sun, rolling hills and a row of houses and trees on the ground."""
    im = Image.new('RGB', (w, h))
    d = ImageDraw.Draw(im)
    top, low = (38, 44, 96), (236, 150, 120)
    horizon = int(h * 0.76)
    for y in range(horizon):
        t = (y / horizon) ** 1.6
        d.line((0, y, w, y), fill=tuple(round(_lerp(a, b, t)) for a, b in zip(top, low)))
    d.ellipse((w * 0.16 - 34, h * 0.22 - 34, w * 0.16 + 34, h * 0.22 + 34), fill=(255, 196, 84))
    tau = 2 * math.pi
    hills = [(x, horizon - 26 - 22 * math.sin(tau * 3 * x / w) - 12 * math.sin(tau * 5 * x / w + 1))
             for x in range(0, w + 1, 4)]
    d.polygon(hills + [(w, h), (0, h)], fill=(79, 120, 140))
    d.rectangle((0, horizon, w, h), fill=(32, 46, 52))
    for i in range(16):
        x = (i + 0.5) * w / 16
        if i % 3 == 1:
            d.rectangle((x - 3, horizon - 30, x + 3, horizon), fill=(26, 34, 38))
            d.ellipse((x - 20, horizon - 76, x + 20, horizon - 22), fill=(42, 140, 120))
        else:
            bw, bh = 30 + 8 * (i % 2), 46 + 18 * ((i * 7) % 4)
            col = ((239, 91, 76), (244, 244, 242), (240, 190, 90))[i % 3]
            d.rectangle((x - bw / 2, horizon - bh, x + bw / 2, horizon), fill=col)
            d.polygon([(x - bw / 2 - 5, horizon - bh), (x + bw / 2 + 5, horizon - bh), (x, horizon - bh - 22)],
                      fill=(60, 40, 52))
            d.rectangle((x - 6, horizon - 22, x + 6, horizon), fill=(40, 30, 40))
    return im.filter(ImageFilter.GaussianBlur(0.6))


def draw(n, cv):
    t = n / demo.FPS
    k = vb.ease_in_out_quart(demo.phase(n, 0.4, 1.9))
    spin = 0.12 * max(0.0, t - 1.6) ** 2
    fw = demo.W * 0.9
    flat = ((demo.W - fw) / 2, (demo.H - fw * 300 / 1024) / 2, fw, fw * 300 / 1024)
    box = polar_warp(cv, panorama(), k, spin=spin, flat=flat, res=480)
    cv.mark('warp', *box)


TECHNIQUE = Technique(
    id='polar-coordinate-warp',
    name='Polar coordinate warp',
    family='vfx',
    group='Symmetry & geometry',
    aliases=('polar warp', 'little planet', 'polar projection', 'tiny planet', 'rectangular to polar'),
    definition='A wide flat picture curls round until its two ends join, becoming a round disc with its '
               'bottom edge pinched into the middle and its top edge spread round the outside.',
    phrasings=('bend this panorama round into a tiny planet',
               'wrap the landscape into a circle so the ground is in the middle',
               'curl the wide shot into a ring, like a fisheye globe'),
    related=('look-around', 'lens-distortion', 'projection-morph', 'refraction-ripple', 'elastic-stretch',
             'zoom-blur'),
    api=('videobuilder.techniques.vfx.polar_coordinate_warp.polar_warp',
         'videobuilder.techniques.vfx.polar_coordinate_warp.polar_warp_image'),
    demo=lambda: demo.film(draw),
)
