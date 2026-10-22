"""Sine Plasma: a few sine waves running across the frame at different
angles and speeds are added together, and the sum is looked up in a looping
colour ramp, so soft bands of colour swirl and merge without end."""
import math

from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# The demo's ramp: dark navy, a periwinkle glow, white hot, then gold and back.
PALETTE = ('#121633', '#6f7fe8', '#f4f4ff', '#f2b51c', '#3a2a08', '#121633')


def _rgb(color):
    c = color.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def plasma_ramp(colors=PALETTE, size=256):
    """A looping lookup table of `size` RGB tuples blending through `colors`
    (hex strings) evenly; repeat the first colour last for a seamless loop."""
    stops = [_rgb(c) for c in colors]
    out = []
    for i in range(size):
        x = i / size * (len(stops) - 1)
        k = min(int(x), len(stops) - 2)
        f = x - k
        a, b = stops[k], stops[k + 1]
        out.append(tuple(round(a[j] + (b[j] - a[j]) * f) for j in range(3)))
    return out


def plasma_field(w, h, t, scale=1.0, speed=1.0):
    """The plasma's value in [0, 1) at each of `w` x `h` cells at time `t`
    seconds, row by row. Four waves are summed: one along x, one along y,
    one diagonal and one rippling out from a centre that wanders, so the
    pattern never settles into stripes. `scale` sizes the blobs (bigger is
    larger), `speed` runs the motion faster or slower."""
    t *= speed
    k = 1 / (scale * max(w, h) / 10)
    xs = [math.sin(x * k * 1.3 + t * 1.1) for x in range(w)]
    ys = [math.sin(y * k * 1.7 - t * 0.9) for y in range(h)]
    cx, cy = w * (0.5 + 0.3 * math.sin(t * 0.43)), h * (0.5 + 0.3 * math.cos(t * 0.37))
    rows = []
    for y in range(h):
        sy, dy2 = ys[y], (y - cy) ** 2
        row = []
        for x in range(w):
            v = (xs[x] + sy + math.sin((x + y) * k * 0.9 + t * 0.7)
                 + math.sin(math.sqrt((x - cx) ** 2 + dy2) * k * 1.5 - t * 1.3))
            row.append((v / 8 + 0.5 + t * 0.05) % 1.0)  # the slow add drifts the colours round the ramp
        rows.append(row)
    return rows


def plasma_image(w, h, t, colors=PALETTE, scale=1.0, speed=1.0):
    """A `w` x `h` PIL RGB image of the plasma at time `t` (see
    `plasma_field`), coloured through `plasma_ramp(colors)`. Keep it small
    (a couple of hundred cells across) and let the canvas smooth it up."""
    ramp = plasma_ramp(colors)
    n = len(ramp)
    im = Image.new('RGB', (w, h))
    im.putdata([ramp[int(v * n)] for row in plasma_field(w, h, t, scale, speed) for v in row])
    return im


def draw_plasma(cv, box, t, colors=PALETTE, cells=160, scale=1.0, speed=1.0, alpha=1.0):
    """Fill `box` (a `vb.Box`) with sine plasma at time `t` seconds. The field
    is computed on a grid `cells` wide and stretched smooth over the box;
    `colors`, `scale` and `speed` as in `plasma_image`."""
    gw = max(2, int(cells))
    gh = max(2, round(gw * box.h / box.w))
    img = vb.Image.from_pil(plasma_image(gw, gh, t, colors, scale, speed))
    cv.image(img, box.x, box.y, box.w, box.h, alpha=alpha)


def draw(n, cv):
    box = vb.Box(0, 0, demo.W, demo.H)
    draw_plasma(cv, box, n / demo.FPS * 1.6, scale=0.7)
    cv.mark('plasma', *box)


TECHNIQUE = Technique(
    id='sine-plasma',
    name='Sine plasma',
    family='particles',
    group='Fire & plasma',
    aliases=('plasma effect', 'demoscene plasma', 'color plasma'),
    definition='Several overlapping sine waves are added up and run through a colour ramp, '
               'so the whole frame fills with soft, glowing bands that ooze and swirl into each other.',
    phrasings=('a retro demoscene plasma background with colours flowing around',
               'psychedelic blobs of colour that melt and morph into one another',
               'a lava-lamp style swirling colour field behind the title'),
    related=('sine-wave-distortion', 'sine-wave-text', 'wave-deformer', 'electric-arc', 'ripple',
             'thin-film-iridescence'),
    api=('videobuilder.techniques.particles.sine_plasma.draw_plasma',
         'videobuilder.techniques.particles.sine_plasma.plasma_image',
         'videobuilder.techniques.particles.sine_plasma.plasma_field'),
    demo=lambda: demo.film(draw),
)
