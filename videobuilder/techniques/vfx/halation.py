"""Halation: the red-orange halo film throws around its brightest lights,
where light passes through the emulsion, bounces off the film base and
re-exposes the red layer just around the highlight. Laid over whatever the
canvas already holds, so it works on any shot."""
import math

from PIL import Image, ImageChops, ImageFilter

from ...looks.fx import image_surface, surface_image
from .. import _demo as demo
from ..schema import Technique


def halation(cv, amount=1.0, threshold=0.75, radius=28, tint=(255, 70, 24)):
    """Add halation to everything drawn on `cv` so far: the pixels brighter
    than `threshold` (0..1 of luma) are lifted out, blurred over about
    `radius` px (at 1080, scaled with the frame) and screened back on in
    `tint`, a wide red halo plus a tighter warm one, so bright shapes on
    dark ground gain a glowing red fringe while their cores stay white.
    `amount` (0 -> 1, more pushes harder) is the strength; ramp it to fade
    the look in.

    In a film, draw the shot as usual, then call `halation(cv)`; anything
    that must stay crisp (captions) goes after."""
    if amount <= 0:
        return
    im = surface_image(cv.surface)
    w, h = im.size
    u = min(w, h) / 1080
    k = max(1, round(4 * u))                       # work at reduced size: the halo is soft anyway
    small = im.reduce(k) if k > 1 else im
    lo = max(0, min(254, round(threshold * 255)))
    ramp = [0 if v <= lo else round(255 * ((v - lo) / (255 - lo)) ** 1.5) for v in range(256)]
    hot = small.convert('L').point(ramp)
    r = max(1.0, radius * u / k)
    wide = hot.filter(ImageFilter.GaussianBlur(r))
    tight = hot.filter(ImageFilter.GaussianBlur(r * 0.35))
    halo = []
    for i, c in enumerate(tint):
        warm = (c / 255, (c / 255) ** 0.5 * 1.1, (c / 255) ** 0.5)[i]  # the tight halo runs hotter, towards orange
        g_wide = 2.4 * amount * c / 255
        g_tight = 1.3 * amount * min(1.0, warm)
        band = ImageChops.add(wide.point(lambda v, g=g_wide: min(255, round(v * g))),
                              tight.point(lambda v, g=g_tight: min(255, round(v * g))))
        halo.append(band)
    halo = Image.merge('RGB', halo)
    if k > 1:
        halo = halo.resize((w, h), Image.BILINEAR)
    out = ImageChops.screen(im, halo)
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(image_surface(out), 0, 0)
    c.paint()
    c.restore()


def _night(cv, t):
    """A dark scene of practical lights: a lamp, lit windows, a neon word."""
    W, H = demo.W, demo.H
    cv.fill('#07080d')
    cv.rect(0, H * 0.74, W, H * 0.26, '#0d0f16')
    for i, x in enumerate((0.1, 0.22, 0.34)):
        cv.rect(W * x, H * 0.5, W * 0.07, H * 0.12, '#fff3d6' if i != 1 else '#ffe2a8')
    cv.rect(W * 0.6, H * 0.5, 8, H * 0.24, '#1a1d27')
    demo.dot(cv, W * 0.6 + 4, H * 0.5, r=H * 0.035, color='#fffaf0')
    demo.word(cv, 'HALATION', W * 0.5, H * 0.32, size=150, color='#fbfbff', weight=900)
    sway = math.sin(t * 2.2) * W * 0.03
    demo.dot(cv, W * 0.82 + sway, H * 0.62, r=H * 0.05, color='#ffffff')


def _draw(n, cv):
    _night(cv, n / demo.FPS)
    p = demo.phase(n, 0.5, 2.0)
    halation(cv, amount=p * p * (3 - 2 * p))
    demo.word(cv, 'halation on' if p > 0 else 'halation off', 150, demo.H - 50, color=demo.MUTED,
              font=demo.mono(24))


TECHNIQUE = Technique(
    id='halation',
    name='Halation',
    family='vfx',
    group='Glow & light',
    aliases=('film halation', 'red halo', 'highlight bleed'),
    definition='Bright lights and white shapes pick up a soft red-orange glow that bleeds past their '
               'edges into the dark around them, like highlights on real film stock.',
    phrasings=('give the bright lights that reddish film glow around them',
               'make the highlights bleed orange like an old movie',
               'add a warm red fringe around the white text so it looks shot on film'),
    related=('fresnel-edge-glow', 'solarization', 'bloom', 'thin-film-iridescence', 'film-dissolve', 'rim-light'),
    api=('videobuilder.techniques.vfx.halation.halation',),
    demo=lambda: demo.film(_draw),
)
