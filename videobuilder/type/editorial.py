"""Editorial stack: a magazine-cover headline. Heavy capitals stacked tight
and set as big as the frame allows, each line revealed by a hard block of
the accent that sweeps across it and peels away, staggered (after
title_editorial_wipe). A hairline rule draws across the top first, and a
halftone plate in the accent fills the room the type leaves -- above the
stack in a tall or square frame, beside it in a wide one. Through the hold
the plate's dots drift and the lines slide a little against each other;
on the exit the blocks sweep back over the lines and carry them off.
"""
import math

import cairo
from functools import lru_cache

from .. import text
from ..canvas import halftone_pattern, paper_grain
from ..ease import ease_in_out_quart, ease_out_quint
from ..layout import Box
from ..text import Font
from . import kit
from .style import Style


def _font(family, size):
    return Font(family, size, weight=900, tracking=-0.03, line_height=0.9)


@lru_cache(maxsize=64)
def _layout(lines, box, family):
    """(inner, font, stack top-left, the plate's box or None, rule y)."""
    inner = box.pad(0.07 * min(box.w, box.h))
    k = kit.shape(box)
    if k == 'wide':
        font = kit.fit(lines, lambda s: _font(family, s), inner.w * 0.62, inner.h * 0.82)
    else:
        font = kit.fit(lines, lambda s: _font(family, s), inner.w, inner.h * (0.56 if k == 'tall' else 0.6))
    lh = text.line_height(font)
    bw = max(text.measure(ln, font) for ln in lines)
    bh = lh * len(lines)
    gap = inner.h * 0.04
    if k == 'wide' and bw < inner.w * 0.68:
        rule_y = inner.y
        x, y = inner.x, inner.bottom - bh
        px = x + bw + inner.w * 0.05
        pw = min(inner.right - px, (inner.bottom - rule_y - gap) * 0.8)
        plate = Box(inner.right - pw, rule_y + gap, pw, inner.bottom - rule_y - gap)
    else:
        # The plate, the stack and the rule over them, centred as one group.
        ph = max(0.0, min(inner.h - bh - 2 * gap, inner.w * 0.7))
        top = inner.cy - (ph + gap + bh) / 2 + gap / 2
        rule_y = top - gap
        plate = Box(inner.x, top, inner.w, ph)
        x, y = inner.x, top + ph + gap
    if plate.w < inner.w * 0.12 or plate.h < inner.h * 0.08:
        plate = None
    return font, lh, x, y, plate, rule_y, inner


def _beats(n, hold, exit_t, length):
    """(cover, peel, stagger, first) for the enter and the exit."""
    avail = hold * 0.7
    unit = avail / (0.4 * (n - 1) + 0.6)
    out = length - exit_t
    xunit = out * 0.9 / (0.25 * (n - 1) + 0.6)
    return (0.28 * unit, 0.32 * unit, 0.4 * unit, hold * 0.22), (0.3 * xunit, 0.3 * xunit, 0.25 * xunit, exit_t)


def draw(cv, p, t, box, clock):
    box = Box(*box)
    lines = tuple(ln.upper() for ln in p.lines)
    font, lh, x0, y0, plate, rule_y, inner = _layout(lines, box, STYLE.font_family(p))
    (cover, peel, stagger, first), (xcover, xpeel, xstagger, xfirst) = _beats(len(lines), clock.hold, clock.exit,
                                                                              p.length)
    if p.paper is not None:
        ctx = cv.ctx
        ctx.save()
        ctx.set_source(paper_grain(cv.width, cv.height, seed=4))
        ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
        ctx.paint_with_alpha(0.3)
        ctx.restore()
    out = clock.leaving(t)
    held = t - clock.hold
    # The rule: draws across, and back off on the exit.
    r = ease_in_out_quart(min(1.0, t / (clock.hold * 0.3))) * (1 - ease_in_out_quart(out))
    if r > 0:
        cv.line(inner.x, rule_y, inner.x + inner.w * r, rule_y, p.ink, width=max(1.5, inner.h * 0.003))
        cv.rect(inner.x, rule_y + inner.h * 0.012, inner.h * 0.018, inner.h * 0.018, p.accent, alpha=r)
    # The plate: a halftone field in the accent, wiping on, its dots drifting.
    if plate is not None:
        a = ease_in_out_quart(min(1.0, max(0.0, (t - clock.hold * 0.1) / (clock.hold * 0.4))))
        z = ease_in_out_quart(min(1.0, max(0.0, (out - 0.15) / 0.6)))
        x_from, x_to = plate.x + plate.w * z, plate.x + plate.w * a
        if x_to > x_from:
            cv.rect(x_from, plate.y, x_to - x_from, plate.h, p.accent)
            ctx = cv.ctx
            dots = kit.mix(p.accent, (0, 0, 0), 0.6) + (0.45,)
            bands = 6
            pitch = max(6.0, min(plate.w, plate.h) / 26)
            for b in range(bands):
                bx0 = plate.x + plate.w * b / bands
                bx1 = min(plate.x + plate.w * (b + 1) / bands + 0.5, x_to)
                bx0 = max(bx0, x_from)
                if bx1 <= bx0:
                    continue
                with cv.clip(bx0, plate.y, bx1 - bx0, plate.h):
                    ctx.save()
                    ctx.translate(-t * pitch * 1.8, t * pitch * 0.6)
                    ctx.set_source(halftone_pattern(pitch, pitch * (0.08 + 0.36 * b / (bands - 1)), math.radians(30),
                                                    dots))
                    ctx.paint()
                    ctx.restore()
    # The stack: a block per line sweeps on, the line is there as it peels off.
    with cv.layer(**kit.camera(t, clock.hold, box.cx, y0 + lh * len(lines), box, k=0.03)):
        for i, line in enumerate(lines):
            y = y0 + i * lh
            w = text.measure(line, font)
            bx, bw = x0 - lh * 0.06, w + lh * 0.12
            slide = math.sin(2 * math.pi * held / 6.0 + i * 1.7) * inner.w * 0.012 * min(1.0, max(0.0, held))
            u = t - first - i * stagger
            xu = t - xfirst - i * xstagger
            if u <= 0:
                continue
            gone = xu >= xcover
            if u >= cover and not gone:
                q = ease_out_quint(min(1.0, (u - cover) / (peel * 1.6)))
                box_ = text.draw(cv, [line], font, x0 - (1 - q) * lh * 0.2 + slide, y, p.ink)
                if xu < 0 and q > 0.9:
                    cv.mark(f'line-{i}', *box_)
            top, hgt = y + lh * 0.04, lh * 0.9
            if u < cover:
                a = ease_in_out_quart(u / cover)
                cv.rect(bx, top, bw * a, hgt, p.accent)
            elif u < cover + peel:
                a = ease_in_out_quart((u - cover) / peel)
                cv.rect(bx + bw * a, top, bw * (1 - a), hgt, p.accent)
            if 0 <= xu < xcover:
                a = ease_in_out_quart(xu / xcover)
                cv.rect(bx + slide, top, bw * a, hgt, p.accent)
            elif xcover <= xu < xcover + xpeel:
                a = ease_in_out_quart((xu - xcover) / xpeel)
                cv.rect(bx + slide + bw * a, top, bw * (1 - a), hgt, p.accent)


STYLE = Style('editorial', 'Editorial stack', 'heavy stacked lines, each revealed by a hard wipe in the accent',
              draw, aliases=('editorial stack', 'magazine', 'magazine cover', 'stack', 'wipe', 'hard wipe'))
