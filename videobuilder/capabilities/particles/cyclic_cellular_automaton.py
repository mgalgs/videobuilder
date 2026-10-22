"""Cyclic Cellular Automaton: a grid of cells, each holding one of `states`
colours arranged in a ring. A cell steps on to the next colour when enough of
its neighbours already show it, so random noise clumps into blobs, then into
waves and spinning spirals that cycle through the ring for ever."""
import colorsys
import random
from functools import lru_cache

from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _neighbours(width, height, moore):
    offsets = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if moore:
        offsets += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    return [tuple(((y + dy) % height) * width + (x + dx) % width for dx, dy in offsets)
            for y in range(height) for x in range(width)]


def cca_step(cells, width, height, states=14, threshold=1, moore=False, neighbours=None):
    """One generation: `cells` (a `bytes` of `width * height` states, row by
    row, wrapping at the edges) to the next. A cell in state `s` moves to
    `(s + 1) % states` when at least `threshold` of its four neighbours (eight
    if `moore`) are already there. `neighbours` is a precomputed table from
    `_neighbours`, to save rebuilding it each step."""
    nb = neighbours or _neighbours(width, height, moore)
    out = bytearray(cells)
    for i, s in enumerate(cells):
        nxt = s + 1 if s + 1 < states else 0
        k = 0
        for j in nb[i]:
            if cells[j] == nxt:
                k += 1
                if k >= threshold:
                    out[i] = nxt
                    break
    return bytes(out)


@lru_cache(maxsize=4)
def cca_run(width, height, generations, states=14, threshold=1, moore=False, seed=0):
    """Every generation from a random start to `generations`, as a tuple of
    `bytes` (index 0 is the noise). Cached, so a film's `draw` can index it per
    frame. The defaults (14 states, 1 of 4 neighbours) settle into spirals
    after about 200 generations on a 160 x 90 grid."""
    rng = random.Random(seed)
    cells = bytes(rng.randrange(states) for _ in range(width * height))
    nb = _neighbours(width, height, moore)
    out = [cells]
    for _ in range(generations):
        cells = cca_step(cells, width, height, states, threshold, moore, nb)
        out.append(cells)
    return tuple(out)


def cca_palette(states, saturation=0.55, value=0.92, hue=0.0):
    """`states` RGB colours evenly round the colour wheel, so the last runs
    back into the first like the states do."""
    return [tuple(round(c * 255) for c in colorsys.hsv_to_rgb((hue + k / states) % 1, saturation, value))
            for k in range(states)]


def draw_cca(cv, cells, width, height, x, y, w, h, palette, alpha=1.0):
    """Draw one generation `cells` as hard-edged blocks filling the box
    (x, y, w, h), state `s` in `palette[s]`."""
    small = PILImage.new('RGB', (width, height))
    small.putdata([palette[s] for s in cells])
    scale = max(1, round(w * cv.scale_factor() / width))
    img = vb.Image.from_pil(small.resize((width * scale, height * scale), PILImage.NEAREST))
    cv.image(img, x, y, w, h, alpha=alpha)


GRID_W, GRID_H, STATES = 160, 90, 14
PALETTE = cca_palette(STATES)


def _generation(n):
    # Fast through the noise and the first clumps, then two generations a frame
    # so the settled spirals are seen turning.
    split = 40
    return 5 * n if n < split else 5 * split + 2 * (n - split)


def draw(n, cv):
    gens = cca_run(GRID_W, GRID_H, _generation(round(demo.SECONDS * demo.FPS)), STATES, seed=3)
    draw_cca(cv, gens[_generation(n)], GRID_W, GRID_H, 0, 0, demo.W, demo.H, PALETTE)
    cv.mark('grid', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='cyclic-cellular-automaton',
    name='Cyclic cellular automaton',
    family='particles',
    group='Cellular automata',
    aliases=('CCA', 'cyclic CA', 'cyclic automaton spirals'),
    definition='A grid of coloured cells where each one advances to the next colour in a loop when a '
               'neighbour already holds it, so random static organises itself into rotating spirals.',
    phrasings=('random pixel noise that self-organises into spinning rainbow spirals',
               'a grid of cells that keeps cycling through colours until waves and spirals emerge',
               'a generative cellular pattern where colour bands chase each other round in loops'),
    related=('hop-cycle', 'cycle-diagram-rotation', 'geometric-loop', 'thomas-attractor',
             'rotating-polygon-loop', 'seamless-loop'),
    api=('videobuilder.capabilities.particles.cyclic_cellular_automaton.draw_cca',
         'videobuilder.capabilities.particles.cyclic_cellular_automaton.cca_run',
         'videobuilder.capabilities.particles.cyclic_cellular_automaton.cca_step',
         'videobuilder.capabilities.particles.cyclic_cellular_automaton.cca_palette'),
    demo=lambda: demo.film(draw),
)
