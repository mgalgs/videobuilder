"""Split-flap: a departures board. Each letter's flap falls through a run of
characters before it settles on its own, the cells starting left to right
and row by row, so the lines clatter in as a wave. Blank cells round the
copy flip now and then through the hold, a lamp beside each settled line
pulses in the accent, and the board pushes in slowly; on the exit every
letter flips back to blank.

The board is laid out per frame shape: as many columns as the longest line
plus a blank either side, the cells as big as the width (wide: the height)
allows, and blank rows above and below wherever the frame has room, so a
tall frame is a whole board, not a strip.
"""
import math
from functools import lru_cache

from .. import text
from ..layout import Box
from ..text import Font
from . import kit
from .style import Style

FLIP = 0.065            # s per flap
EXIT_FLIP = 0.05
ASPECT = 0.72           # a cell's width over its height
GAP = 0.1               # between cells, as a share of a cell's width
EXTRA_ROWS = {'tall': 12, 'square': 6, 'wide': 4}   # at most this many blank rows round the copy
CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'


def _lines(p):
    return tuple(ln.upper() for ln in p.lines)


@lru_cache(maxsize=64)
def _board(lines, box, family):
    """(cols, rows, first text row, cell w, cell h, gap, board origin, font)."""
    cols = max(len(ln) for ln in lines) + 2
    n = len(lines)
    inner, w, h, k = kit.room(box, tall=(1.0, 0.9), wide=(0.94, 0.86), square=(0.98, 0.9))
    cw = w / (cols + (cols - 1) * GAP)
    ch = cw / ASPECT
    want = n + (2 if k != 'wide' or h > (n + 2) * ch else 0)
    max_ch = h / (want + (want - 1) * GAP * ASPECT)
    if ch > max_ch:
        ch = max_ch
        cw = ch * ASPECT
    gap = GAP * cw
    rows = max(n, min(n + EXTRA_ROWS[k], int((h + gap) // (ch + gap))))
    if (rows - n) % 2:
        rows -= 1
    bw, bh = cols * cw + (cols - 1) * gap, rows * ch + (rows - 1) * gap
    x0, y0 = inner.cx - bw / 2, inner.cy - bh / 2
    font = Font(family, round(ch * 0.74), weight=700)
    return cols, rows, (rows - n) // 2, cw, ch, gap, (x0, y0), font


def _targets(lines, cols):
    """The settled character of every text cell: {(row, col): char}."""
    out = {}
    for r, line in enumerate(lines):
        off = (cols - len(line)) // 2
        for i, c in enumerate(line):
            out[(r, off + i)] = c
    return out


@lru_cache(maxsize=32)
def _plan(lines, cols, rows, first, length, hold, exit_t):
    """Every cell's bursts of flaps: {(board row, col): [(t0, flap s, chars), ...]},
    chars running from the one showing to the one it settles on."""
    targets = _targets(lines, cols)
    rnd = kit.rng('split-flap', '|'.join(lines))
    plan = {}
    enter = {}
    for (r, c), ch in targets.items():
        if ch == ' ':
            continue
        start = 0.10 + 0.055 * c + 0.16 * r + rnd.uniform(0, 0.12)
        seq = [' '] + [rnd.choice(CHARS) for _ in range(rnd.randint(5, 10))] + [ch]
        enter[(r, c)] = (start, seq)
    longest = max((len(s) - 1) * FLIP for _, s in enter.values()) if enter else 0
    latest = max((st for st, _ in enter.values()), default=0) or 1
    k = min(1.0, max(0.05, hold - longest - 0.05) / latest)
    out_len = length - exit_t
    x_latest = max((0.03 * c + 0.06 * r for (r, c) in enter), default=0) or 1
    xk = min(1.0, max(0.0, out_len - 4 * EXIT_FLIP - 0.05) / x_latest)
    for (r, c), (start, seq) in enter.items():
        back = [seq[-1]] + [rnd.choice(CHARS) for _ in range(2)] + [' ']
        plan[(first + r, c)] = [(start * k, FLIP, seq), (exit_t + (0.03 * c + 0.06 * r) * xk, EXIT_FLIP, back)]
    # The hold: blank cells (never a line's lamp, a gap between its words, nor
    # the cell either side of it, which would read as a letter of the line)
    # flip a few characters and back.
    lamps = {(first + r, 0) for r in range(len(lines))}
    copy = {(first + r, c + d) for (r, c) in targets for d in (-1, 0, 1)}
    for r in range(rows):
        for c in range(cols):
            if (r, c) in copy or (r, c) in lamps:
                continue
            bursts, t = [], hold + rnd.uniform(0, 1.6)
            while t < exit_t - 0.4:
                seq = [' '] + [rnd.choice(CHARS) for _ in range(rnd.randint(2, 4))] + [' ']
                bursts.append((t, FLIP, seq))
                t += (len(seq) - 1) * FLIP + rnd.uniform(1.0, 3.2)
            if bursts:
                plan[(r, c)] = bursts
    return plan


def _state(bursts, t):
    """(showing, next, flap progress or None) of a cell at `t`."""
    showing = bursts[0][2][0] if bursts else ' '
    for t0, d, seq in bursts:
        if t < t0:
            break
        j = int((t - t0) / d)
        if j < len(seq) - 1:
            return seq[j], seq[j + 1], (t - t0) / d - j
        showing = seq[-1]
    return showing, showing, None


def _half(cv, x, y, cw, ch, char, top, sy, font, panel, ink, shade=0.0):
    """One half of a cell (the top or the bottom) showing `char`, folded to
    `sy` of its height about the hinge."""
    if sy < 0.02:
        return
    ctx = cv.ctx
    hinge = y + ch / 2
    ctx.save()
    ctx.translate(0, hinge)
    ctx.scale(1, sy)
    ctx.translate(0, -hinge)
    with cv.clip(x, y if top else hinge, cw, ch / 2):
        cv.rect(x, y, cw, ch, panel, radius=cw * 0.08)
        if char != ' ':
            lh = text.line_height(font)
            text.draw(cv, [char], font, x + (cw - text.measure(char, font)) / 2, y + (ch - lh) / 2, ink)
        if shade:
            cv.rect(x, y, cw, ch, (0, 0, 0, shade))
    ctx.restore()


def draw(cv, p, t, box, clock):
    lines = _lines(p)
    cols, rows, first, cw, ch, gap, (x0, y0), font = _board(lines, Box(*box), STYLE.font_family(p))
    plan = _plan(lines, cols, rows, first, p.length, clock.hold, clock.exit)
    g = kit.ground(p)
    panel = kit.mix(g, p.ink, 0.11)
    lower = kit.mix(g, p.ink, 0.085)
    flap_panel = kit.mix(panel, p.accent, 0.22)
    bw, bh = cols * cw + (cols - 1) * gap, rows * ch + (rows - 1) * gap
    with cv.layer(**kit.camera(t, clock.hold, x0 + bw / 2, y0 + bh / 2, box, k=0.05)):
        cv.rect(x0 - gap * 2, y0 - gap * 2, bw + gap * 4, bh + gap * 4, kit.mix(g, (0, 0, 0), 0.35), radius=gap * 3)
        for r in range(rows):
            for c in range(cols):
                x, y = x0 + c * (cw + gap), y0 + r * (ch + gap)
                cur, nxt, q = _state(plan.get((r, c), ()), t)
                if q is None:
                    _half(cv, x, y, cw, ch, cur, True, 1, font, panel, p.ink)
                    _half(cv, x, y, cw, ch, cur, False, 1, font, lower, p.ink)
                else:
                    _half(cv, x, y, cw, ch, nxt, True, 1, font, panel, p.ink)
                    _half(cv, x, y, cw, ch, cur, False, 1, font, lower, p.ink)
                    if q < 0.5:   # the top flap falls: the old letter's top half, folding to the hinge
                        _half(cv, x, y, cw, ch, cur, True, math.cos(math.pi * q), font, flap_panel, p.ink, 0.35 * q)
                    else:         # and lands as the new letter's bottom half
                        _half(cv, x, y, cw, ch, nxt, False, -math.cos(math.pi * q), font, flap_panel, p.ink,
                              0.35 * (1 - q))
                cv.rect(x, y + ch / 2 - ch * 0.012, cw, ch * 0.024, kit.mix(g, (0, 0, 0), 0.5))
        targets = _targets(lines, cols)
        for i, line in enumerate(lines):
            r = first + i
            settled = all(_state(plan[(r, c)], t) == (ch_, ch_, None)
                          for (ri, c), ch_ in targets.items() if ri == i and ch_ != ' ')
            lx, ly = x0 + cw / 2, y0 + r * (ch + gap) + ch / 2
            lit = settled and clock.hold * 0.5 < t < clock.exit
            pulse = 0.65 + 0.35 * math.sin(2 * math.pi * (t - clock.hold) / 1.6 - i * 0.9)
            cv.ctx.arc(lx, ly, cw * 0.2, 0, 2 * math.pi)
            cv.ctx.set_source_rgba(*kit.rgba(p.accent, pulse) if lit else kit.rgba(kit.mix(g, p.ink, 0.2)))
            cv.ctx.fill()
            if settled:
                off = (cols - len(line)) // 2
                cv.mark(f'line-{i}', x0 + off * (cw + gap), y0 + r * (ch + gap), len(line) * (cw + gap) - gap, ch)


def events(p, clock):
    """A flap at every change of every text cell, thinned to one per 1/25 s:
    a board clatters as one."""
    lines = _lines(p)
    cols = max(len(ln) for ln in lines) + 2
    plan = _plan(lines, cols, len(lines), 0, p.length, clock.hold, clock.exit)
    times = sorted(t0 + j * d for (r, c), bursts in plan.items() if r < len(lines) and
                   _targets(lines, cols).get((r, c), ' ') != ' '
                   for t0, d, seq in bursts for j in range(1, len(seq)))
    out, last = [], -1.0
    for t in times:
        if t - last >= 0.04:
            out.append((t, 'flap'))
            last = t
    return out


STYLE = Style('split-flap', 'Split-flap board', 'each letter flips through the alphabet and settles, cell by cell',
              draw, aliases=('splitflap', 'departures', 'departures board', 'flap board', 'solari'),
              events=events, sound={'flap': (('fit/tick/domino', 'click/tink', 'pro_click/tink'), ('tick', 'click'),
                                             -14.0)},
              family='monospace')
