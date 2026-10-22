"""Retiming: an animation that already exists is played back on a new clock,
holding its path but changing its pace -- here normal speed, then slow
motion, then a fast catch-up -- by mapping output time to source time."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def retime(t, keys):
    """Output time `t` -> source time, through `keys`: `(output, source)`
    pairs in increasing output order. Between keys the source clock runs at a
    constant speed (the slope); before the first key and after the last it
    holds. A key's slope below 1 is slow motion, above 1 fast motion, 0 a
    freeze, negative a rewind.

    In a film, wrap the time an animation reads, e.g.
    `draw_move(cv, retime(n / fps, ((0, 0), (1, 1), (2, 1.3), (2.5, 2.5))))`."""
    keys = tuple(keys)
    if not keys:
        raise ValueError('retime needs at least one (output, source) key')
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, s0), (t1, s1) in zip(keys, keys[1:]):
        if t <= t1:
            return s0 if t1 == t0 else s0 + (s1 - s0) * (t - t0) / (t1 - t0)
    return keys[-1][1]


def speed(t, keys):
    """How fast the source clock runs at output time `t` under `keys`
    (1 = as authored, 0 = held)."""
    for (t0, s0), (t1, s1) in zip(keys, keys[1:]):
        if t0 <= t < t1:
            return (s1 - s0) / (t1 - t0)
    return 0.0


START, END = 0.3, 2.7                       # the source move runs 0.3 s -> 2.7 s on both lanes
KEYS = ((START, START), (0.9, 0.9), (2.0, 1.35), (END, END))   # 1x, then 0.4x, then ~1.9x
X0, X1 = 220, demo.W - 160
LANES = ((demo.H * 0.32, 'original', demo.MUTED), (demo.H * 0.72, 'retimed', demo.ACCENT))


def source(s):
    """The authored move at source time `s`: a dot hopping left to right."""
    p = vb.clamp01((s - START) / (END - START))
    return X0 + (X1 - X0) * p, -abs(math.sin(p * math.pi * 3)) * 70


def lane(cv, y, label, color, clock, n):
    demo.floor(cv, y + 36, demo.LINE)
    f = demo.mono(26)
    vb.text.draw(cv, [label], f, 80, y - 150, demo.MUTED)
    for k in range(n % 4, n + 1, 4):          # ghosts every 4 frames: their spacing shows the pace
        x, dy = source(clock(k / demo.FPS))
        demo.dot(cv, x, y + dy, 10, color, alpha=0.35)
    x, dy = source(clock(n / demo.FPS))
    demo.dot(cv, x, y + dy, 30, color)
    cv.mark(label, x - 30, y + dy - 30, 60, 60)


def draw(n, cv):
    t = n / demo.FPS
    lane(cv, *LANES[0], lambda u: u, n)
    lane(cv, *LANES[1], lambda u: retime(u, KEYS), n)
    rate = speed(t, KEYS)
    tag = f'{rate:.1f}×' if START <= t < END else ''
    if tag:
        f = demo.mono(40, 700)
        w, _ = vb.text.block_size([tag], f)
        vb.text.draw(cv, [tag], f, demo.W - 80 - w, LANES[1][0] - 160, demo.ACCENT)


TECHNIQUE = Technique(
    id='retiming',
    name='Retiming',
    family='principles',
    group='Time remapping',
    aliases=('time remapping', 'time remap', 'speed ramp', 'time warp'),
    definition='An existing move keeps its exact path but is played back on a new clock, '
               'so parts of it run slower, faster or pause while it still ends where it did.',
    phrasings=('slow that bit down, then let it whip through the rest',
               'keep the same animation but change its pacing',
               'make it go into slow motion halfway and then speed back up'),
    related=('velocity-preserving-retarget', 'interruptible-motion', 'hyperlapse', 'cut-on-action',
             'distance-based-duration', 'reverse-motion-cut'),
    api=('videobuilder.techniques.principles.retiming.retime',
         'videobuilder.techniques.principles.retiming.speed'),
    demo=lambda: demo.film(draw),
)
