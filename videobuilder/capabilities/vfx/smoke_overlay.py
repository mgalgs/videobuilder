"""Smoke overlay: a see-through layer of soft smoke wisps laid over a shot,
sliding across it on a breeze so the picture underneath keeps being veiled
and revealed."""
from functools import lru_cache

import numpy as np
from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...canvas import rgba

TILE = (96, 192)  # rows, cols of one wrap-around smoke texture


@lru_cache(maxsize=16)
def smoke_texture(seed=0, scale=6.0, stretch=2.5, coverage=0.5):
    """A wrap-around smoke density texture, a float array of shape `TILE`
    in 0 -> 1: smoothed noise whose blobs are about `scale` cells tall and
    `stretch` times as wide (long, wispy streaks), then cut so only about
    `coverage` of it holds smoke, with clear gaps between the wisps. It
    tiles seamlessly in both directions, so it can scroll forever."""
    rows, cols = TILE
    rnd = np.random.default_rng(seed)
    fy = np.fft.fftfreq(rows)[:, None]
    fx = np.fft.fftfreq(cols)[None, :]
    total = np.zeros(TILE)
    for octave, amp in ((1, 1.0), (2, 0.3), (4, 0.1)):  # a soft base plus finer ragged edges
        s = scale / octave
        lowpass = np.exp(-2 * np.pi ** 2 * ((fy * s) ** 2 + (fx * s * stretch) ** 2))
        layer = np.real(np.fft.ifft2(np.fft.fft2(rnd.standard_normal(TILE)) * lowpass))
        total += amp * layer / layer.std()
    cut = np.quantile(total, 1 - coverage)
    top = np.quantile(total, 0.995)
    d = np.clip((total - cut) / (top - cut), 0, 1)
    return d * d * (3 - 2 * d)  # smoothstep: feathered edges, denser cores


def _shifted(tex, dx, dy):
    """`tex` scrolled by (dx, dy) cells, wrapping, with bilinear sub-cell motion."""
    ix, iy = int(np.floor(dx)), int(np.floor(dy))
    fx, fy = dx - ix, dy - iy
    a = np.roll(tex, (iy, ix), axis=(0, 1))
    b = np.roll(a, 1, axis=1)
    top = a * (1 - fx) + b * fx
    return top * (1 - fy) + np.roll(top, 1, axis=0) * fy


def smoke_density(t, layers=3, wind=(70.0, -6.0), size=520.0, coverage=0.5, seed=0):
    """The overlay's smoke density at `t` seconds, a `TILE`-shaped float
    array in 0 -> 1 that tiles the frame. Each of `layers` textures drifts
    with `wind` (px per second, frame-sized: `size` px per tile height) at
    its own speed and height, near layers faster and larger than far ones,
    so the wisps slide past each other and the smoke churns instead of
    moving as one sheet."""
    rows, cols = TILE
    out = np.zeros(TILE)
    for i in range(layers):
        depth = 1.0 - 0.28 * i  # 1 for the nearest layer, smaller further back
        tex = smoke_texture(seed * 7 + i, scale=9.0 * depth + 3, coverage=coverage)
        px = rows / size
        dx = wind[0] * t * depth * px + 37.0 * i
        dy = wind[1] * t * depth * px + 11.0 * i + 1.5 * np.sin(t * 0.9 + i * 2.1)
        out = 1 - (1 - out) * (1 - _shifted(tex, dx, dy) * (0.55 + 0.45 * depth))  # screen the layers
    return out


def smoke_overlay(cv, t, x=0, y=0, w=None, h=None, color='#d9dce4', strength=0.75, layers=3,
                  wind=(70.0, -6.0), coverage=0.5, seed=0):
    """Lay drifting smoke over whatever is already drawn in the box (x, y,
    w, h) (default: the whole canvas) as it is `t` seconds in. The smoke is
    `color` at up to `strength` opacity where it is thickest and clear
    between the wisps; `wind` (px per second) carries it, `coverage` is
    roughly how much of the frame it veils, and `layers` drifting sheets
    give it depth. The same `seed` and `t` always give the same frame, so
    draw it last in any `draw(n, cv)` with `t = n / fps`."""
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    dens = smoke_density(t, layers, wind, size=h, coverage=coverage, seed=seed)
    rows, cols = TILE
    # The tile is `rows` cells to `h` px; repeat it sideways to fill wider boxes.
    need = int(np.ceil(w / (h * cols / rows) * cols)) + 1
    dens = np.tile(dens, (1, need // cols + 1))[:, :need]
    alpha = (np.clip(dens * strength, 0, 1) * 255).astype(np.uint8)
    red, green, blue, _ = (round(255 * c) for c in rgba(color))
    img = Image.new('RGBA', (need, rows), (red, green, blue, 0))
    img.putalpha(Image.fromarray(alpha, 'L'))
    big = img.resize((max(2, round(need * 4)), rows * 4), Image.BICUBIC)
    cell = h / rows
    with cv.clip(x, y, w, h):
        cv.image(vb.Image.from_pil(big), x, y, need * cell, h)
    return vb.Box(x, y, w, h)


def _scene(cv):
    """Something to see through the smoke: a photo with a title card on it."""
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    demo.card(cv, demo.W / 2, demo.H / 2 + 20, w=420, h=250, color=demo.TEAL)


def draw(n, cv):
    _scene(cv)
    t = n / demo.FPS
    box = smoke_overlay(cv, t + 2.0, wind=(260.0, -20.0), strength=0.8, coverage=0.45, seed=5)
    cv.mark('smoke', *box)


CAPABILITY = Capability(
    id='smoke-overlay',
    name='Smoke overlay',
    family='vfx',
    group='Particle & weather overlays',
    aliases=('smoke plate', 'smoke layer', 'drifting smoke'),
    definition='A translucent layer of soft, wispy smoke slides across the whole picture, thickening and '
               'thinning so the shot behind it is half hidden and half seen.',
    phrasings=('put some smoke drifting over the footage',
               'add a hazy wisp layer that rolls across the screen',
               'make it look like smoke is blowing past in front of the scene'),
    related=('smoke-dissolve', 'smoke-puffs', 'heat-haze', 'lens-dirt-overlay', 'layered-fog-bands',
             'smoke-simulation'),
    api=('videobuilder.capabilities.vfx.smoke_overlay.smoke_overlay',
         'videobuilder.capabilities.vfx.smoke_overlay.smoke_density',
         'videobuilder.capabilities.vfx.smoke_overlay.smoke_texture'),
    demo=lambda: demo.film(draw),
)
