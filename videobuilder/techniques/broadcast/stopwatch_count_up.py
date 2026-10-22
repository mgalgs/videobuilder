"""Stopwatch Count-up: an elapsed-time readout starts at zero and runs up at
a steady rate, the hundredths blurring, the seconds ticking over and the
minutes carrying, like a race clock. Unlike a number count-up it is not
eased: the readout is the time itself."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

DIGITS = '0123456789'


def stopwatch_text(seconds, places=2, hours=False):
    """Elapsed `seconds` as a stopwatch reads it: 'MM:SS.cc' with `places`
    fractional digits (0 drops the point), or 'H:MM:SS.cc' when `hours` is
    true or the time passes an hour. The fraction is truncated, never
    rounded, so the readout only shows a second once it has fully elapsed."""
    seconds = max(0.0, seconds)
    unit = 10 ** places
    ticks = int(math.floor(seconds * unit + 1e-6))
    whole, frac = divmod(ticks, unit)
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    text = f'{h}:{m:02d}:{s:02d}' if hours or h else f'{m:02d}:{s:02d}'
    return text + (f'.{frac:0{places}d}' if places else '')


def elapsed(t, start=0.0, rate=1.0, stop=None):
    """Seconds on a stopwatch started at film time `start` and running at
    `rate` (2.0 runs twice as fast as real time), frozen at film time `stop`
    if given. Zero before `start`."""
    if stop is not None:
        t = min(t, stop)
    return max(0.0, t - start) * rate


def draw_stopwatch(cv, seconds, font, x, y, color, places=2, hours=False, align='left', alpha=1.0):
    """Draw `stopwatch_text(seconds)` with every digit centred in a cell as wide
    as the font's widest digit, so the readout never jitters as it runs.
    `align='left'` puts the first character at `x`, `'center'` centres the
    readout on `x`, `'right'` ends it at `x`; `y` is the top. Returns the Box."""
    s = stopwatch_text(seconds, places, hours)
    cell = max(vb.text.measure(d, font) for d in DIGITS)
    widths = [cell if ch in DIGITS else vb.text.measure(ch, font) for ch in s]
    total = sum(widths)
    left = {'left': x, 'center': x - total / 2, 'right': x - total}[align]
    cx = left
    for ch, w in zip(s, widths):
        vb.text.draw(cv, [ch], font, cx + (w - vb.text.measure(ch, font)) / 2, y, color, alpha=alpha)
        cx += w
    return vb.Box(left, y, total, vb.text.line_height(font))


# ---- the demo: a race-clock panel, its seconds hand sweeping beside the readout ----

START = 0.3


def draw(n, cv):
    t = elapsed(n / demo.FPS, START)
    pw, ph = 720, 220
    px, py = (demo.W - pw) / 2, (demo.H - ph) / 2
    cv.shadow(px, py, pw, ph, radius=22, dy=10, blur=32, color=(0, 0, 0, 0.5))
    cv.rect(px, py, pw, ph, '#1c1e25', radius=22)
    cv.outline(px, py, pw, ph, demo.LINE, width=2, radius=22)

    # a small dial whose hand goes round once a second
    cx, cy, r = px + 110, py + ph / 2, 64
    cv.arc(cx, cy, r, 0, 2 * math.pi, demo.LINE, width=8)
    frac = t % 1.0
    if t > 0:
        cv.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * frac, demo.ACCENT, width=8)
    a = -math.pi / 2 + 2 * math.pi * frac
    cv.line(cx, cy, cx + (r - 16) * math.cos(a), cy + (r - 16) * math.sin(a), demo.INK, width=4)
    demo.dot(cv, cx, cy, r=7, color=demo.INK)

    f = demo.mono(96, 700)
    top = cy - vb.text.line_height(f) / 2 + 14
    box = draw_stopwatch(cv, t, f, px + 214, top, demo.INK)
    cv.mark('readout', *box)
    vb.text.draw(cv, ['ELAPSED'], demo.font(20, 800), px + 218, py + 36, demo.ACCENT)
    if t > 0:
        demo.dot(cv, px + pw - 40, py + 44, r=7, color=demo.ACCENT, alpha=0.55 + 0.45 * (int(t * 2) % 2 == 0))


TECHNIQUE = Technique(
    id='stopwatch-count-up',
    name='Stopwatch count-up',
    family='broadcast',
    group='Timers & indicators',
    aliases=('elapsed timer', 'running clock', 'race clock', 'chronometer readout'),
    definition='A time readout starts at zero and climbs steadily in minutes, seconds and hundredths, '
               'showing how long has passed since the clock was started.',
    phrasings=('put a running timer on screen that counts up from zero',
               'show the elapsed time ticking in hundredths like a stopwatch',
               'add a race clock in the corner that keeps going'),
    related=('number-count-down', 'number-count-up', 'game-clock-countdown', 'timing',
             'decimal-counter-with-formatting', 'delay'),
    api=('videobuilder.techniques.broadcast.stopwatch_count_up.draw_stopwatch',
         'videobuilder.techniques.broadcast.stopwatch_count_up.stopwatch_text',
         'videobuilder.techniques.broadcast.stopwatch_count_up.elapsed'),
    demo=lambda: demo.film(draw),
)
