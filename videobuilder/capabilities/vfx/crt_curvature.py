"""CRT curvature: the picture is bent as if seen on the bulging glass of an old
tube screen -- its edges bow outward, the corners pull in and round off, and
the corners and rim fall darker than the middle."""
import math

import cairo
from PIL import Image, ImageDraw

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _pixels(cv, draw):
    """`draw(c)` on a fresh canvas the size and scale of `cv`, as a PIL RGB image."""
    c = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    draw(c)
    s = c.surface
    s.flush()
    im = Image.frombuffer('RGBA', (s.get_width(), s.get_height()), bytes(s.get_data()), 'raw', 'BGRA',
                          s.get_stride(), 1)
    return im.convert('RGB')


def barrel(im, amount, cells=64):
    """`im` (PIL) bent onto a convex tube: an output point at (u, v), the
    picture's centre at 0 and its edges at +-1, shows the source pixel at
    (u, v) * (1 + `amount` * (u^2 + v^2)) / (1 + `amount` / 2). The middle
    is enlarged a touch, the rim squeezed, and what falls past the source's
    edge is left empty, which bows the screen's outline; the corners are then
    rounded off in step with `amount`. Returns
    `(picture, mask)`: the bent RGB image and an 'L' mask of where it shows."""
    w, h = im.size
    if amount <= 1e-4:
        return im, Image.new('L', (w, h), 255)
    nx = cells
    ny = max(1, round(cells * h / w))

    def src(x, y):
        u, v = 2 * x / w - 1, 2 * y / h - 1
        k = (1 + amount * (u * u + v * v)) / (1 + amount / 2)
        return (u * k + 1) * w / 2, (v * k + 1) * h / 2

    xs = [w * i / nx for i in range(nx + 1)]
    ys = [h * j / ny for j in range(ny + 1)]
    grid = [[src(x, y) for x in xs] for y in ys]
    mesh = []
    for j in range(ny):
        for i in range(nx):
            box = (round(xs[i]), round(ys[j]), round(xs[i + 1]), round(ys[j + 1]))
            (ax, ay), (bx, by) = grid[j][i], grid[j + 1][i]
            (qx, qy), (dx, dy) = grid[j + 1][i + 1], grid[j][i + 1]
            mesh.append((box, (ax, ay, bx, by, qx, qy, dx, dy)))
    picture = im.transform((w, h), Image.MESH, mesh, Image.BILINEAR)
    mask = Image.new('L', (w, h), 255).transform((w, h), Image.MESH, mesh, Image.BILINEAR)
    box = mask.getbbox()
    if box:
        ss = 4  # supersampled, for a smooth corner
        r = ss * min(w, h) * 0.2 * min(1.0, amount / 0.1)
        round_ = Image.new('L', (w * ss, h * ss), 0)
        ImageDraw.Draw(round_).rounded_rectangle([v * ss for v in box], radius=r, fill=255)
        mask = Image.composite(mask, Image.new('L', (w, h), 0), round_.resize((w, h), Image.LANCZOS))
    return picture, mask


def _vignette(size, strength):
    """An 'L' darkness mask the shape of `size`: 0 in the middle, rising
    toward the rim and most in the corners, peaking at 255 * `strength`."""
    g = Image.radial_gradient('L').resize(size, Image.BILINEAR)  # 0 at the centre, 255 at the inscribed rim
    lut = [round(255 * strength * vb.clamp01((i / 255 - 0.35) / 0.85) ** 1.4) for i in range(256)]
    return g.point(lut)


def crt_curvature(cv, scene, amount, x=0, y=0, w=None, h=None, vignette=0.6):
    """Draw `scene(c)` bent onto a curved tube screen occupying the box
    (`x`, `y`, `w`, `h`) in film px (default the whole frame). `amount` is the
    bulge (0 is flat; about 0.1 to 0.2 reads as an old TV); animate it to
    curve the glass in or out. `vignette` (0 to 1) is how dark the corners
    fall, scaled with `amount` so a flat screen stays evenly lit. `scene`
    draws in film coordinates, as onto the frame; only the box is used.
    Whatever is already on `cv` shows around the bowed outline."""
    s = cv.scale
    w = cv.width - x if w is None else w
    h = cv.height - y if h is None else h
    px = (round(x * s), round(y * s), round((x + w) * s), round((y + h) * s))
    im = _pixels(cv, scene).crop(px)
    picture, mask = barrel(im, amount)
    shade = vignette * vb.clamp01(amount / 0.15)
    if shade > 0:
        picture = Image.composite(Image.new('RGB', picture.size), picture, _vignette(picture.size, shade))
    rgba = picture.convert('RGBA')
    rgba.putalpha(mask)
    data = bytearray(rgba.tobytes('raw', 'BGRa'))  # cairo wants premultiplied alpha
    surf = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, rgba.width, rgba.height,
                                              rgba.width * 4)
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(surf, px[0], px[1])
    c.paint()
    c.restore()


SX, SY, SW, SH = 150, 62, 660, 416  # the demo's screen, in film px


def _landscape(cv):
    """A dusk landscape filling the demo screen: sky, sun, three hill bands."""
    sky = cairo.LinearGradient(0, SY, 0, SY + SH)
    sky.add_color_stop_rgb(0, 0.32, 0.34, 0.66)
    sky.add_color_stop_rgb(0.65, 0.55, 0.58, 0.95)
    cv.ctx.set_source(sky)
    cv.ctx.rectangle(SX, SY, SW, SH)
    cv.ctx.fill()
    demo.dot(cv, SX + SW * 0.68, SY + SH * 0.36, r=40, color='#f2b705')
    for k, (base, amp, col) in enumerate(((0.55, 24, '#6b70a8'), (0.70, 20, '#3b4170'), (0.84, 18, '#1c2033'))):
        c = cv.ctx
        c.move_to(SX, SY + SH)
        for i in range(61):
            t = i / 60
            c.line_to(SX + SW * t, SY + SH * base - amp * math.sin(2 * math.pi * (t * 1.2 + 0.3 * k)))
        c.line_to(SX + SW, SY + SH)
        c.close_path()
        c.set_source_rgb(*(int(col[i:i + 2], 16) / 255 for i in (1, 3, 5)))
        c.fill()
    # grid lines make the bend easy to read
    for i in range(1, 8):
        cv.line(SX + SW * i / 8, SY, SX + SW * i / 8, SY + SH, demo.INK, width=1.5, alpha=0.2)
    for j in range(1, 6):
        cv.line(SX, SY + SH * j / 6, SX + SW, SY + SH * j / 6, demo.INK, width=1.5, alpha=0.2)


def draw(n, cv):
    amount = 0.18 * vb.ease_in_out_quart(demo.phase(n, 0.5, 2.2))
    crt_curvature(cv, _landscape, amount, SX, SY, SW, SH, vignette=0.75)


CAPABILITY = Capability(
    id='crt-curvature',
    name='CRT curvature',
    family='vfx',
    group='CRT & display',
    aliases=('screen curvature', 'barrel screen', 'curved glass', 'tube bulge'),
    definition='The picture bows outward like the rounded glass of an old television tube, its corners '
               'pulled in and rounded off and falling darker than the centre.',
    phrasings=('make it look like it is on an old curved TV screen',
               'bulge the image like the glass of a retro tube monitor',
               'give the frame that rounded, dark-cornered old CRT look'),
    related=('glass-refraction', 'arc-bend-morph', 'refraction-ripple', 'lens-distortion', 'bend-deformer',
             'crumple'),
    api=('videobuilder.capabilities.vfx.crt_curvature.crt_curvature',
         'videobuilder.capabilities.vfx.crt_curvature.barrel'),
    demo=lambda: demo.film(draw),
)
