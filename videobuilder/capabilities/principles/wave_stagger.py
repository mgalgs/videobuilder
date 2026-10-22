"""Wave Stagger: a row of items all bob through the same up-and-down cycle,
each one a little behind its neighbour, so a wave rolls along the row."""
import math

from .. import _demo as demo
from ..schema import Capability


def wave_stagger(t, i, period=1.2, lag=0.1, start=0.0):
    """Offset in [-1, 1] of item `i` at time `t` (seconds): one sine cycle
    every `period` seconds, item `i` running `i * lag` seconds behind item 0.
    Each item rests at 0 until the wave reaches it (`start + i * lag`), so the
    motion visibly sets off from the first item. Multiply by an amplitude in
    pixels, degrees or scale to move, tilt or pulse each item."""
    u = t - start - i * lag
    return 0.0 if u <= 0 else math.sin(2 * math.pi * u / period)


COUNT = 9


def draw(n, cv):
    t = n / demo.FPS
    gap = 100
    x0, cy, amp, r = demo.W / 2 - gap * (COUNT - 1) / 2, demo.H / 2, 120, 26
    for i in range(COUNT):
        x = x0 + i * gap
        cv.line(x, cy - amp - r, x, cy + amp + r, demo.LINE, width=2)  # each dot's track: it only moves up and down
        y = cy - amp * wave_stagger(t, i, period=1.3, lag=0.13, start=0.2)
        demo.dot(cv, x, y, r)
        cv.mark(f'dot{i}', x - r, y - r, 2 * r, 2 * r)


CAPABILITY = Capability(
    id='wave-stagger',
    name='Wave Stagger',
    family='principles',
    group='Stagger',
    aliases=('sine wave stagger', 'sequenced ripple', 'cascading wave', 'diagonal cascade'),
    definition='A row of items each bob up and down on the same repeating cycle, every one starting a beat '
               'after the one before it, so a wave seems to roll along the row.',
    phrasings=('make the dots move like a wave going across',
               'have the letters ripple up and down one after another',
               'offset each one a bit so the bounce travels down the line like a stadium wave'),
    related=('wave-deformer', 'sine-wave-text', 'linear-repeater-stagger', 'sine-wave-distortion',
             'oscillation', 'ocean-waves'),
    api=('videobuilder.capabilities.principles.wave_stagger.wave_stagger',),
    demo=lambda: demo.film(draw),
)
