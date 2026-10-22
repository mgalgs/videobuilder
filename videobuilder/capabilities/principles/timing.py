"""Timing: how long a move takes is what tells the viewer what moved. The same
slide over the same distance reads as light and quick in a few frames, and
as heavy or calm when it is stretched across a second or more."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# Named durations in seconds, from a flick to a heavy, deliberate move.
TIMINGS = {'snap': 0.25, 'quick': 0.45, 'natural': 0.8, 'calm': 1.3, 'heavy': 1.8}


def timed(t, start, timing='natural', ease=vb.ease_in_out_quart):
    """Eased progress 0 -> 1 at time `t` (seconds) of a move beginning at
    `start` and lasting `timing`: a name from `TIMINGS` or a number of
    seconds. Clamped either side, so it holds 0 before and 1 after."""
    seconds = TIMINGS[timing] if isinstance(timing, str) else float(timing)
    if seconds <= 0:
        return 1.0 if t >= start else 0.0
    return ease(vb.clamp01((t - start) / seconds))


LANES = (('snap', 14, demo.TEAL), ('natural', 20, demo.ACCENT), ('heavy', 30, demo.INK))


def draw(n, cv):
    t = n / demo.FPS
    x0, x1 = 210, demo.W - 90
    label = demo.mono(20, 600)
    for i, (name, r, color) in enumerate(LANES):
        y = demo.H / 2 + (i - 1) * 140
        cv.line(x0, y, x1, y, demo.LINE, width=2)
        cv.outline(x1 - r - 4, y - r - 4, 2 * r + 8, 2 * r + 8, demo.MUTED, width=1.5, radius=r + 4, alpha=0.5)
        vb.text.draw(cv, [f'{TIMINGS[name]:.2f} s'], label, 60, y - 24, demo.INK)
        vb.text.draw(cv, [name], demo.font(16, 500), 60, y + 2, demo.MUTED)
        x = x0 + (x1 - x0) * timed(t, 0.5, name)
        demo.dot(cv, x, y, r, color=color)
        cv.mark(name, x - r, y - r, 2 * r, 2 * r)


TECHNIQUE = Technique(
    id='timing',
    name='Timing',
    family='principles',
    group='Disney principles',
    aliases=('spacing and timing', 'duration', 'pacing'),
    definition='Choosing how many frames a move lasts so its speed tells the viewer how heavy, '
               'light, urgent or relaxed the thing moving is.',
    phrasings=('make the big one move slower so it feels heavier',
               'speed this up so it feels snappy',
               'give each move a duration that matches its weight'),
    related=('delay', 'time-remapping', 'freeze-frame', 'offset', 'distance-based-duration',
             'timecode-counter'),
    api=('videobuilder.techniques.principles.timing.timed',
         'videobuilder.techniques.principles.timing.TIMINGS'),
    demo=lambda: demo.film(draw),
)
