"""Night vision: whatever is drawn is seen through an image-intensifier
scope -- a dark scene lifted to bright phosphor green, noisy with live
grain, highlights blooming, inside a round eyepiece that falls off to black."""
import math
from functools import lru_cache

from PIL import Image, ImageChops, ImageFilter, ImageOps

from ...looks import fx
from .. import _demo as demo
from ..schema import Technique


@lru_cache(maxsize=4)
def _eyepiece(w, h, radius, soft):
    """An L mask w x h: 255 inside a centred circle `radius` (a share of the
    short side, halved) wide, easing to 0 over the outer `soft` of it."""
    n = 256
    data = bytearray(n * n)
    for y in range(n):
        for x in range(n):
            d = math.hypot(x + 0.5 - n / 2, y + 0.5 - n / 2) / (n / 2)
            k = min(1.0, max(0.0, (1 - d) / soft))
            data[y * n + x] = int(255 * k * k * (3 - 2 * k))
    side = max(2, round(min(w, h) * radius))
    disc = Image.frombytes('L', (n, n), bytes(data)).resize((side, side), Image.BICUBIC)
    out = Image.new('L', (w, h), 0)
    out.paste(disc, ((w - side) // 2, (h - side) // 2))
    return out


def _treat(im, t, age, u, gain=6.0, power=1.0, grain=0.22, bloom=0.7, scope=0.98, flicker=0.06,
           black='#020803', mid='#2f9a34', white='#dcffd2'):
    w, h = im.size
    gain = 1 + (gain - 1) * power
    gain *= 1 + flicker * math.sin(t * 37.0) * math.sin(t * 11.0)   # the tube's gain hunts a little
    g = fx.luma(im)
    g = g.point(lambda v: min(255, int(v * gain + 6 * power)))
    if bloom:
        hot = g.point(lambda v: max(0, v - 170) * 3).filter(ImageFilter.GaussianBlur(18 * u))
        g = ImageChops.screen(g, hot.point(lambda v: int(v * bloom)))
    if grain:
        k = max(1, round(1.5 * u))                              # grain a couple of px across at 1080
        n = fx.noise(max(1, w // k), max(1, h // k), fx.boil(t, 30) % 24)
        n = fx.grow(n, (w, h), Image.BILINEAR).point(lambda v: int(128 + (v - 128) * grain))
        g = ImageChops.add(g, n, 1.0, -128)
    out = ImageOps.colorize(g, black=black, mid=mid, white=white)
    if scope:
        out = Image.composite(out, Image.new('RGB', (w, h), black), _eyepiece(w, h, scope, 0.22))
    return out


NIGHT_VISION = fx.Filter('night-vision', 'Night vision', 'grainy phosphor-green image-intensifier view', _treat)


def night_vision(cv, t, power=1.0, box=None, **opts):
    """A context manager: everything drawn on `cv` inside the block (and what
    was there already) comes out as a night-vision view when it ends.

    `t`: film time in seconds (the grain and gain flicker run on it).
    `power` 0 -> 1 ramps the tube's gain up (overshoot past 1 for a
    switch-on flare). `opts`: `gain` (brightness boost, 6), `grain` (0 -> 1,
    0.22), `bloom` (glow round highlights, 0.7), `scope` (eyepiece diameter
    over the short side, 0.98; 0 for a full frame), `flicker`, and the
    `black`/`mid`/`white` phosphor inks.

        with night_vision(cv, n / fps):
            draw_dark_scene(cv)
        # readouts that should stay crisp go here, after the block
    """
    return fx.apply(cv, NIGHT_VISION, t, box=box, opts=dict(power=power, **opts))


# ---- demo: a dark yard; the scope switches on and lifts it into green ----

def _night_scene(cv, t):
    W, H = demo.W, demo.H
    cv.fill('#07090f')
    demo.dot(cv, W * 0.6, H * 0.24, r=46, color='#5c6170')               # the moon
    for i, (y, c) in enumerate(((0.58, '#10141c'), (0.68, '#0c1017'), (0.8, '#090c12'))):
        pts = [(x, H * y + 30 * math.sin(x / 260 + i * 1.7)) for x in range(0, W + 9, 8)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            cv.rect(x0, min(y0, y1), x1 - x0, H - min(y0, y1), c)
    for x, s in ((0.33, 1.0), (0.5, 0.8), (0.69, 1.15)):                   # trees
        cx, base = W * x, H * 0.82
        for k in range(3):
            ww, hh = (140 - 30 * k) * s, 70 * s
            cv.rect(cx - ww / 2, base - 50 * k * s - hh, ww, hh, '#06080c', radius=hh / 2)
        cv.rect(cx - 8 * s, base - 10, 16 * s, 40, '#06080c')
    fx_ = W * (0.27 + 0.4 * (t / demo.SECONDS))                               # a fox trots across
    demo.dot(cv, fx_, H * 0.76, r=24, color='#171b23')
    cv.rect(fx_ - 60, H * 0.76 - 8, 50, 16, '#171b23', radius=8)
    demo.dot(cv, fx_ + 10, H * 0.745, r=5, color='#c8d0b0')                  # eye shine


def _draw(n, cv):
    t = n / demo.FPS
    on = demo.phase(n, 0.5, 0.9)
    if on <= 0:
        _night_scene(cv, t)
        return
    flare = 1.6 * math.exp(-6 * demo.phase(n, 0.5, 1.6))                     # switch-on flare, settling
    with night_vision(cv, t, power=on + flare * on):
        _night_scene(cv, t)


TECHNIQUE = Technique(
    id='night-vision',
    name='Night vision',
    family='vfx',
    group='Thermal & sensor',
    aliases=('night-vision green', 'image intensifier', 'low-light green', 'NVG look'),
    definition='A dark picture is brightened into speckled, glowing green monochrome and shown '
               'inside a round eyepiece that fades to black at its rim.',
    phrasings=('make it look like we are watching through night-vision goggles',
               'the green, grainy view a soldier sees through a night scope',
               'turn this dark shot into that glowing green surveillance look'),
    related=('spotlight-dim', 'day-night-cycle', 'chroma-key', 'vignette', 'matcap-shading',
             'photographic-negative'),
    api=('videobuilder.techniques.vfx.night_vision.night_vision',
         'videobuilder.techniques.vfx.night_vision.NIGHT_VISION',
         'videobuilder.looks.fx.apply'),
    demo=lambda: demo.film(_draw),
)
