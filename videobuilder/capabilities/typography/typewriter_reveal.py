"""Typewriter Reveal: the same idea as Typewriter (`type_typewriter.py`),
which keeps the capability -- its api already names `vb.type.draw`: a line
appears one character at a time, left to right, with a caret riding just
after the last letter in. This module's own code stays (a film may still
import it), but it is no longer a capability of its own.

`vb.type`'s 'typewriter' style is the full-frame film of this (paper, struck
letters, a sheet feeding out); `draw_typed` is the bare move for any line of
any font, placed anywhere. With a `seed` it keys at the typewriter style's
uneven human cadence (`type.typewriter.schedule`) instead of a steady one.
"""
import videobuilder as vb

from .. import _demo as demo
from ...type.typewriter import schedule

MERGED_INTO = 'type-typewriter'


def typed(text, p, seed=None):
    """How many characters of `text` are in at progress `p` (0 -> 1): one key
    per step, evenly, the last landing at 1. With `seed`, the keys fall at
    `schedule`'s uneven cadence instead (a longer reach after a space or a
    comma), stretched to the same 0 -> 1."""
    p = vb.clamp01(p)
    if not text:
        return 0
    if seed is None:
        return min(len(text), int(p * len(text) + 1e-9))
    times, span = schedule(text, seed, 1.0)
    keys = list(times[1:]) + [span]   # each key lands at the end of its reach; the last at the span
    return sum(1 for k in keys if k <= p * span + 1e-9)


def draw_typed(cv, text, font, x, y, p, color, caret=None, caret_on=True, seed=None):
    """Draw `text` typed in to progress `p` from its top-left (x, y). `caret`:
    a colour for a thin bar just after the last letter in (None for no
    caret); `caret_on` lets the caller blink it. `seed`: see `typed`.
    Letters sit where they will in the finished line, so nothing shifts as
    the line grows. Returns the Box of the finished line."""
    n = typed(text, p, seed)
    if n:
        vb.text.draw(cv, [text[:n]], font, x, y, color)
    lh = vb.text.line_height(font)
    if caret is not None and caret_on:
        cx = x + (vb.text.measure(text[:n], font) if n else 0.0)
        cv.rect(cx + font.size * 0.06, y + lh * 0.1, max(2.0, font.size * 0.06), lh * 0.8, caret)
    return vb.Box(x, y, vb.text.measure(text, font), lh)


def draw(n, cv):
    f = demo.mono(84, 600)
    text = 'Hello, world.'
    w, h = vb.text.block_size([text], f)
    t = n / demo.FPS
    p = demo.phase(n, 0.4, 2.2)
    blink = p < 1 or (t - 2.2) % 0.5 < 0.25
    box = draw_typed(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, p, demo.INK, caret=demo.ACCENT,
                     caret_on=blink)
    cv.mark('text', *box)
