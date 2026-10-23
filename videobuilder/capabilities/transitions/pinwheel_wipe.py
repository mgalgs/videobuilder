"""Pinwheel wipe: the frame is cut into equal pie slices about its centre,
and in every slice at once a radial edge sweeps round like a clock hand,
uncovering the incoming scene blade by blade until the slices close up."""
import math

from .. import _demo as demo
from ..schema import Capability


def pinwheel_wipe(cv, a, b, p, blades=6, cx=None, cy=None, start=-math.pi / 2, clockwise=True,
                  edge=None, edge_width=4):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` underneath, and `b(cv)`
    showing through `blades` wedges about (`cx`, `cy`) (default the frame
    centre), each opening from its own spoke -- the first at angle `start`,
    radians, 0 along +x -- and sweeping `2 pi / blades` round by `p` = 1.
    `clockwise=False` turns them the other way. `edge`, a colour, strokes
    each blade's moving edge so the sweep reads on busy pictures; it fades
    out over the last eighth of the wipe so it never sits on the finished
    frame and pops off.

    In a film, call it while two shots are live in an overlap, e.g.
    `pinwheel_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    p = min(1.0, max(0.0, p))
    w, h = cv.width, cv.height
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    a(cv)
    if p <= 0:
        return
    if p >= 1:
        b(cv)
        return
    # far enough out to reach every corner from any centre inside the frame
    r = 2 * math.hypot(w, h)
    step = 2 * math.pi / blades
    sweep = step * p * (1 if clockwise else -1)
    spokes = [start + k * step for k in range(blades)]
    c = cv.ctx
    c.save()
    c.new_path()
    for s in spokes:
        c.move_to(cx, cy)
        if clockwise:
            c.arc(cx, cy, r, s, s + sweep)
        else:
            c.arc_negative(cx, cy, r, s, s + sweep)
        c.close_path()
    c.clip()
    b(cv)
    c.restore()
    fade = min(1.0, (1 - p) * 8)
    if edge is not None and fade > 0:
        for s in spokes:
            t = s + sweep
            cv.line(cx, cy, cx + r * math.cos(t), cy + r * math.sin(t), edge,
                    width=edge_width, alpha=fade)


CAPABILITY = Capability(
    id='pinwheel-wipe',
    name='Pinwheel wipe',
    family='transitions',
    group='Wipes',
    aliases=('pinwheel transition', 'windmill wipe', 'multi-blade clock wipe', 'radial blade wipe'),
    definition='Several blades fanned out from the centre of the frame all rotate together, '
               'each one sweeping the next picture into view until the whole screen has turned over.',
    phrasings=('spin the new scene in like a pinwheel',
               'a clock wipe but with lots of hands going round at once',
               'reveal the next shot with rotating pie slices from the middle'),
    related=('paint-brush-wipe', 'coin-flip', 'spin', 'ribbon-sweep', 'flip', 'fill-sweep-button'),
    api=('videobuilder.capabilities.transitions.pinwheel_wipe.pinwheel_wipe',),
    # a gentle smoothstep over 1.0-2.8 s puts the 70% poster frame (2.1 s) at
    # about two-thirds through the sweep, with A and B in alternating blades
    demo=lambda: demo.two_scenes(lambda cv, a, b, p: pinwheel_wipe(
        cv, a, b, p * p * (3 - 2 * p), edge=demo.ACCENT), start=1.0, length=1.8),
)
