"""Grid Wave Loader: a row of bars that each grow and shrink in turn, the
offsets between neighbours making a swell run along the row on a loop."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def wave_levels(count, t, period=1.2, spread=0.6, sharpness=2.0):
    """How tall each of `count` bars is at `t` seconds, as 0 -> 1 levels.
    Each bar pulses once per `period`; bar `i` lags the first by `spread *
    period * i / count`, so a swell travels left to right. `sharpness` above
    1 narrows the swell to a few bars. The pattern repeats every `period`."""
    out = []
    for i in range(count):
        ph = t / period - spread * i / count
        out.append((0.5 - 0.5 * math.cos(2 * math.pi * ph)) ** sharpness)
    return out


def draw_wave_loader(cv, cx, cy, t, count=9, bar=26, gap=14, low=26, high=150, color=demo.ACCENT,
                     peak=None, **kw):
    """Draw the loader centred at (cx, cy) at `t` seconds: `count` rounded
    bars `bar` wide, `gap` apart, each between `low` and `high` tall and
    centred on the row's midline. Bars near their crest wash over with `peak`
    (default: `color`). `kw` goes to `wave_levels`. Returns the row's Box."""
    total = count * bar + (count - 1) * gap
    x = cx - total / 2
    for v in wave_levels(count, t, **kw):
        h = low + (high - low) * v
        cv.rect(x, cy - h / 2, bar, h, color, radius=bar / 2)
        if peak:
            cv.rect(x, cy - h / 2, bar, h, peak, radius=bar / 2, alpha=vb.clamp01((v - 0.6) / 0.4))
        x += bar + gap
    return vb.Box(cx - total / 2, cy - high / 2, total, high)


def draw(n, cv):
    box = draw_wave_loader(cv, demo.W / 2, demo.H / 2, n / demo.FPS, count=11, bar=34, gap=18, low=34,
                           high=240, period=1.5, peak=demo.TEAL)
    cv.mark('loader', *box)


TECHNIQUE = Technique(
    id='grid-wave-loader',
    name='Grid wave loader',
    family='ui',
    group='Loaders',
    aliases=('bar wave', 'wave bars', 'square wave loader', 'traveling wave bars', 'sine bar wave'),
    definition='A waiting indicator made of a line of bars that stretch tall and sink back one after another, '
               'so a swell keeps rolling across them.',
    phrasings=('a loading animation where the bars rise and fall in a wave',
               'little bars pulsing one after the other like a ripple while it loads',
               'a row of blocks bobbing up and down in sequence as a spinner'),
    related=('scale-tile-wave', 'audio-waveform-bars', 'grid-diagonal-stagger', 'wave-stagger',
             'wave-function-collapse', 'wave-deformer'),
    api=('videobuilder.techniques.ui.grid_wave_loader.draw_wave_loader',
         'videobuilder.techniques.ui.grid_wave_loader.wave_levels'),
    demo=lambda: demo.film(draw),
)
