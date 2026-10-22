"""Seamless Loop: every moving thing is driven by a phase that wraps, and the
clip's length is a whole number of its cycles, so the frame after the last is
frame 0 again and the clip repeats forever with no jump."""
import math

from .. import _demo as demo
from ..schema import Technique


def loop_phase(n, frames, cycles=1, offset=0.0):
    """Frame `n` of a `frames`-long looping clip -> phase in [0, 1), going
    round `cycles` (a whole number) times across the clip, shifted by
    `offset` (a share of one cycle). Frame `frames` lands on the same phase
    as frame 0, so played on repeat the seam is invisible. Drive angles with
    `2 * pi * phase`, or waves with `loop_wave`."""
    if cycles != int(cycles):
        raise ValueError(f'cycles must be a whole number to loop cleanly, not {cycles}')
    return (n * cycles / frames + offset) % 1.0


def loop_wave(n, frames, cycles=1, offset=0.0):
    """A smooth -1 -> 1 -> -1 swing (a cosine) at `loop_phase`: -1 at phase 0,
    1 halfway. Use for anything that breathes, bobs or pulses in a loop."""
    return -math.cos(2 * math.pi * loop_phase(n, frames, cycles, offset))


FRAMES = round(demo.SECONDS * demo.FPS)


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H / 2 - 30, 160
    cv.arc(cx, cy, r, 0, 2 * math.pi, demo.MUTED, width=3, alpha=0.5)
    # the seam: where every cycle starts and ends
    top = cy - r
    cv.line(cx, top - 18, cx, top + 18, demo.MUTED, width=3)
    # an orbiting dot, twice round the clip, with a fading trail behind it
    p = loop_phase(n, FRAMES, cycles=2)
    for i in range(10, 0, -1):
        a = 2 * math.pi * (p - i * 0.012) - math.pi / 2
        demo.dot(cv, cx + r * math.cos(a), cy + r * math.sin(a), 20 * (1 - i / 14), color=demo.TEAL,
                 alpha=0.3 * (1 - i / 11))
    a = 2 * math.pi * p - math.pi / 2
    x, y = cx + r * math.cos(a), cy + r * math.sin(a)
    demo.dot(cv, x, y, 24)
    cv.mark('dot', x - 24, y - 24, 48, 48)
    # a centre pulse, once round the clip, peaking halfway
    s = 1 + 0.25 * loop_wave(n, FRAMES)
    demo.dot(cv, cx, cy, 32 * s, color=demo.TEAL, alpha=0.85)
    # a playhead that wraps back to the start, the clip's own loop
    x0, x1, by = cx - 220, cx + 220, demo.H - 50
    cv.line(x0, by, x1, by, demo.LINE, width=4)
    px = x0 + (x1 - x0) * n / FRAMES
    cv.rect(x0, by - 2, px - x0, 4, demo.MUTED)
    demo.dot(cv, px, by, 7, color=demo.INK)
    demo.word(cv, '\u21bb', x1 + 30, by, size=30, color=demo.MUTED, weight=700)


TECHNIQUE = Technique(
    id='seamless-loop',
    name='Seamless Loop',
    family='principles',
    group='Cycles & loops',
    aliases=('perfect loop', 'cyclic loop', 'looping animation'),
    definition='A clip whose motion runs in whole cycles so its last frame flows straight back into its first, '
               'letting it play on repeat with no visible jump.',
    phrasings=('make it loop forever without a hitch where it restarts',
               'an animation that can play on repeat with no jump at the end',
               'a GIF-style loop where you cannot tell where it starts'),
    related=('geometric-loop', 'interruptible-motion', 'empty-state-idle-loop', 'delay',
             'frame-by-frame-hand-drawn-animation', 'scroll-scrubbed-frame-sequence'),
    api=('videobuilder.techniques.principles.seamless_loop.loop_phase',
         'videobuilder.techniques.principles.seamless_loop.loop_wave'),
    demo=lambda: demo.film(draw),
)
