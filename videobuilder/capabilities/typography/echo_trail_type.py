"""Echo Trail Type: the same idea as Frame delay echo
(`../vfx/frame_delay_echo.py`), which keeps the capability -- both call
`echo_trail` to stack fading copies of a moving subject at a few fixed lags
behind the live one, this one tracing a moving word rather than a whole
frame. This module's own code stays (a film may still import it), but it is
no longer a capability of its own."""
import math

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'frame-delay-echo'


def echo_trail(cv, draw_copy, t, copies=6, lag=0.05, falloff=0.62):
    """Draw `copies` echoes and then the live copy, oldest first so newer ones
    sit on top. `draw_copy(cv, t, k, alpha)` draws the subject as it was at
    time `t`; echo `k` (1 = nearest) is `k * lag` seconds behind, at `alpha`
    `falloff ** k`, and `k` is 0 for the live copy. When the subject stops,
    its past positions meet its present one and the trail closes up on its own."""
    for k in range(copies, 0, -1):
        draw_copy(cv, t - k * lag, k, falloff ** k)
    draw_copy(cv, t, 0, 1.0)


def draw_echo_trail(cv, text, font, at, t, color, echo=None, **kw):
    """`text` centred on `at(t) -> (cx, cy)` with its echo trail; `t` is in
    seconds. Echoes use `echo` (default `color`). `kw` goes to `echo_trail`.
    Returns the Box of the live copy."""
    w, h = vb.text.block_size([text], font)
    out = []

    def copy(cv, tk, k, alpha):
        cx, cy = at(tk)
        box = vb.text.draw(cv, [text], font, cx - w / 2, cy - h / 2, color if k == 0 else (echo or color),
                           alpha=alpha)
        if k == 0:
            out.append(box)

    echo_trail(cv, copy, t, **kw)
    return out[0]


def _path(t):
    # A swoop in from the left on a dying wave, coming to rest at centre by 2.9 s.
    # Smoothstep, not a steep ease, so the word is still travelling briskly at
    # 2.1 s and its echoes are spread out along the path rather than stacked.
    u = vb.clamp01((t - 0.5) / 2.4)
    p = u * u * (3 - 2 * u)
    x = demo.W * (0.22 + 0.28 * p)
    y = demo.H / 2 - 260 * math.sin(p * 2 * math.pi) * (1 - p)
    return x, y


def draw(n, cv):
    box = draw_echo_trail(cv, 'ECHO', demo.font(150, 900), _path, n / demo.FPS, demo.INK, echo=demo.ACCENT,
                          copies=6, lag=0.1)
    cv.mark('text', *box)
