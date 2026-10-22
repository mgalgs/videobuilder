"""Smash cut: a quiet shot is cut off mid-moment by a loud, contrasting one,
with no blend between them; the incoming shot lands a touch too close and
snaps back, so the cut hits like a jolt."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def smash_cut(cv, a, b, p, at=0.15, punch=0.08, settle=0.5):
    """Draw the cut at progress `p` (0 -> 1): `a(cv)` untouched until `at`,
    then `b(cv)` at once, starting `punch` larger and offset a little,
    springing back to rest over the next `settle` of the transition.
    `punch=0` leaves a plain hard cut.

    In a film, call it across a short overlap, e.g.
    `smash_cut(cv, lambda c: quiet(c, old), lambda c: loud(c, new), new.f / overlap_frames)`."""
    if p < at:
        a(cv)
        return
    k = vb.clamp01((p - at) / settle) if settle > 0 else 1.0
    jolt = (1 - k) ** 3
    z = 1 + punch * jolt
    cx, cy = cv.width / 2, cv.height / 2
    dx = cv.width * 0.012 * jolt * math.cos(k * 9)
    with cv.layer(dx=cx * (1 - z) + dx, dy=cy * (1 - z), scale=z):
        b(cv)


def _quiet(cv, t):
    cv.fill(demo.BG)
    r = 26 + 6 * math.sin(t * 2.2)
    demo.dot(cv, demo.W / 2 + 40 * math.sin(t * 0.7), demo.H / 2 + 30, r=r, color=demo.MUTED, alpha=0.7)
    demo.word(cv, 'shh...', demo.W / 2, demo.H / 2 - 120, size=44, color=demo.MUTED, weight=500)


def _loud(cv):
    cv.fill('#f2b705')
    step = 70
    for i in range(-demo.H // step, demo.W // step + 2):
        x = i * step
        cv.line(x, 0, x + demo.H, demo.H, '#e0a800', width=22)
    demo.word(cv, 'BANG!', demo.W / 2, demo.H / 2, size=210, color=demo.BG, weight=900)


def _draw(n, cv):
    t = n / demo.FPS
    p = demo.phase(n, 1.4, 2.2)    # cuts at 1.5 s
    smash_cut(cv, lambda c: _quiet(c, t), _loud, p, at=0.125)


CAPABILITY = Capability(
    id='smash-cut',
    name='Smash cut',
    family='transitions',
    group='Cuts',
    aliases=('contrast cut', 'sudden cut', 'hard cut'),
    definition='A calm shot is cut off without warning by a loud, starkly different one, '
               'with nothing in between to soften the change.',
    phrasings=('jump straight from the quiet bit to something loud',
               'abruptly cut to a totally different shot for shock value',
               'no fade, just slam into the next scene'),
    related=('zoom-blur', 'strobe-cut', 'punch-in', 'impact-hit', 'impact-shake', 'silence-drop'),
    api=('videobuilder.capabilities.transitions.smash_cut.smash_cut',),
    demo=lambda: demo.film(_draw),
)
