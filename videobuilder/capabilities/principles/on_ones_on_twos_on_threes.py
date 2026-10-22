"""On Ones, On Twos, On Threes: the same move drawn a new pose every frame, every
second frame or every third, so it reads silky, snappy-handmade or deliberately
choppy at one playback rate."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def on_steps(n, step, start=0):
    """Frame `n` held on `step`s: the frame a pose drawn every `step` frames
    (counted from `start`) shows at `n`. `step=1` is on ones (unchanged), 2 on
    twos, 3 on threes. Draw the moving thing at the returned frame instead of
    `n` and it holds each pose for `step` frames; the rest of the film can
    stay on ones."""
    step = max(1, int(step))
    return n if n < start else n - (n - start) % step


LANES = ((1, 'ONES', demo.ACCENT), (2, 'TWOS', demo.TEAL), (3, 'THREES', demo.INK))


def draw(n, cv):
    x0, x1, r = 210, demo.W - 70, 24
    label = demo.font(22, 800)
    for i, (step, name, color) in enumerate(LANES):
        y = demo.H / 2 + (i - 1) * 150
        vb.text.draw(cv, [f'ON {name}'], label, 50, y - 14, demo.MUTED)
        cv.line(x0, y + r + 10, x1, y + r + 10, demo.LINE, width=2)
        at = lambda f: x0 + r + (x1 - x0 - 2 * r) * vb.ease_in_out_quart(demo.phase(f, 0.3, 2.4))  # noqa: E731
        held = on_steps(n, step)
        for k in (3, 2, 1):  # the last few poses, faint: wider gaps the longer each is held
            demo.dot(cv, at(held - k * step), y, r, color=color, alpha=0.1 * (4 - k))
        x = at(held)
        demo.dot(cv, x, y, r, color=color)
        cv.mark(f'dot-{step}', x - r, y - r, 2 * r, 2 * r)


TECHNIQUE = Technique(
    id='on-ones-on-twos-on-threes',
    name='On Ones, On Twos, On Threes',
    family='principles',
    group='Principle sub-techniques',
    aliases=('on ones', 'on twos', 'on threes', 'animating on twos', 'shooting on twos', 'frame holds'),
    definition='The moving thing gets a new pose every frame, every other frame or every third frame, '
               'so the same motion looks fluid, hand-made or deliberately steppy.',
    phrasings=('make it move on twos like hand-drawn animation',
               'hold each pose for a couple of frames so it feels choppier',
               'animate at a lower frame rate than the rest of the video'),
    related=('frame-by-frame-hand-drawn-animation', 'frame-interpolation', 'pulldown-judder',
             'interruptible-motion', 'view-transition', 'stop-motion-animation'),
    api=('videobuilder.techniques.principles.on_ones_on_twos_on_threes.on_steps',),
    demo=lambda: demo.film(draw),
)
