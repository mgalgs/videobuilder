"""Clock wipe: a hand pivots on the frame's centre and sweeps once around,
uncovering the incoming scene in the pie slice behind it."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

SWEEP = vb.ease.bezier(0.45, 0, 0.55, 1)  # gentle in and out: the hand starts, travels, settles


def clock_wipe(cv, a, b, p, cx=None, cy=None, start=-math.pi / 2, clockwise=True,
               edge='#f4efe4', edge_width=6, ease=SWEEP):
    """Draw the clock wipe at progress `p` (0 -> 1): `a(cv)` everywhere, then
    `b(cv)` clipped to the pie slice swept so far from angle `start` (radians,
    the canvas convention; the default is twelve o'clock) about (`cx`, `cy`),
    default the frame's centre. `edge` draws the sweeping hand as a line of
    `edge_width` (None for a bare cut edge); `ease` shapes the sweep.

    In a film, call it while two shots are live in an overlap, e.g.
    `clock_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    cx = cv.width / 2 if cx is None else cx
    cy = cv.height / 2 if cy is None else cy
    r = math.hypot(max(cx, cv.width - cx), max(cy, cv.height - cy)) + 2  # reaches every corner
    sweep = 2 * math.pi * vb.clamp01(ease(vb.clamp01(p)))
    a(cv)
    if sweep <= 0:
        return
    hand = start + sweep if clockwise else start - sweep
    c = cv.ctx
    c.save()
    c.new_path()
    c.move_to(cx, cy)
    if clockwise:
        c.arc(cx, cy, r, start, hand)
    else:
        c.arc_negative(cx, cy, r, start, hand)
    c.close_path()
    c.clip()
    try:
        b(cv)
    finally:
        c.restore()
    if edge and sweep < 2 * math.pi:
        cv.line(cx, cy, cx + r * math.cos(hand), cy + r * math.sin(hand), edge, width=edge_width)


TECHNIQUE = Technique(
    id='clock-wipe',
    name='Clock wipe',
    family='transitions',
    group='Wipes',
    aliases=('radial wipe', 'sweep wipe', 'clock sweep'),
    definition='A straight edge pinned at the centre of the frame turns one full circle like a clock hand, '
               'and the next scene shows up in the wedge it leaves behind.',
    phrasings=('wipe to the next shot by sweeping round like the hand of a clock',
               'a radial reveal that spins around the middle of the screen',
               'turn a line around the centre to uncover the new scene'),
    related=('wipe-reveal', 'spin', 'area-fill-sweep', 'fill-sweep-button', 'circular-clip-reveal', 'coin-flip'),
    api=('videobuilder.techniques.transitions.clock_wipe.clock_wipe',),
    demo=lambda: demo.two_scenes(clock_wipe),
)
