"""Doom-style fire: a coarse grid of heat values where a white-hot bottom row
feeds every cell above it, each cell copying the one below with a random
sideways nudge and a little cooling, so ragged pixel flames lick upwards
through a black-red-orange-yellow-white ramp."""
import random

from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

HOT = 36  # the hottest heat value; 0 is cold


def _ramp(stops, levels):
    out = []
    for i in range(levels):
        t = i / (levels - 1) * (len(stops) - 1)
        k = min(int(t), len(stops) - 2)
        f = t - k
        a, b = stops[k], stops[k + 1]
        out.append(tuple(round(a[j] + (b[j] - a[j]) * f) for j in range(3)))
    return tuple(out)


# Embers to white heat, weighted to reds and oranges: white only at the very hottest.
PALETTE = _ramp(((12, 7, 7), (70, 10, 8), (135, 24, 8), (190, 50, 8), (215, 80, 10), (225, 110, 16),
                 (230, 140, 26), (235, 175, 45), (245, 215, 100), (255, 255, 235)), HOT + 1)

_runs = {}  # (cols, rows, seed, douse, cooling) -> [heat grid per step]: frames are drawn in any order


def fire_heat(step, cols=160, rows=90, seed=0, douse=None, cooling=1):
    """The heat grid after `step` steps of the fire, as a bytes of
    `cols * rows` values 0..HOT, row by row from the top. The bottom row
    burns at HOT until step `douse` (None: forever), then goes cold and the
    flames die back. Each step every cell above the bottom takes the heat of
    the cell below it, shifted sideways by -2..+1 and cooled by 0 to
    `cooling` at random: 1 is the original's tall blaze, 2 or 3 give shorter,
    more ragged tongues. The same arguments give the same grid; runs are cached, so
    asking for steps in order costs one step each."""
    key = cols, rows, seed, douse, cooling
    if key not in _runs:
        _runs[key] = [bytes(cols * rows)], random.Random(seed)
    states, rng = _runs[key]
    size = cols * rows
    while len(states) <= step:
        heat = bytearray(states[-1])
        src = HOT if douse is None or len(states) <= douse else 0
        heat[size - cols:] = bytes([src]) * cols
        noise = rng.randbytes(size)
        for i in range(cols, size):
            r = noise[i] & 3
            j = i - r + 1 - cols
            if cols <= j + cols < size:
                v = heat[i] - (noise[i] >> 2) % (cooling + 1)
                heat[j] = v if v > 0 else 0
        states.append(bytes(heat))
    return states[step]


def draw_doom_fire(cv, x, y, w, h, step, cols=160, rows=90, seed=0, douse=None, cooling=1,
                   palette=PALETTE, transparent=True, alpha=1.0):
    """Draw the fire at `step` (see `fire_heat`) into the box (x, y, w, h)
    as hard-edged pixels. `transparent` leaves cold cells see-through so the
    fire burns over whatever is behind it; otherwise they take `palette[0]`.
    Returns the Box."""
    heat = fire_heat(step, cols, rows, seed, douse, cooling)
    lut = [bytes(c) + bytes([0 if transparent and v == 0 else 255]) for v, c in enumerate(palette)]
    img = PILImage.frombytes('RGBA', (cols, rows), b''.join(lut[v] for v in heat))
    s = cv.scale_factor()
    px = max(cols, round(w * s)), max(rows, round(h * s))
    cv.image(vb.Image.from_pil(img.resize(px, PILImage.NEAREST)), x, y, w, h, alpha=alpha)
    return vb.Box(x, y, w, h)


STEPS_PER_FRAME = 2


def draw(n, cv):
    # Lit at frame 0, the flames climb and roar, then the source is put out at 2.2 s and they sink.
    box = draw_doom_fire(cv, 0, 0, demo.W, demo.H, n * STEPS_PER_FRAME, seed=3,
                         douse=round(2.2 * demo.FPS) * STEPS_PER_FRAME)
    cv.mark('fire', *box)


CAPABILITY = Capability(
    id='doom-style-fire',
    name='Doom-style fire',
    family='particles',
    group='Fire & plasma',
    aliases=('demoscene fire', 'PSX Doom fire', 'pixel fire', 'cellular fire effect'),
    definition='Chunky retro pixels of heat rise from a blazing bottom edge, each row cooling and '
               'drifting at random, so jagged flames flicker up from white through yellow and orange to red and black.',
    phrasings=('an old-school pixelated fire burning up from the bottom of the screen',
               'that retro game title-screen fire made of big pixels',
               'a low-res flickering blaze like the one in classic 90s shooters'),
    related=('fire-overlay', 'heat-haze', 'fireworks', 'burning-ship-fractal', 'smoke-simulation', 'line-boil'),
    api=('videobuilder.capabilities.particles.doom_style_fire.draw_doom_fire',
         'videobuilder.capabilities.particles.doom_style_fire.fire_heat'),
    demo=lambda: demo.film(draw),
)
