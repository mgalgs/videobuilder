"""Color cycling: a still picture painted from an indexed palette, whose
colours are rotated one slot every few frames, so bands seem to flow while
no shape moves."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique


def ramp(stops, steps):
    """`steps` colours blended evenly through the hex or RGB `stops` and back
    to the first, so the ramp wraps without a seam. Returns 0-255 RGB tuples."""
    cols = [rgba(s)[:3] for s in stops]
    out = []
    for i in range(steps):
        t = i / steps * len(cols)
        k, f = int(t), t - int(t)
        a, b = cols[k % len(cols)], cols[(k + 1) % len(cols)]
        out.append(tuple(round(255 * (x + (y - x) * f)) for x, y in zip(a, b)))
    return out


def cycled(palette, index, shift):
    """The colour palette slot `index` shows after rotating `palette` by
    `shift` slots. Whole slots only: a fractional shift snaps down, as real
    palette rotation steps rather than blends."""
    return palette[(index - math.floor(shift)) % len(palette)]


def cycle_shift(t, rate=8.0):
    """Slots rotated by time `t` seconds at `rate` slots a second."""
    return t * rate


def draw_cycled_bands(cv, cx, cy, radius, palette, shift, bands=None, wobble=0.12, lobes=5, seed=1.3):
    """A fixed blob of concentric bands centred at (cx, cy), band `i` from
    the outside painted `cycled(palette, i, shift)`. The outline never
    changes; only `shift` does, so the colours ripple inward while the
    shape stays put. `wobble` (0 = circles) and `lobes` shape the rim.
    Returns the Box of the blob."""
    bands = bands or len(palette)
    c = cv.ctx
    for i in range(bands):
        r = radius * (1 - i / bands)
        c.new_path()
        for j in range(97):
            a = j / 96 * 2 * math.pi
            k = 1 + wobble * (1 - 0.6 * i / bands) * (0.6 * math.sin(lobes * a + seed)
                                                      + 0.4 * math.sin((lobes - 2) * a - 2 * seed))
            x, y = cx + r * k * math.cos(a), cy + r * k * math.sin(a)
            c.line_to(x, y) if j else c.move_to(x, y)
        c.close_path()
        c.set_source_rgba(*rgba(cycled(palette, i, shift)))
        c.fill()
    reach = radius * (1 + wobble)
    return vb.Box(cx - reach, cy - reach, 2 * reach, 2 * reach)


PALETTE = ramp(('#2a2c6b', '#6b6ff0', demo.INK, '#f2b705', demo.ACCENT), 10)


def draw(n, cv):
    shift = cycle_shift(n / demo.FPS)
    box = draw_cycled_bands(cv, demo.W / 2, demo.H / 2 - 30, demo.H * 0.36, PALETTE, shift,
                            bands=2 * len(PALETTE))  # the palette twice, outside in
    cv.mark('bands', *box)
    # the palette itself, rotating under the picture
    sw, y = 44, demo.H - 70
    x0 = demo.W / 2 - sw * len(PALETTE) / 2
    for i in range(len(PALETTE)):
        cv.rect(x0 + i * sw + 2, y, sw - 4, 26, cycled(PALETTE, i, shift), radius=4)
    cv.mark('palette', x0, y, sw * len(PALETTE), 26)


TECHNIQUE = Technique(
    id='color-cycling',
    name='Color cycling',
    family='shapes',
    group='Gradients & color',
    aliases=('palette cycling', 'palette rotation', 'palette animation', 'hue rotation', 'color rotation loop'),
    definition='A still image whose palette is rotated a step at a time, so stripes of colour seem '
               'to stream through it although no shape moves.',
    phrasings=('make the colours flow through the rings without the shape moving',
               'rotate the palette so the stripes ripple like an old pixel-art waterfall',
               'loop the colours round and round through the bands'),
    related=('hue-cycle-fill', 'channel-shuffle', 'cross-processing', 'swirl',
             'scroll-linked-background-shift', 'gradient-shift-button'),
    api=('videobuilder.techniques.shapes.color_cycling.draw_cycled_bands',
         'videobuilder.techniques.shapes.color_cycling.cycled',
         'videobuilder.techniques.shapes.color_cycling.ramp',
         'videobuilder.techniques.shapes.color_cycling.cycle_shift'),
    demo=lambda: demo.film(draw),
)
