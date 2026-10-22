"""Physarum slime mold: thousands of tiny agents each lay a trail and steer
toward the strongest trail just ahead of them, so a speckled haze organises
itself into a web of glowing veins, and the busiest veins thicken while the
rest wither away."""
import math
import random
from functools import lru_cache

from PIL import Image as PILImage
from PIL import ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def physarum(width, height, steps, agents=6000, seed=0, spawn=None, food=(), sensor=(6.0, 6.0),
             sensor_angle=0.6, turn=0.45, speed=1.0, deposit=40, decay=0.9, food_deposit=255):
    """Run a Physarum (slime mold) agent simulation on a `width` x `height`
    grid and return the trail map after each of `steps` steps, as a list of
    8-bit greyscale `bytes` (row-major, 0 = empty, 255 = a saturated vein).

    Each agent smells the trail at three points `sensor` cells ahead (left,
    straight on, right, `sensor_angle` radians apart), turns by `turn`
    toward the strongest, moves `speed` cells and drops `deposit` of trail.
    Each step the whole map is blurred one cell (diffusion) and multiplied by
    `decay`, so unused paths fade. `sensor` is (start, end): the reach grows
    from one to the other over the run, which coarsens a fine mesh into a few
    thick veins. `spawn` is (cx, cy, r), a disc the agents start scattered
    in (default: the whole grid); `food` is (x, y) cells that keep emitting
    `food_deposit`, so the network grows to link them. Seeded, so the same
    arguments always give the same frames."""
    rnd = random.Random(seed)
    cx, cy, r = spawn or (width / 2, height / 2, max(width, height))
    xs, ys, hs = [], [], []
    while len(xs) < agents:
        a, d = rnd.uniform(0, 2 * math.pi), r * math.sqrt(rnd.random())
        x, y = cx + d * math.cos(a), cy + d * math.sin(a)
        if 0 <= x < width and 0 <= y < height:
            xs.append(x)
            ys.append(y)
            hs.append(rnd.uniform(0, 2 * math.pi))
    trail = bytearray(width * height)
    lut = [int(v * decay) for v in range(256)]
    blur = ImageFilter.BoxBlur(1)
    food = [(int(fx) % width) + (int(fy) % height) * width for fx, fy in food]
    out = []
    for s in range(steps):
        reach = sensor[0] + (sensor[1] - sensor[0]) * (s / max(1, steps - 1))

        def smell(x, y, h):
            return trail[int(x + reach * math.cos(h)) % width + (int(y + reach * math.sin(h)) % height) * width]

        for i in range(agents):
            x, y, h = xs[i], ys[i], hs[i]
            c = smell(x, y, h)
            lt = smell(x, y, h - sensor_angle)
            rt = smell(x, y, h + sensor_angle)
            if c >= lt and c >= rt:
                pass
            elif lt > rt:
                h -= turn
            elif rt > lt:
                h += turn
            else:
                h += turn if rnd.random() < 0.5 else -turn
            x = (x + speed * math.cos(h)) % width
            y = (y + speed * math.sin(h)) % height
            xs[i], ys[i], hs[i] = x, y, h
            k = int(x) + int(y) * width
            v = trail[k] + deposit
            trail[k] = v if v < 255 else 255
        for k in food:
            trail[k] = food_deposit
        img = PILImage.frombytes('L', (width, height), bytes(trail)).filter(blur).point(lut)
        trail = bytearray(img.tobytes())
        out.append(bytes(trail))
    return out


def _hex(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def trail_image(trail, width, height, colors=(demo.BG, '#3b3f8f', '#f2b630', '#fff6dc'), size=None):
    """A trail map from `physarum` as a `vb.Image`: values run through the
    `colors` ramp (empty -> faint -> vein -> hot core), smoothly upscaled to
    `size` (w, h) if given. Draw it with `cv.image`."""
    stops = [_hex(c) for c in colors]
    pal = []
    for v in range(256):
        t = (v / 255) ** 0.6 * (len(stops) - 1)
        i = min(int(t), len(stops) - 2)
        f = t - i
        pal += [round(stops[i][j] + (stops[i + 1][j] - stops[i][j]) * f) for j in range(3)]
    img = PILImage.frombytes('L', (width, height), trail)
    img = img.convert('P')
    img.putpalette(pal)
    img = img.convert('RGB')
    if size:
        img = img.resize(size, PILImage.BICUBIC)
    return vb.Image.from_pil(img)


GW, GH = 256, 144


@lru_cache(maxsize=1)
def _trails():
    return physarum(GW, GH, demo.FPS * 3, agents=5000, seed=7, spawn=(GW / 2, GH / 2, 64),
                    sensor=(4.0, 11.0))


@lru_cache(maxsize=None)
def _frame(n):
    return trail_image(_trails()[n], GW, GH, size=(GW * 4, GH * 4))


def draw(n, cv):
    cv.image(_frame(min(n, demo.FPS * 3 - 1)), 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='physarum-slime-mold',
    name='Physarum slime mold',
    family='particles',
    group='Swarms & agents',
    aliases=('slime mold network', 'Physarum transport network', 'slime mould simulation'),
    definition='A cloud of tiny agents that follow and reinforce each other\'s trails, so a speckled haze '
               'draws itself into a glowing web of veins whose busy paths thicken and quiet ones fade.',
    phrasings=('grow an organic vein network like slime mold spreading out',
               'particles that leave trails and clump into branching paths',
               'a living web of glowing tendrils that links up some dots'),
    related=('diffusion-limited-aggregation', 'space-colonization', 'morphing-blob', 'noise-vertex-wobble',
             'springs-network', 'connector-network'),
    api=('videobuilder.capabilities.particles.physarum_slime_mold.physarum',
         'videobuilder.capabilities.particles.physarum_slime_mold.trail_image'),
    demo=lambda: demo.film(draw),
)
