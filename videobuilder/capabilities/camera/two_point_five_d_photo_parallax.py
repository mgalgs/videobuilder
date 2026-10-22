"""2.5D Photo Parallax: one still photo and a greyscale depth map of it are
cut into a stack of depth slices, and as the camera drifts the near slices
slide further than the far ones, so the flat picture seems to have depth.

    slices = depth_slices(photo, depth)                  # once, PIL images in
    draw_depth_parallax(cv, slices, box, view=(math.sin(t), 0))   # each frame
"""
import math
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ... import parallax


def _fill_from(rgb, valid):
    """`rgb` with the pixels outside the mask `valid` painted in from the
    nearest valid ones (a push-pull pyramid: average down with the holes left
    out, then fill each level's holes from the one below it)."""
    img = rgb.convert('RGBA')
    img.putalpha(valid)
    levels = [img]
    while max(levels[-1].size) > 1:
        small = levels[-1].convert('RGBa').reduce(2).convert('RGBA')   # premultiplied: holes don't darken it
        r, g, b, a = small.split()
        levels.append(Image.merge('RGBA', (r, g, b, a.point(lambda v: min(255, 4 * v)))))  # any valid child counts
    fill = levels[-1].copy()
    fill.putalpha(255)
    for lvl in reversed(levels[:-1]):
        fill = Image.alpha_composite(fill.resize(lvl.size, Image.Resampling.BILINEAR), lvl)
    return fill.convert('RGB')


def depth_slices(photo, depth, layers=12, feather=1.0, reach=0.04):
    """Cut `photo` (a PIL image) into up to `layers` depth slices by `depth`
    (a PIL greyscale image the same size: white is near, black is far).
    Returns `(vb.Image, z)` pairs back to front, `z` 0 (far) to 1 (near);
    depth bands with no pixels in them are skipped.

    Each slice is its band plus whatever nearer pixels lie within `reach`
    (a fraction of the photo's width; keep it at least the `travel` you
    draw with) of it, and that margin is painted in from the band's own
    colours. So when a near object slides aside it uncovers what is
    plausibly behind it, not a hole or a copy of itself. The furthest slice
    is painted in everywhere and stays opaque. `feather` softens each cut
    (px of blur). Cut once, outside `draw`: it is the slow part."""
    rgb = photo.convert('RGB')
    d = depth.convert('L').resize(rgb.size)
    cuts = [round(255 * k / layers) for k in range(layers)] + [256]
    out = []
    for k in range(layers):
        lo, hi = cuts[k], cuts[k + 1]
        band = d.point(lambda v, lo=lo, hi=hi: 255 if lo <= v < hi else 0)
        if not band.getbbox():
            continue
        near = band.filter(ImageFilter.BoxBlur(reach * rgb.width)).point(lambda v: 255 if v else 0)
        cover = ImageChops.multiply(near, d.point(lambda v, lo=lo: 255 if v >= lo else 0))
        if feather:
            cover = cover.filter(ImageFilter.GaussianBlur(feather))
        piece = _fill_from(rgb, band)
        if out:                                      # the furthest slice stays opaque: it backs the rest
            piece.putalpha(cover)
        out.append((vb.Image.from_pil(piece), (lo + hi) / 2 / 255))
    return tuple(out)


def draw_depth_parallax(cv, slices, box, view=(0.0, 0.0), travel=0.035, focus=0.3, push=0.0):
    """Draw `slices` (from `depth_slices`) filling `box` (x, y, w, h), seen
    from camera position `view`: (-1..1, -1..1) across and up/down. Each
    slice shifts by `(z - focus) * travel * box width * view`, so depth
    `focus` holds still, nearer slides with the camera's opposite, further
    with it. `push` (0..1) adds a dolly-in that grows near slices faster.
    The photo is overscanned just enough that its edges never show."""
    x, y, w, h = box
    iw, ih = slices[0][0].w, slices[0][0].h
    spread = max(abs(z - focus) for _, z in slices) * travel
    base = max(w / iw, h / ih) * (1 + 2.2 * spread)
    vx, vy = view
    with cv.clip(x, y, w, h):
        for img, z in slices:
            s = base * (1 + 0.12 * push * (0.4 + z))
            dx, dy = -(z - focus) * travel * w * vx, -(z - focus) * travel * w * vy
            sw, sh = iw * s, ih * s
            cv.image(img, x + (w - sw) / 2 + dx, y + (h - sh) / 2 + dy, sw, sh)


# ---- the demo's photo: a dusk landscape painted with its own depth map ----

PW, PH = 960, 540


def _paint(d, z, shape, color, depth_value):
    """Draw one closed `shape` into the photo `d` and the depth map `z`."""
    d.polygon(shape, fill=color)
    z.polygon(shape, fill=depth_value)


def _ridge(seed, top, height, color, depth_value, d, z):
    pts = [(px, top + py) for px, py in parallax.ridge(PW, height, seed=seed)]
    _paint(d, z, pts + [(PW, PH), (0, PH)], color, depth_value)


def _pine(d, z, x, base, size, color, depth_value):
    for i in range(3):
        w, top = size * (0.5 - 0.12 * i), base - size * (0.55 + 0.42 * i)
        _paint(d, z, [(x - w, top + size * 0.6), (x, top), (x + w, top + size * 0.6)], color, depth_value)
    _paint(d, z, [(x - size * 0.05, base), (x - size * 0.05, base - size * 0.3),
                  (x + size * 0.05, base - size * 0.3), (x + size * 0.05, base)], color, depth_value)


@lru_cache(maxsize=1)
def demo_slices():
    """The demo's photo and depth map, cut into slices (built once)."""
    sky = Image.new('RGB', (1, PH))
    top, bottom = (36, 44, 78), (238, 150, 104)
    for py in range(PH):
        t = min(1.0, py / (PH * 0.6))
        sky.putpixel((0, py), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    photo = sky.resize((PW, PH))
    depth = Image.new('L', (PW, PH), 0)
    d, z = ImageDraw.Draw(photo), ImageDraw.Draw(depth)
    sx, sy, sr = PW * 0.66, PH * 0.34, 46
    _paint(d, z, [(sx + sr * math.cos(a / 24 * math.tau), sy + sr * math.sin(a / 24 * math.tau)) for a in range(24)],
           (255, 214, 150), 12)
    _ridge(3, PH * 0.36, 90, (122, 98, 128), 60, d, z)
    _ridge(7, PH * 0.50, 80, (82, 66, 98), 115, d, z)
    _ridge(12, PH * 0.64, 70, (50, 42, 66), 170, d, z)
    _ridge(5, PH * 0.80, 40, (26, 24, 36), 230, d, z)
    for px, size in ((110, 150), (175, 110), (800, 170), (870, 120)):
        _pine(d, z, px, PH * 0.88, size, (16, 16, 24), 250)
    return depth_slices(photo, depth), vb.Image.from_pil(depth.convert('RGB'))


BOX = (40, 50, 720, 405)


def draw(n, cv):
    slices, depth = demo_slices()
    t = n / demo.FPS / demo.SECONDS
    view = (math.sin(math.tau * t), 0.35 * math.sin(2 * math.tau * t))
    cv.shadow(*BOX, radius=6, dy=10, blur=30, color=(0, 0, 0, 0.5))
    draw_depth_parallax(cv, slices, BOX, view=view, travel=0.05)
    cv.outline(*BOX, demo.LINE, width=2)
    # the depth map that drives it, as a small key beside the picture
    kx, ky, kw, kh = 790, 200, 132, 74
    cv.image(depth, kx, ky, kw, kh)
    cv.outline(kx, ky, kw, kh, demo.MUTED, width=1)
    demo.word(cv, 'depth map', kx + kw / 2, ky + kh + 22, size=18, color=demo.MUTED, weight=600)
    dot = kx + kw / 2 + (kw / 2 - 8) * view[0]
    demo.dot(cv, dot, ky - 18, r=5, color=demo.ACCENT)  # where the camera is


CAPABILITY = Capability(
    id='two-point-five-d-photo-parallax',
    name='2.5D photo parallax',
    family='camera',
    group='Depth',
    aliases=('depth-map parallax', 'image depth displacement', '2.5D parallax', '3D photo effect'),
    definition='A single still photo is cut into depth slices from a depth map, and as the camera drifts '
               'the near slices slide further than the far ones, so the flat picture seems to have depth.',
    phrasings=('make this still photo look 3D with a slow camera drift',
               'give the picture some depth so the foreground moves against the background',
               'animate a flat image like the camera is moving through it'),
    related=('parallax-occlusion-mapping', 'parallax-slide', 'parallax-letter-layers',
             'pointer-parallax-layers', 'displacement-map', 'scroll-parallax-layers'),
    api=('videobuilder.capabilities.camera.two_point_five_d_photo_parallax.draw_depth_parallax',
         'videobuilder.capabilities.camera.two_point_five_d_photo_parallax.depth_slices'),
    demo=lambda: demo.film(draw),
)
