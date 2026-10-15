"""Helpers the `data_*` components share: number formatting that stays short
for any value a slot allows, fitting a line of type to a width, series
normalising, and the beat the compendium previews at.

A leading underscore keeps this module out of the catalog.
"""
import math

import videobuilder as vb
from videobuilder import text

from .. import kit

FPB = round(kit.GRID.frames_per_beat)  # 15 frames a beat at 120 bpm
MINUS = '−'


def series_pairs(raw):
    """Series items as (label, value) pairs; a plain number is labelled by its
    1-based position."""
    return [tuple(item) if isinstance(item, (list, tuple)) else (str(i + 1), item) for i, item in enumerate(raw)]


def num(v, decimals=None, signed=False):
    """`v` as short, legible text: thousands as k, millions as M, billions as
    B, a typographic minus, and at most one decimal unless `decimals` says
    otherwise. Any finite value comes back no longer than ~7 characters."""
    if v is None or not math.isfinite(v):
        return '0'
    sign = MINUS if v < 0 else ('+' if signed and v > 0 else '')
    a = abs(v)
    if a >= 1e4:
        for size, suffix in ((1e3, 'k'), (1e6, 'M'), (1e9, 'B'), (1e12, 'T')):
            q = a / size
            body = f'{q:.0f}' if q >= 99.95 else f'{q:.1f}'.rstrip('0').rstrip('.')
            if float(body) < 1000:
                return f'{sign}{body}{suffix}'
        return f'>{sign}999T'
    if decimals is None:
        decimals = 0 if float(a).is_integer() or a >= 100 else (1 if a >= 1 else 2)
    out = f'{a:,.{decimals}f}'
    return sign + out


def decimals_of(*values):
    """How many decimals the counted-up text of `values` should keep, so a
    count-up shows 0.0 -> 2.4 rather than flickering between widths."""
    best = 0
    for v in values:
        a = abs(v)
        if a >= 1e4 or float(a).is_integer():
            continue
        best = max(best, 1 if a >= 1 else 2)
    return best


def fit(copy, make, max_w, hi, lo):
    """`make(size)` for the largest size from `hi` down to `lo` at which
    `copy` measures no wider than `max_w`."""
    size = hi
    while size > lo and text.measure(copy, make(size)) > max_w:
        size -= 2
    return make(size)


def prog(f, a, z, ease=vb.ease_out_expo):
    return ease(vb.clamp01((f - a) / max(1e-9, z - a)))


def spring(f, delay, spec):
    return vb.spring_at(f - delay, 30, **spec)


def scaled(cv, cx, cy, s):
    """A layer scaled by `s` about (cx, cy)."""
    s = max(s, 1e-3)
    return cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s)


def pop(f, at, amount=0.12, spec=vb.damped(0.45, hz=5.0)):
    """1, plus a quick scale accent landing on frame `at` that decays back to 1
    within the beat (the `pop-on-the-beat` move)."""
    if f < at:
        return 1.0
    return 1 + amount * (1 - vb.spring_at(f - at, 30, **spec))


def glow(cv, cx, cy, r, color, alpha):
    import cairo
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    cr, cg, cb, _ = vb.rgba(color)
    g.add_color_stop_rgba(0, cr, cg, cb, alpha)
    g.add_color_stop_rgba(1, cr, cg, cb, 0)
    cv.ctx.rectangle(cx - r, cy - r, 2 * r, 2 * r)
    cv.ctx.set_source(g)
    cv.ctx.fill()


def kind_of(cv):
    """'wide', 'tall' or 'square' for the canvas being drawn."""
    if cv.width > cv.height * 1.2:
        return 'wide'
    if cv.height > cv.width * 1.2:
        return 'tall'
    return 'square'


def safe(cv):
    """The safe area: `kit.safe`, with a taller bottom margin in 9:16 where a
    phone app lays its caption and buttons."""
    s = kit.safe(cv)
    if kind_of(cv) == 'tall':
        return vb.Box(s.x, s.y + 16, s.w, s.h - 16 - 56)
    return s


def _hard_break(lines, f, max_w):
    """`lines` with any line still wider than `max_w` (one long word) split
    character by character."""
    out = []
    for line in lines:
        while text.measure(line, f) > max_w and len(line) > 1:
            k = len(line) - 1
            while k > 1 and text.measure(line[:k], f) > max_w:
                k -= 1
            out.append(line[:k])
            line = line[k:]
        out.append(line)
    return out


def wrap_fit(copy, make, max_w, hi, lo, max_lines=2, balance=True):
    """(lines, font): `copy` wrapped to `max_w` at the largest size from `hi`
    down to `lo` that needs no more than `max_lines` lines, words longer than
    the width broken by force so nothing ever runs past `max_w`."""
    size = hi
    while True:
        f = make(size)
        lines = _hard_break(text.wrap(copy, f, max_w, balance=balance), f, max_w)
        if len(lines) <= max_lines or size <= lo:
            return lines, f
        size -= 2
