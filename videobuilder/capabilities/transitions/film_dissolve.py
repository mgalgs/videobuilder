"""Film Dissolve: a cross-dissolve mixed in linear light, the way two
exposures add up on film, so the brighter scene shows through early and the
darks fade last, with a little grain riding the middle of the mix."""
import math

from PIL import Image, ImageChops, ImageMath

from ... import canvas
from ...looks.fx import image_surface, noise, surface_image
from .. import _demo as demo
from ..schema import Capability

_TOP = 65535.0
_TO_LINEAR = [_TOP * ((i / 255) / 12.92 if i <= 10 else ((i / 255 + 0.055) / 1.055) ** 2.4) for i in range(256)]
_TO_SRGB = None  # built on first use: 65536 entries


def _to_srgb():
    global _TO_SRGB
    if _TO_SRGB is None:
        def enc(v):
            x = v / _TOP
            s = 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
            return max(0, min(255, round(s * 255)))
        _TO_SRGB = [enc(v) for v in range(65536)]
    return _TO_SRGB


def _shot(cv, scene):
    sub = canvas.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    scene(sub)
    return surface_image(sub.surface)


def film_dissolve(cv, a, b, p, grain=0.12, seed=0):
    """Draw the dissolve at progress `p` (0 -> 1): `a(cv)` and `b(cv)`, each
    drawn whole, mixed by exposure rather than by pixel value -- both
    converted to linear light, weighted (1 - p) and p, and converted back.
    `grain` is the strength of the film grain laid over the mix, strongest
    halfway and gone at both ends (0 for none); `seed` varies it per use.

    In a film, call it while two shots are live in an overlap, e.g.
    `film_dissolve(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    p = min(1.0, max(0.0, p))
    ia, ib = _shot(cv, a), _shot(cv, b)
    lut, out = _to_srgb(), []
    for ca, cb in zip(ia.split(), ib.split()):
        la, lb = ca.point(_TO_LINEAR, 'F'), cb.point(_TO_LINEAR, 'F')
        mix = ImageMath.lambda_eval(lambda e: e['a'] * (1 - p) + e['b'] * p, a=la, b=lb)
        out.append(mix.convert('I').point(lut, 'L'))
    im = Image.merge('RGB', out)
    k = grain * math.sin(math.pi * p)
    if k > 0:
        w, h = im.size
        g = noise(w, h, seed * 1009 + round(p * 1000), blur=0.6 * max(1.0, h / 1080))
        g = g.point([max(0, min(255, round(128 + (v - 128) * k * 2))) for v in range(256)])
        im = ImageChops.add(im, Image.merge('RGB', (g, g, g)), offset=-128)
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(image_surface(im), 0, 0)
    c.paint()
    c.restore()


def _night(cv):
    """A dark street at night with a few bright windows: the outgoing shot."""
    W, H = demo.W, demo.H
    cv.fill('#0b0e18')
    cv.rect(0, H * 0.68, W, H * 0.32, '#131826')
    for x in (0.16, 0.42, 0.68):
        cv.rect(W * x, H * 0.3, W * 0.16, H * 0.38, '#1c2335')
        cv.rect(W * (x + 0.04), H * 0.38, W * 0.08, H * 0.12, '#ffd27a')
    demo.dot(cv, W * 0.86, H * 0.2, r=H * 0.07, color='#f4f1e4')
    demo.word(cv, 'Scene A', 90, 40, size=24, color=demo.INK)


def _day(cv):
    """A bright midday shot with a dark doorway: the incoming one."""
    W, H = demo.W, demo.H
    cv.fill('#bfe0f2')
    cv.rect(0, H * 0.68, W, H * 0.32, '#e9d9b8')
    cv.rect(W * 0.3, H * 0.28, W * 0.4, H * 0.4, '#f6f1e6')
    cv.rect(W * 0.45, H * 0.42, W * 0.1, H * 0.26, '#1a1410')
    demo.dot(cv, W * 0.14, H * 0.2, r=H * 0.08, color='#fff6d8')
    demo.word(cv, 'Scene B', 90, 40, size=24, color=demo.BG)


CAPABILITY = Capability(
    id='film-dissolve',
    name='Film dissolve',
    family='transitions',
    group='Dissolves',
    aliases=('linear-light dissolve', 'optical dissolve', 'gamma-correct crossfade'),
    definition='One scene melts into the next the way two exposures add on film: the brighter '
               'parts of each glow through the blend while the darks fade away last, with a hint of grain.',
    phrasings=('a crossfade that looks like real film, not a video mix',
               'dissolve to the next shot with the highlights blooming through',
               'an old-movie style blend between two scenes'),
    related=('noise-dissolve', 'pixelate-transition', 'cross-zoom', 'thin-film-iridescence', 'screen-blend',
             'halation'),
    api=('videobuilder.capabilities.transitions.film_dissolve.film_dissolve',),
    demo=lambda: demo.two_scenes(film_dissolve, start=0.6, length=1.8, a=_night, b=_day),
)
