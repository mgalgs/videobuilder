"""Sub drop: videobuilder's sound pack already has these as the
`pro_sub_drop/*` sounds, so this entry only names `vb.sfx.sound` and demos
it. Put the drop's onset on the hit and give it room to fall away:

    BOOM = vb.sfx.sound('pro_sub_drop/low', at=IMPACT, align='onset', dur=2, gain_db=-4)
    vb.Film(..., sounds=(BOOM,))

`note=` tunes it to the music's key (E1-B1); `pro_sub_drop/quick` is the
short one, `pro_sub_drop/bright` the one that blooms a moment after the cut.

The demo slams a card onto the floor; under it a wide, slow wave rolls out
from the impact, its waves stretching longer and lower as it fades, the
picture of the tone dropping in pitch while the sub drop plays.
"""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

SOUND = 'pro_sub_drop/low'
FALLBACK = 'pro_impact/short'
HIT = round(0.9 * demo.FPS)                 # the frame the card lands on, and the drop starts
FALL = 1.8                                  # seconds the drop takes to fall away
CARD_W, CARD_H = 200, 120
FLOOR = demo.H * 0.44                       # where the card's bottom lands
WAVE_Y = demo.H * 0.72
X0, X1 = 60, demo.W - 60


def _wave(cv, t):
    """The tone `t` seconds after the hit: a sine across the frame whose
    wavelength grows (pitch falling) and whose height shrinks (fading)."""
    if t < 0 or t > FALL:
        cv.line(X0, WAVE_Y, X1, WAVE_Y, demo.LINE, width=3)
        return
    u = t / FALL
    amp = 70 * math.exp(-3.2 * u) * min(1.0, t * 12)
    wavelength = 50 + 520 * u ** 1.4
    phase = 2 * math.pi * (t * 3.5)
    cx = demo.W / 2
    prev = None
    for i in range(0, 241):
        x = X0 + (X1 - X0) * i / 240
        d = abs(x - cx)
        y = WAVE_Y + amp * math.exp(-(d / 400) ** 2) * math.sin(2 * math.pi * d / wavelength - phase)
        if prev:
            cv.line(prev[0], prev[1], x, y, demo.ACCENT, width=6, alpha=0.35 + 0.65 * (1 - u))
        prev = (x, y)
    cv.mark('wave', X0, WAVE_Y - 80, X1 - X0, 160)


def draw(n, cv):
    t = (n - HIT) / demo.FPS
    thump = math.exp(-6 * t) * math.cos(14 * t) if t >= 0 else 0.0
    with cv.layer(dy=10 * thump, scale=1 + 0.02 * max(0.0, thump)):   # the frame takes the weight
        demo.floor(cv, FLOOR)
        fall = demo.phase(n, 0.35, HIT / demo.FPS) ** 2   # falling under gravity
        y = -CARD_H + (FLOOR - CARD_H / 2 + CARD_H) * fall
        squash = 0.18 * max(0.0, thump)
        demo.card(cv, demo.W / 2, y + CARD_H / 2 * squash, w=CARD_W * (1 + squash), h=CARD_H * (1 - squash))
        _wave(cv, t)
    if 0 <= t <= FALL:
        demo.word(cv, 'SUB', demo.W / 2, demo.H * 0.92, size=26, color=demo.MUTED, weight=800,
                  alpha=1 - t / FALL)


def _sound():
    """The sub drop on the hit. A pack without one (the tests' small
    fixture pack) gets its hit instead, so the demo still carries sound."""
    try:
        return vb.sfx.sound(SOUND, at=HIT, fps=demo.FPS, align='onset', dur=FALL, gain_db=-4)
    except ValueError:
        return vb.sfx.sound(FALLBACK, at=HIT, fps=demo.FPS, align='onset', gain_db=-8)


def film():
    return demo.film(draw, sounds=(_sound(),))


TECHNIQUE = Technique(
    id='sub-drop',
    name='Sub drop',
    family='sound',
    group='Sound effects',
    aliases=('sub-bass drop', 'sub boom', 'bass drop'),
    definition='A deep bass boom that slides down in pitch and dies away under a big moment, '
               'giving it a weight you feel in your chest.',
    phrasings=('add a low boom under the logo slam',
               'give the impact some deep bass that falls away',
               'put a heavy rumble drop on the hit'),
    related=('silence-drop', 'gravity-drop', 'drop-shadow-lift', 'signal-dropout', 'character-drop',
             'physics-letter-drop'),
    api=('videobuilder.sfx.sound',),
    demo=film,
)
