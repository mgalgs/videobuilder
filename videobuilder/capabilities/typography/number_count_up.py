"""Number Count-up: the same stat counting up as Numbers that count up
(`counting_numbers.py`), which keeps the capability -- a figure runs up
from a starting value to its final one, fast at first and slowing as it
lands, then holds. This module's own code stays (a film may still import
it), but it is no longer a capability of its own. (The `stat-counter`
compendium component is a whole slide built on the same idea; this is the
move on its own, for any number in any layout.)"""
import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'counting-numbers'


def _decimals(*values):
    """Decimals that every value in `values` needs (0, 1 or 2), so 0 -> 2.4
    counts as 0.0, 0.1, ... rather than changing width part-way."""
    best = 0
    for v in values:
        if not float(v).is_integer():
            best = max(best, 1 if abs(round(v, 1) - v) < 1e-9 else 2)
    return best


def count_up(value, p, start=0, decimals=None, prefix='', suffix='', separator=',', ease=vb.ease_out_expo):
    """The text of a number counting from `start` to `value` at progress `p`
    (0 -> 1, eased by `ease`). `decimals` defaults to what `start` and
    `value` need; `separator` groups thousands ('' for none). At `p` = 1 the
    text is exactly the final value."""
    p = vb.clamp01(p)
    d = _decimals(start, value) if decimals is None else decimals
    shown = value if p >= 1 else start + (value - start) * ease(p)
    body = f'{abs(shown):,.{d}f}'.replace(',', separator)
    sign = '−' if round(shown, d) < 0 else ''
    return f'{prefix}{sign}{body}{suffix}'


def draw_count_up(cv, value, font, x, y, p, color, align='right', **kw):
    """Draw `value` counting up at progress `p` inside the box its final text
    takes up, top-left at (x, y). The number is right-aligned in that box by
    default, so digits grow leftwards and the units column never moves; use
    a monospaced or tabular-figure font to stop the digits jittering. `kw`
    goes to `count_up`. Returns the Box of the final text."""
    final = count_up(value, 1, **kw)
    w, h = vb.text.block_size([final], font)
    vb.text.draw(cv, [count_up(value, p, **kw)], font, x, y, color, align=align, width=w)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    p = demo.phase(n, 0.3, 2.2)
    f = demo.mono(150, 700)
    w, h = vb.text.block_size([count_up(48250, 1)], f)
    x, y = (demo.W - w) / 2, demo.H / 2 - h / 2 - 40
    box = draw_count_up(cv, 48250, f, x, y, p, demo.INK)
    cv.mark('number', *box)
    bar_w = 520
    bx = (demo.W - bar_w) / 2
    cv.rect(bx, y + h + 36, bar_w, 6, demo.LINE, radius=3)
    cv.rect(bx, y + h + 36, bar_w * vb.ease_out_expo(p), 6, demo.ACCENT, radius=3)
    demo.word(cv, 'people signed up', demo.W / 2, y + h + 96, size=40, color=demo.MUTED, weight=600)
