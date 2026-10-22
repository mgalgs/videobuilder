"""CCTV surveillance look: whatever the film draws turns into a security
camera feed -- soft grey monochrome stepping at a few frames a second, bowed
by a wide-angle lens, crawling with grain and faint scanlines, darker at the
corners, with the camera's name, a ticking timestamp and a blinking REC laid
over it crisp."""
import math
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import lru_cache

from PIL import Image, ImageChops, ImageOps

import videobuilder as vb

from ...looks.fx import Filter, apply, noise
from .. import _demo as demo
from ..schema import Technique

START = datetime(2026, 10, 14, 2, 17, 58)


def _barrel_mesh(w, h, k, cells=(16, 9)):
    """An Image.MESH for a w x h frame bowed outwards by `k`: the middle
    swells, the edges squeeze, the corners stay put so nothing goes black."""
    cx, cy = w / 2, h / 2
    diag = math.hypot(cx, cy)

    def src(x, y):
        dx, dy = x - cx, y - cy
        s = (1 + k * (dx * dx + dy * dy) / (diag * diag)) / (1 + k)
        return cx + dx * s, cy + dy * s

    gx, gy = cells
    xs = [round(w * i / gx) for i in range(gx + 1)]
    ys = [round(h * j / gy) for j in range(gy + 1)]
    mesh = []
    for j in range(gy):
        for i in range(gx):
            x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
            quad = (*src(x0, y0), *src(x0, y1), *src(x1, y1), *src(x1, y0))
            mesh.append(((x0, y0, x1, y1), quad))
    return mesh


barrel_mesh = lru_cache(maxsize=8)(_barrel_mesh)


@lru_cache(maxsize=8)
def _scanlines(w, h, pitch, depth):
    """An L image: full white with every `pitch`-th row dimmed by `depth`."""
    pitch = max(2, round(pitch))
    rows = bytes(round(255 * (1 - depth)) if y % pitch == 0 else 255 for y in range(h))
    return Image.frombytes('L', (1, h), rows).resize((w, h), Image.NEAREST)


@lru_cache(maxsize=8)
def _vignette(w, h, strength):
    """An L image: white in the middle falling towards the corners."""
    sw, sh = 64, 36
    data = bytes(round(255 * max(0.0, 1 - strength * (((x + 0.5) / sw * 2 - 1) ** 2 * 0.8 +
                                                      ((y + 0.5) / sh * 2 - 1) ** 2) ** 1.4))
                 for y in range(sh) for x in range(sw))
    return Image.frombytes('L', (sw, sh), data).resize((w, h), Image.BICUBIC)


def treat(im, t, age, u, distortion=0.16, grain=0.14, fps=6, tint=('#07090a', '#dfe7ea')):
    """The CCTV treatment of a PIL RGB frame (a `looks.fx` filter's `treat`):
    grey and low-detail, bowed by `distortion`, with `grain` (0 -> 1) that
    changes every 1/`fps` s, scanlines, a vignette and a cold `tint`
    (shadow, highlight)."""
    w, h = im.size
    g = im.convert('L')
    k = max(1, round(3 * u))                     # a cheap sensor: about a third of the detail
    if k > 1 and w > 4 * k:
        g = g.reduce(k).resize((w, h), Image.BILINEAR)
    if distortion:
        g = g.transform((w, h), Image.MESH, barrel_mesh(w, h, distortion), Image.BILINEAR)
    g = g.point([max(0, min(255, round(18 + (v - 128) * 1.12 + 120))) for v in range(256)])
    if grain:
        step = math.floor(t * fps + 1e-9) % 10
        n = noise(w, h, 4099 + step, blur=0.5 * max(1.0, u * 1.5))
        n = n.point([max(0, min(255, round(128 + (v - 128) * grain * 2.2))) for v in range(256)])
        g = ImageChops.add(g, n, offset=-128)
    g = ImageChops.multiply(g, _scanlines(w, h, 4 * u, 0.22))
    band = (t * 0.35) % 1.4 - 0.2              # a faint brighter band rolling down the picture
    by = round(band * h)
    lift = Image.new('L', (w, h), 0)
    lift.paste(10, (0, max(0, by - round(h * 0.06)), w, min(h, by + round(h * 0.06))))
    g = ImageChops.add(g, lift)
    g = ImageChops.multiply(g, _vignette(w, h, 0.75))
    return ImageOps.colorize(g, tint[0], tint[1])


FILTER = Filter('cctv', 'CCTV', 'A security camera feed: grey, grainy, choppy and bowed.', treat,
                aliases=('surveillance', 'security-camera'), fps=6)


def osd(cv, t, camera='CAM 04', place='LOBBY', start=START, rec=True):
    """The camera's on-screen display over a `cv.width` x `cv.height` frame:
    camera id and place top left, a blinking REC top right, the date and a
    timestamp ticking from `start` (a datetime) by `t` seconds bottom left."""
    W, H = cv.width, cv.height
    s = H / 1080
    f = demo.mono(round(34 * s), 700)
    m = 56 * s
    stamp = (start + timedelta(seconds=math.floor(t))).strftime('%Y-%m-%d  %H:%M:%S')

    def put(text, x, y, right=False):
        if right:
            x -= vb.text.block_size([text], f)[0]
        vb.text.draw(cv, [text], f, x + 2 * s, y + 2 * s, '#000000', alpha=0.6)
        return vb.text.draw(cv, [text], f, x, y, '#f2f2ee')

    top = put(f'{camera}  {place}', m, m)
    cv.mark('camera-id', *top)
    if rec:
        box = put('REC', W - m, m, right=True)
        if (t % 1.0) < 0.6:
            demo.dot(cv, box.x - 26 * s, box.y + box.h / 2, r=11 * s, color='#e8402f')
    cv.mark('timestamp', *put(stamp, m, H - m - 40 * s))


@contextmanager
def cctv(cv, t, camera='CAM 04', place='LOBBY', start=START, fps=6, distortion=0.16, grain=0.14):
    """A context manager: everything drawn on `cv` inside the block becomes
    a security-camera feed, then the camera's on-screen display (`osd`) is
    laid over it. It yields the film time held to `fps` frames a second --
    draw the scene at that time so its motion is choppy like the feed's.

        with cctv(cv, t, camera='CAM 02', place='CAR PARK') as ts:
            draw_scene(cv, ts)
    """
    flt = FILTER if fps == FILTER.fps else Filter('cctv', FILTER.title, FILTER.line, treat, fps=fps)
    ts = flt.step(t)
    with apply(cv, flt, ts, opts=dict(distortion=distortion, grain=grain, fps=fps)):
        yield ts
    osd(cv, t, camera=camera, place=place, start=start)


def _scene(cv, t):
    """A car park seen from a high corner: bays, two parked cars and someone
    walking across."""
    W, H = demo.W, demo.H
    cv.fill('#3a3f46')
    cv.rect(0, 0, W, H * 0.3, '#22262c')                       # back wall
    for i in range(6):
        cv.rect(W * (0.06 + 0.16 * i), H * 0.08, W * 0.1, H * 0.1, '#555b63')   # wall windows
    cv.line(0, H * 0.3, W, H * 0.3, '#8a9099', width=6)
    horizon, vx = H * 0.3, W / 2
    for i in range(-5, 6):                                      # bay lines receding to the wall
        cv.line(vx + i * W * 0.05, horizon, vx + i * W * 0.24, H, '#c9ccd0', width=7)
    cv.line(0, H * 0.62, W, H * 0.62, '#c9ccd0', width=6)
    for x, c in ((W * 0.2, '#6c7480'), (W * 0.74, '#9aa2ad')):
        cv.rect(x - 150, H * 0.42, 300, 150, c, radius=34)        # parked cars
        cv.rect(x - 105, H * 0.36, 210, 90, c, radius=30)
        cv.rect(x - 85, H * 0.38, 170, 50, '#2a2e34', radius=12)
    x = W * (0.08 + 0.8 * t / demo.SECONDS)                     # the walker
    y = H * 0.6 + 8 * abs(math.sin(t * 7))
    cv.shape_shadow([(x - 50, y + 190), (x + 70, y + 190), (x + 50, y + 205), (x - 60, y + 205)], blur=12)
    cv.rect(x - 34, y, 68, 150, '#1b1d21', radius=30)
    demo.dot(cv, x, y - 34, r=32, color='#1b1d21')
    stride = math.sin(t * 7) * 22
    cv.line(x - 12, y + 140, x - 12 - stride, y + 195, '#1b1d21', width=22)
    cv.line(x + 12, y + 140, x + 12 + stride, y + 195, '#1b1d21', width=22)
    cv.mark('walker', x - 40, y - 70, 80, 270)


def draw(n, cv):
    t = n / demo.FPS
    with cctv(cv, t, camera='CAM 02', place='CAR PARK B') as ts:
        _scene(cv, ts)


TECHNIQUE = Technique(
    id='cctv-surveillance-look',
    name='CCTV surveillance look',
    family='vfx',
    group='Thermal & sensor',
    aliases=('security camera feed', 'surveillance feed', 'low-fi CCTV', 'security cam footage'),
    definition='The picture becomes a security camera recording: choppy grey footage with grain, a '
               'bulging wide lens and dark corners, stamped with a camera name and a running clock.',
    phrasings=('make it look like we are watching it on a security camera',
               'grainy black-and-white CCTV footage with a timestamp in the corner',
               'turn this shot into a surveillance feed'),
    related=('follow-cam', 'vhs-tracking-bar', 'rotoscope-look', 'tracking-shot', 'pov-shot',
             'video-feedback-loop'),
    api=('videobuilder.techniques.vfx.cctv_surveillance_look.cctv',
         'videobuilder.techniques.vfx.cctv_surveillance_look.treat',
         'videobuilder.techniques.vfx.cctv_surveillance_look.osd'),
    demo=lambda: demo.film(draw),
)
