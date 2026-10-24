"""Match Cut: a straight cut between two scenes that share a subject in the
same place, at the same size, so the eye carries over the edit -- a setting
sun becomes a clock face, a ball becomes a planet."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def match_offset(match_a, match_b):
    """The `(dx, dy, scale)` that lays scene B over the frame so its subject,
    `match_b = (cx, cy, size)`, lands on scene A's `match_a = (cx, cy, size)`.
    Pass it to `cv.layer(dx=..., dy=..., scale=...)` around `b(cv)`."""
    ax, ay, asize = match_a
    bx, by, bsize = match_b
    s = asize / bsize
    return ax - bx * s, ay - by * s, s


def match_cut(cv, a, b, p, at=0.5, match_a=None, match_b=None):
    """Draw the cut at progress `p` (0 -> 1): `a(cv)` before `at`, `b(cv)`
    from `at` on, with no blend between them.

    The match is the film's job -- the two subjects should share a shape, a
    spot in frame, or a direction of travel. When they don't sit in quite
    the same place, give each subject as `(cx, cy, size)`: B is then moved
    and scaled so its subject lands exactly on A's (see `match_offset`). B
    should fill its own background, since the scaled layer may not cover
    the frame otherwise."""
    if p < at:
        a(cv)
    elif match_a is None or match_b is None:
        b(cv)
    else:
        dx, dy, s = match_offset(match_a, match_b)
        with cv.layer(dx=dx, dy=dy, scale=s):
            b(cv)


# ---- demo: a setting sun cuts to a clock face, same spot, same size, same drift ----

R = 120
CUT = 1.5


def _sun_at(n):
    """Where the shared circle is at frame `n`: one slow drift down and right
    that runs straight through the cut."""
    t = demo.phase(n, 0.0, demo.SECONDS)
    return demo.W * (0.34 + 0.32 * t), demo.H * (0.40 + 0.10 * t)


def _label(cv, text, ink):
    vb.text.draw(cv, [text], demo.font(28, 800), 40, 32, ink)


def _sunset(cx, cy):
    def draw(cv):
        cv.fill(demo.BG)
        horizon = demo.H * 0.66
        for i in range(5):
            demo.dot(cv, cx, cy, R + 40 + 34 * i, color=demo.ACCENT, alpha=0.07)
        demo.dot(cv, cx, cy, R, color=demo.ACCENT)
        cv.rect(0, horizon, demo.W, demo.H - horizon, '#0b0d12')
        cv.line(0, horizon, demo.W, horizon, demo.MUTED, width=3)
    return draw


def _clock(n):
    """Scene B drawn in its own layout: a clock face at the frame's centre."""
    cx, cy = demo.W / 2, demo.H / 2

    def draw(cv):
        cv.fill('#e9e6df')
        cv.rect(-demo.W, cy + R * 1.6, 3 * demo.W, demo.H, '#d9d4c9')  # wide: B is shifted to match
        demo.dot(cv, cx, cy, R, color=demo.TEAL)
        for k in range(12):
            a = k * math.pi / 6
            r0 = R * (0.78 if k % 3 else 0.68)
            cv.line(cx + r0 * math.cos(a), cy + r0 * math.sin(a),
                    cx + R * 0.88 * math.cos(a), cy + R * 0.88 * math.sin(a), demo.BG, width=5)
        minute = -math.pi / 2 + n / demo.FPS * 1.2
        cv.line(cx, cy, cx + R * 0.72 * math.cos(minute), cy + R * 0.72 * math.sin(minute), demo.BG, width=7)
        cv.line(cx, cy, cx + R * 0.45 * math.cos(minute / 12), cy + R * 0.45 * math.sin(minute / 12),
                demo.BG, width=10)
        demo.dot(cv, cx, cy, 10, color=demo.BG)
    return draw, (cx, cy, R)


def draw(n, cv):
    sx, sy = _sun_at(n)
    clock, anchor = _clock(n)
    match_cut(cv, _sunset(sx, sy), clock, n / demo.FPS / demo.SECONDS, at=CUT / demo.SECONDS,
              match_a=(sx, sy, R), match_b=anchor)
    _label(cv, *(('Scene A', demo.INK) if n / demo.FPS < CUT else ('Scene B', demo.BG)))


CAPABILITY = Capability(
    id='match-cut',
    name='Match cut',
    family='transitions',
    group='Cuts',
    aliases=('matched cut', 'graphic match', 'match on action', 'shape match'),
    definition='A hard cut where something in the new shot sits in the same spot, with the same shape or '
               'movement, as something in the old one, so the change feels seamless.',
    phrasings=('cut from the sun straight to a clock in the same place',
               'line the two shots up so the circle carries across the cut',
               'jump to the next scene but keep the shape where it was'),
    related=('rack-focus', 'cross-zoom', 'zoom-blur', 'strobe-cut', 'tilt-shift-miniature', 'tracking-shot'),
    api=('videobuilder.capabilities.transitions.match_cut.match_cut',
         'videobuilder.capabilities.transitions.match_cut.match_offset'),
    demo=lambda: demo.film(draw),
)
