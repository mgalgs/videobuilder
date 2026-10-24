"""Accumulation Motion Blur: the same idea as Motion blur (`motion_blur.py`),
which keeps the capability -- both smear whatever moves along the path it
travelled during the exposure, this one by averaging many renders of the
scene at instants spread across the shutter interval, so curves and spins
blur along their true path. This module's own code stays (a film may still
import it), but it is no longer a capability of its own."""
import math

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'motion-blur'


def accumulation_blur(cv, draw, t, frame=1 / demo.FPS, shutter=0.5, samples=16, background=None):
    """Draw `draw(cv, time)` averaged over `samples` instants from
    `t - shutter * frame` to `t`.

    `draw` renders the scene at any time in seconds; it is called once per
    sample. `frame` is one frame's length in seconds and `shutter` the share
    of it the shutter stays open (0.5 is film's 180-degree shutter, 1 a full
    frame, more exaggerates the streaks). `background`, when given, fills each
    sample first; the average is exact only where every sample is opaque, so
    give one unless `draw` paints the whole frame itself. Wrap the call in
    `cv.clip(...)` to blur one region only.

    Each sample is composited over the running result at opacity 1/k, which
    keeps the result the mean of the k samples so far and leaves still
    pixels exactly as one render would."""
    samples = max(1, int(samples))
    span = shutter * frame
    c = cv.ctx
    c.save()
    c.push_group()
    for k in range(1, samples + 1):
        at = t - span * (1 - (k - 1) / (samples - 1)) if samples > 1 else t
        c.push_group()
        if background is not None:
            cv.fill(background)
        draw(cv, at)
        c.pop_group_to_source()
        c.paint_with_alpha(1 / k)
    c.pop_group_to_source()
    c.paint()
    c.restore()


LEFT, RIGHT = demo.W * 0.18, demo.W * 0.82
TOP, BOTTOM = demo.H * 0.3, demo.H * 0.78  # the two lanes' resting heights
LIFT = demo.H * 0.07
SHUTTER = 1.0  # a full frame open: the streaks read clearly at gallery size


def _pose(s):
    """The card's x, lift and turn at `s` seconds: it swings across and back
    in a shallow arc, spinning a full turn each way."""
    go = vb.ease_in_out_quart(vb.clamp01((s - 0.45) / 0.75))
    back = vb.ease_in_out_quart(vb.clamp01((s - 1.85) / 0.75))
    p = go - back
    return LEFT + (RIGHT - LEFT) * p, -LIFT * math.sin(math.pi * p), 2 * math.pi * p


def _card(cv, s, y):
    x, lift, turn = _pose(s)
    c = cv.ctx
    c.save()
    c.translate(x, y + lift)
    c.rotate(turn)
    demo.card(cv, 0, 0, w=110, h=70)
    c.restore()


def _label(cv, text, y):
    vb.text.draw(cv, [text], demo.font(18, 700), 32, y, demo.MUTED)


def draw(n, cv):
    s = n / demo.FPS
    cv.line(0, demo.H / 2, demo.W, demo.H / 2, demo.LINE, width=2)
    _label(cv, 'one render per frame', 24)
    _card(cv, s, TOP)
    with cv.clip(0, demo.H / 2 + 1, demo.W, demo.H / 2):
        accumulation_blur(cv, lambda c, at: _card(c, at, BOTTOM), s, shutter=SHUTTER, samples=24,
                          background=demo.BG)
    _label(cv, '24 renders averaged across the shutter', demo.H / 2 + 24)
