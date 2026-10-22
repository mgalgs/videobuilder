"""Look-around: the camera stays put inside a 360-degree panorama and turns,
so the surroundings sweep past and wrap all the way round."""
import math
from functools import lru_cache

import numpy as np
from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def look_around_view(pano, yaw, pitch=0.0, fov=90.0, size=(960, 540)):
    """The view out of a camera at the centre of the equirectangular panorama
    `pano` (a PIL image, a `vb.Image`, or an RGB(A) array; 360 degrees across,
    180 degrees top to bottom, the horizon across the middle), as a PIL image
    of `size` px. `yaw` turns the camera right in degrees (0 looks at the
    panorama's centre column), `pitch` tilts it up, `fov` is the horizontal
    field of view in degrees. Straight lines stay straight, as through a real lens."""
    src = _pixels(pano)
    ph, pw = src.shape[:2]
    w, h = size
    f = (w / 2) / math.tan(math.radians(fov) / 2)
    xs = (np.arange(w) + 0.5 - w / 2) / f
    ys = (h / 2 - np.arange(h) - 0.5) / f
    x, y = np.meshgrid(xs, ys)
    z = np.ones_like(x)
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    y, z = y * cp + z * sp, z * cp - y * sp  # tilt up about the camera's x axis
    lon = np.arctan2(x, z) + math.radians(yaw)
    lat = np.arctan2(y, np.hypot(x, z))
    u = (lon / (2 * math.pi) + 0.5) * pw - 0.5
    v = (0.5 - lat / math.pi) * ph - 0.5
    u0 = np.floor(u).astype(int)
    v0 = np.clip(np.floor(v).astype(int), 0, ph - 2)
    fu = (u - u0)[..., None]
    fv = np.clip(v - v0, 0, 1)[..., None]
    u0, u1 = u0 % pw, (u0 + 1) % pw  # wraps: the left and right edges meet behind the camera
    top = src[v0, u0] * (1 - fu) + src[v0, u1] * fu
    bot = src[v0 + 1, u0] * (1 - fu) + src[v0 + 1, u1] * fu
    out = (top * (1 - fv) + bot * fv).astype(np.uint8)
    return PILImage.fromarray(out, 'RGBA' if out.shape[2] == 4 else 'RGB')


def look_around(cv, pano, yaw, pitch=0.0, fov=90.0, box=None, quality=1.0):
    """Draw the camera's view into `pano` (see `look_around_view`) filling
    `box` (x, y, w, h; default the whole frame). `quality` scales the
    rendered pixels below the canvas's own (0.5 renders a quarter as many,
    then stretches them).

    In a film, sweep `yaw` over a shot, e.g.
    `look_around(cv, pano, -60 + 300 * vb.ease_in_out_quart(p))`."""
    x, y, w, h = box or (0, 0, cv.width, cv.height)
    s = cv.scale_factor() * quality
    size = (max(2, round(w * s)), max(2, round(h * s)))
    img = vb.Image.from_pil(look_around_view(pano, yaw, pitch, fov, size))
    cv.image(img, x, y, w, h)


def _pixels(pano):
    if isinstance(pano, np.ndarray):
        return pano.astype(np.float32)
    pil = pano._pil if isinstance(pano, vb.Image) else pano
    hit = _ARRAYS.get(id(pil))
    if hit is None or hit[0] is not pil:
        if len(_ARRAYS) > 4:
            _ARRAYS.clear()
        hit = _ARRAYS[id(pil)] = pil, np.asarray(pil.convert('RGB'), dtype=np.float32)
    return hit[1]


_ARRAYS = {}  # id(pil) -> (pil, float pixels): a panorama is converted once, not every frame


# ---- the demo: a night valley wrapped all the way round, with four landmarks ----

PW, PH = 2400, 1200
SKY_TOP, SKY_LOW = (38, 40, 74), (96, 104, 178)
RIDGES = (((150, 160, 245), 0.455, 22, 7), ((72, 78, 140), 0.50, 22, 3), ((40, 43, 72), 0.56, 18, 11))


def _ridge(lon, base, amp, seed):
    """Height (as a fraction of the panorama) of a ridge at longitudes `lon`;
    whole-number frequencies, so it joins up seamlessly behind the camera."""
    r = np.zeros_like(lon)
    for k, a in ((2, 1.0), (3, 0.6), (5, 0.35), (9, 0.15)):
        r += a * np.sin(k * lon + seed * k * 0.7)
    return base - amp / PH * r


@lru_cache(maxsize=1)
def _panorama():
    cv = vb.Canvas(PW, PH)
    bands = 160
    for i in range(bands):
        t = min(1.0, (i + 0.5) / bands / 0.6) ** 1.5
        color = '#%02x%02x%02x' % tuple(round(a + (b - a) * t) for a, b in zip(SKY_TOP, SKY_LOW))
        cv.rect(0, PH * i / bands, PW, PH / bands + 1, color)
    lon = np.linspace(0, 2 * math.pi, 241)
    for color, base, amp, seed in RIDGES:
        top = [(PW * k / 240, PH * h) for k, h in enumerate(_ridge(lon, base, amp, seed))]
        vb.paths.draw(cv, top + [(PW, PH), (0, PH)], '#%02x%02x%02x' % color, fill=True)
    for i, (label, color) in enumerate((('N', '#f2b705'), ('E', demo.TEAL), ('S', demo.ACCENT), ('W', demo.INK))):
        cx = PW * (0.5 + i / 4) % PW
        if label == 'N':  # the moon hangs above north
            my, stretch = PH * 0.31, 1 / math.cos(math.pi * 0.19)  # widened, as the panorama squeezes it back
            vb.paths.draw(cv, [(cx + 30 * stretch * math.cos(a), my + 30 * math.sin(a))
                               for a in np.linspace(0, 2 * math.pi, 64)], color, fill=True)
        for dx in (-PW, 0, PW):  # drawn either side so it survives the wrap
            demo.word(cv, label, cx + dx, PH * 0.385, size=56, color=color)
    rgb = np.frombuffer(cv.bgra(), np.uint8).reshape(PH, PW, 4)[..., 2::-1]
    return PILImage.fromarray(np.ascontiguousarray(rgb), 'RGB')


def _draw(n, cv):
    p = demo.phase(n, 0.3, 2.8)
    yaw = 180 - 180 * math.cos(math.pi * p)  # a smooth full turn, N back round to N
    pitch = 8 + 4 * math.sin(math.pi * p)
    look_around(cv, _panorama(), yaw, pitch, fov=95)
    _compass(cv, yaw)


def _compass(cv, yaw):
    """A small heading dial in the corner, its needle following the camera."""
    cx, cy, r = demo.W - 70, demo.H - 70, 34
    cv.sector(cx, cy, r + 6, 0, 2 * math.pi, demo.BG, alpha=0.6)
    cv.arc(cx, cy, r, 0, 2 * math.pi, demo.INK, width=2, alpha=0.8)
    a = math.radians(yaw) - math.pi / 2
    cv.line(cx, cy, cx + r * 0.85 * math.cos(a), cy + r * 0.85 * math.sin(a), demo.ACCENT, width=4)


TECHNIQUE = Technique(
    id='look-around',
    name='Look-around',
    family='camera',
    group='Camera moves',
    aliases=('360 pan', 'panorama pan', 'equirectangular look-around'),
    definition='The camera stays in one spot and swivels to look in every direction, so a scene that '
               'surrounds it on all sides slides past and comes back round to where it started.',
    phrasings=('turn the camera all the way around like you are standing in the middle of the scene',
               'spin the view through a full 360 panorama',
               'look around the whole place from where you stand'),
    related=('polar-coordinate-warp', 'rotoscope-look', 'zoom-through', 'canvas-pan-and-zoom',
             'turntable-rotation', 'flip'),
    api=('videobuilder.techniques.camera.look_around.look_around',
         'videobuilder.techniques.camera.look_around.look_around_view'),
    demo=lambda: demo.film(_draw),
)
