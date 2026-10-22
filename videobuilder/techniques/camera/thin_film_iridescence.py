"""Thin-film iridescence: a soap-film surface whose colour is light
interfering with itself inside a film a few hundred nanometres thick, so the
bands of magenta, gold, teal and blue shift as the viewing angle changes and
as the film's thickness swirls and drains."""
import math
from functools import lru_cache

import cairo
from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

N_FILM = 1.33          # refractive index of soapy water
MAX_NM = 1400.0        # thickest optical path the colour table covers
TABLE = 1024           # entries in that table


def _cmf(lam):
    """A rough wavelength (nm) -> linear RGB response, normalised later so a
    flat spectrum comes out white."""
    g = lambda c, s: math.exp(-((lam - c) / s) ** 2 / 2)  # noqa: E731
    return (g(600, 42) + 0.18 * g(445, 22), g(548, 40), g(452, 28))


@lru_cache(maxsize=1)
def _table():
    lams = range(400, 701, 6)
    weights = [_cmf(l) for l in lams]
    white = [sum(w[c] for w in weights) for c in range(3)]
    out = []
    for i in range(TABLE):
        d = MAX_NM * i / (TABLE - 1)
        rgb = [0.0, 0.0, 0.0]
        for lam, w in zip(lams, weights):
            r = math.sin(2 * math.pi * N_FILM * d / lam) ** 2   # reflectance of a film in air
            for c in range(3):
                rgb[c] += r * w[c]
        rgb = [v / white[c] for c, v in enumerate(rgb)]
        mean = sum(rgb) / 3
        rgb = [min(1.0, max(0.0, mean + (v - mean) * 1.45)) for v in rgb]   # push the saturation up
        out.append(tuple(v ** (1 / 2.2) for v in rgb))
    return out


def film_color(thickness_nm, cos_theta=1.0):
    """The colour (r, g, b in 0..1) a soap film `thickness_nm` thick reflects
    when seen at an angle whose cosine is `cos_theta` (1 = head on). Thicker
    film or a more glancing view shifts the colour along the interference
    series: black, silver, gold, magenta, blue, green, pink..."""
    sin_t = math.sqrt(max(0.0, 1 - cos_theta ** 2)) / N_FILM      # refracted angle inside the film
    d = thickness_nm * math.sqrt(1 - sin_t ** 2)
    i = round(min(1.0, max(0.0, d / MAX_NM)) * (TABLE - 1))
    return _table()[i]


def iridescent_sphere(size, view=0.0, swirl=0.0, thickness=(260, 900), sheen=0.6):
    """A `size`-pixel square `vb.Image` of a soap-film sphere: its colour at
    each point comes from `film_color`, with the film thin at the top and
    thicker toward the bottom (`thickness` nm, top to bottom) and stirred by
    slow eddies. `view` (-1 -> 1) turns the viewpoint left to right, which
    slides the bands across the surface; `swirl` (any number, animate it
    steadily) moves the eddies. Transparent outside the disc."""
    table = _table()
    ax = view * 0.75                                   # view direction's lean, radians
    vx, vz = math.sin(ax), math.cos(ax)
    t0, t1 = thickness
    px = bytearray(size * size * 4)
    half = size / 2
    edge = 1.5 / half
    k = 0
    for j in range(size):
        y = (j + 0.5 - half) / half
        for i in range(size):
            x = (i + 0.5 - half) / half
            r2 = x * x + y * y
            if r2 >= 1:
                k += 4
                continue
            nz = math.sqrt(1 - r2)
            cos_t = max(0.05, x * vx + nz * vz)
            lean = x * math.cos(0.3 * swirl) - y * math.sin(0.3 * swirl)
            d = (t0 + (t1 - t0) * (0.5 + 0.5 * y) ** 1.4
                 + 120 * math.sin(3.1 * lean + 2.3 * y + swirl)
                 + 70 * math.sin(5.3 * y - 2.0 * x + 1.7 * swirl))
            sin_t = math.sqrt(1 - cos_t * cos_t) / N_FILM
            opd = max(0.0, d) * math.sqrt(1 - sin_t * sin_t)
            r, g, b = table[min(TABLE - 1, int(opd / MAX_NM * (TABLE - 1)))]
            shade = sheen + (1 - sheen) * cos_t
            a = min(1.0, (1 - math.sqrt(r2)) / edge)
            px[k] = int(255 * r * shade)
            px[k + 1] = int(255 * g * shade)
            px[k + 2] = int(255 * b * shade)
            px[k + 3] = int(255 * a)
            k += 4
    return vb.Image.from_pil(Image.frombytes('RGBA', (size, size), bytes(px)))


def draw_iridescent_bubble(cv, cx, cy, r, view=0.0, swirl=0.0, thickness=(260, 900), alpha=1.0):
    """Draw a soap bubble of radius `r` centred at (cx, cy) with a
    thin-film iridescent skin (see `iridescent_sphere`), a dark rim and a
    specular highlight that follows `view`. Animate `view` and `swirl` to make
    the colours slide and churn. Rendered at the canvas's pixel scale."""
    size = max(8, min(320, round(2 * r * cv.scale_factor())))
    img = iridescent_sphere(size, view, swirl, thickness)
    cv.image(img, cx - r, cy - r, 2 * r, 2 * r, alpha=alpha)
    ctx = cv.ctx
    ctx.save()
    rim = cairo.RadialGradient(cx, cy, r * 0.82, cx, cy, r)
    rim.add_color_stop_rgba(0, 0, 0, 0, 0)
    rim.add_color_stop_rgba(1, 0, 0, 0, 0.35 * alpha)
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.set_source(rim)
    ctx.fill()
    hx, hy = cx - r * (0.42 + 0.25 * view), cy - r * 0.48
    spec = cairo.RadialGradient(hx, hy, 0, hx, hy, r * 0.24)
    spec.add_color_stop_rgba(0, 1, 1, 1, 0.9 * alpha)
    spec.add_color_stop_rgba(1, 1, 1, 1, 0)
    ctx.arc(hx, hy, r * 0.24, 0, 2 * math.pi)
    ctx.set_source(spec)
    ctx.fill()
    ctx.restore()
    cv.mark('bubble', cx - r, cy - r, 2 * r, 2 * r)


def draw(n, cv):
    t = n / demo.FPS
    view = math.sin(2 * math.pi * t / demo.SECONDS)      # the viewpoint swings right, back, left
    draw_iridescent_bubble(cv, demo.W / 2, demo.H / 2, demo.H * 0.36, view=view, swirl=1.6 * t)


TECHNIQUE = Technique(
    id='thin-film-iridescence',
    name='Thin-film iridescence',
    family='camera',
    group='Lighting & surface',
    aliases=('iridescence', 'oil-slick shimmer', 'soap bubble colours', 'interference colour'),
    definition='A surface is washed with rainbow bands, like a soap bubble or a slick of oil, and the '
               'colours slide and swap as the viewing angle or the film beneath them shifts.',
    phrasings=('make it shimmer with rainbow colours like a bubble',
               'give the sphere an oily rainbow sheen that changes as it turns',
               'a pearly, colour-shifting finish that moves with the light'),
    related=('fresnel-edge-glow', 'gooch-shading', 'heat-haze', 'chrome-specular-shimmer', 'film-dissolve',
             'shine-glint-sweep'),
    api=('videobuilder.techniques.camera.thin_film_iridescence.draw_iridescent_bubble',
         'videobuilder.techniques.camera.thin_film_iridescence.iridescent_sphere',
         'videobuilder.techniques.camera.thin_film_iridescence.film_color'),
    demo=lambda: demo.film(draw),
)
