"""Bloom: the brightest parts of a picture spill a soft halo of their own
colour into the dark around them, the way strong light overexposes a lens;
dim parts stay crisp."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...canvas import Canvas


def bloom(cv, box, paint, strength=1.0, radius=28, threshold=0.55):
    """Draw `paint(sub)` into `cv` sharp, then add a glow of only its bright
    parts on top. `paint` draws in frame coordinates and is called twice
    (once on `cv`, once on an offscreen canvas); `box` (a `vb.Box`) bounds
    what it draws and is grown by the blur. Pixels whose brightness is above
    `threshold` (0..1) feed the glow, ramping in from there, so dim shapes
    don't bloom. The glow is two blurs, a wide one of `radius` px and a tight
    one a quarter of that, added onto what's below (light adds) at
    `strength` (0 = none; above 1 burns hotter)."""
    paint(cv)
    if strength <= 0:
        return
    from PIL import Image, ImageChops, ImageFilter
    s = cv.scale_factor()
    pad = radius * 2.5
    x0, y0, w, h = box.x - pad, box.y - pad, box.w + 2 * pad, box.h + 2 * pad
    k = max(1.0, radius * s / 6)                   # draw small: the blur hides it
    sc = s / k
    sub = Canvas(w, h, scale=sc)
    sub.ctx.translate(-x0, -y0)
    paint(sub)
    sub.surface.flush()
    W, H = sub.surface.get_width(), sub.surface.get_height()
    im = Image.frombuffer('RGBA', (W, H), bytes(sub.surface.get_data()), 'raw', 'BGRA',
                          sub.surface.get_stride(), 1)
    lo = 255 * vb.clamp01(threshold)
    ramp = [0 if v <= lo else min(255, round(255 * (v - lo) / max(1.0, 255 - lo) * 1.5)) for v in range(256)]
    mask = im.convert('L').point(ramp)
    bright = ImageChops.multiply(im, Image.merge('RGBA', (mask,) * 4))
    ctx = cv.ctx
    for r, a in ((radius, 1.6), (radius / 4, 0.8)):
        gain = a * strength                        # brightened before adding, so a wide halo still reads
        glow = bright.filter(ImageFilter.GaussianBlur(max(0.5, r * sc))).point(lambda v: min(255, v * gain))
        data = bytearray(glow.tobytes('raw', 'BGRA'))
        out = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, W, H, W * 4)
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.translate(x0, y0)
        ctx.scale(1 / sc, 1 / sc)
        ctx.set_source_surface(out, 0, 0)
        ctx.get_source().set_filter(cairo.FILTER_GOOD)
        ctx.paint()
        ctx.restore()


def _mix(a, b, p):
    """Hex colour `a` blended towards `b` by `p`."""
    ca, cb = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in (a, b))
    return '#' + ''.join(f'{round(x + (y - x) * p):02x}' for x, y in zip(ca, cb))


def draw(n, cv):
    # the lights come up from dim to blazing, then ease back a little; only once
    # they're bright does the halo bleed out (the grey bar never blooms)
    up = vb.ease.ease_in_out_quart(demo.phase(n, 0.3, 1.3))
    settle = demo.phase(n, 1.6, 2.4)
    level = up * (1 - 0.2 * settle)
    cx, cy = demo.W / 2, demo.H / 2 - 50
    gold = _mix('#5a4a14', '#ffe066', level)
    blue = _mix('#2c2a5e', '#c9c4ff', level)

    def paint(c):
        c.arc(cx, cy, 170, 0, 2 * math.pi, gold, width=14)
        c.rect(cx - 150, cy + 250, 300, 12, blue, radius=6)
        c.rect(cx - 90, cy + 300, 180, 10, demo.MUTED, radius=5)

    box = vb.Box(cx - 200, cy - 200, 400, 520)
    bloom(cv, box, paint, strength=1.6 * level, radius=50)
    cv.mark('ring', cx - 177, cy - 177, 354, 354)


TECHNIQUE = Technique(
    id='bloom',
    name='Bloom',
    family='camera',
    group='Lighting & surface',
    aliases=('glow bloom', 'post glow', 'glow pass', 'light bleed', 'HDR glow'),
    definition='The brightest shapes in the frame spill a soft haze of their own colour '
               'into the dark around them, as though too much light reached the lens.',
    phrasings=('make the bright parts glow and bleed into the background',
               'add a soft dreamy light halo around the highlights',
               'turn up the brightness until the lights start to bloom'),
    related=('glow-button', 'phosphor-persistence', 'fireflies', 'spiral-bloom', 'fresnel-edge-glow',
             'outline-pulse-glow'),
    api=('videobuilder.techniques.camera.bloom.bloom',),
    demo=lambda: demo.film(draw),
)
