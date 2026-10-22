"""Whoosh: videobuilder already has it as `vb.sfx.sound` with a whoosh from the
bundled pack, its peak put on the fastest frame of the move, so this entry
only names it and demos it: a card whips across and back, a whoosh on each
pass, with streaks behind it and the sound's lane drawn underneath."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

PASSES = ((0.55, 1.15, -1, 1), (1.75, 2.35, 1, -1))   # (start s, end s, from side, to side)
REACH = 300                                           # how far either side of centre the card rests
LANE_Y = demo.H - 105


def card_x(t):
    """The card's centre at `t` seconds: resting left, whipping right, whipping back."""
    x = -REACH
    for start, end, a, b in PASSES:
        if t >= start:
            p = vb.ease_in_out_quart(vb.clamp01((t - start) / (end - start)))
            x = REACH * (a + (b - a) * p)
    return demo.W / 2 + x


def peak_frame(start, end):
    """The middle of a pass: where an ease-in-out is fastest, so where the whoosh peaks."""
    return round((start + end) / 2 * demo.FPS)


def draw(n, cv):
    t = n / demo.FPS
    cx, cy = card_x(t), demo.H / 2 - 95
    speed = card_x(t) - card_x(t - 1 / demo.FPS)          # px per frame, signed
    if abs(speed) > 4:                                    # speed streaks trailing the card
        for i, dy in enumerate((-48, -16, 16, 48)):
            length = min(abs(speed) * (3.2 - 0.5 * i), 420)
            x0 = cx - math.copysign(130, speed)
            cv.line(x0, cy + dy, x0 - math.copysign(length, speed), cy + dy, demo.INK, width=4,
                    alpha=min(0.55, abs(speed) / 120))
    demo.card(cv, cx, cy)

    # the sound's lane: each whoosh's swell centred on its peak frame, a playhead crossing it
    x0, x1 = 80, demo.W - 80
    cv.line(x0, LANE_Y, x1, LANE_Y, demo.LINE, width=2)
    fx = lambda f: x0 + (x1 - x0) * f / (demo.SECONDS * demo.FPS)   # noqa: E731
    for start, end, _, _ in PASSES:
        pk = peak_frame(start, end)
        heard = vb.clamp01(1 - abs(n - pk) / 6)           # lights up as the whoosh passes
        for f in range(pk - 12, pk + 13):
            amp = 42 * math.exp(-((f - pk) / 4.5) ** 2) * (0.6 + 0.4 * abs(math.sin(f * 1.7)))
            cv.line(fx(f), LANE_Y - amp, fx(f), LANE_Y + amp, demo.ACCENT if heard else demo.MUTED,
                    width=6, alpha=0.5 + 0.5 * heard)
    cv.line(fx(n), LANE_Y - 55, fx(n), LANE_Y + 55, demo.INK, width=2, alpha=0.8)
    demo.word(cv, 'whoosh', demo.W / 2, LANE_Y - 75, size=26, color=demo.MUTED, weight=700)


def film():
    sounds = tuple(vb.sfx.sound('whoosh_fast/tight', at=peak_frame(s, e), dur=0.5, gain_db=-6)
                   for s, e, _, _ in PASSES)
    return demo.film(draw, sounds=sounds)


CAPABILITY = Capability(
    id='whoosh',
    name='Whoosh',
    family='sound',
    group='Sound effects',
    aliases=('swoosh', 'swish', 'whoosh SFX', 'pass-by'),
    definition='A short rush of air on the soundtrack, loudest at the instant something on screen moves '
               'fastest, so a quick move feels like it cut through the air.',
    phrasings=('add a whoosh when the card flies in',
               'make the fast slide sound like it swooshes past',
               'put a swish sound on the whip pan'),
    related=('speed-lines', 'sound-bridge', 'tape-wobble', 'silence-drop', 'scroll-velocity-skew', 'sonic-logo'),
    api=('videobuilder.sfx.sound', 'videobuilder.sfx.find'),
    demo=film,
)
