"""Decimal Counter with Formatting: a number counts toward its target while
always showing the same decimal places and comma groups, each digit in an
equal-width cell so the figure never shuffles sideways as it changes."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

DIGITS = '0123456789'


def format_count(value, decimals=2, sep=',', point='.'):
    """`value` as text with exactly `decimals` places and `sep` between each
    group of three integer digits, e.g. 12838.5 -> '12,838.50'. A negative
    value keeps a leading '-'."""
    sign = '-' if round(value, decimals) < 0 else ''
    return sign + f'{abs(value):,.{decimals}f}'.replace(',', '\0').replace('.', point).replace('\0', sep)


def count_value(start, end, p, ease=vb.ease_out_quint, decimals=2):
    """The value shown at progress `p` (0 -> 1) of a count from `start` to
    `end`, eased and rounded to `decimals`, landing on `end` exactly at 1."""
    p = vb.clamp01(p)
    return end if p >= 1 else round(start + (end - start) * ease(p), decimals)


def draw_counter(cv, value, font, x, y, color, decimals=2, sep=',', point='.', align='right', alpha=1.0):
    """Draw `value` formatted by `format_count`, with every digit centred in a
    cell as wide as the font's widest digit (tabular figures in any font).
    `align='right'` anchors the last digit at `x`, so new leading digits and
    commas grow leftward and the decimals stay put; `'left'` anchors the
    first character at `x`. `y` is the top. Returns the Box drawn."""
    s = format_count(value, decimals, sep, point)
    cell = max(vb.text.measure(d, font) for d in DIGITS)
    widths = [cell if ch in DIGITS else vb.text.measure(ch, font) for ch in s]
    total = sum(widths)
    left = x - total if align == 'right' else x
    cx = left
    for ch, w in zip(s, widths):
        vb.text.draw(cv, [ch], font, cx + (w - vb.text.measure(ch, font)) / 2, y, color, alpha=alpha)
        cx += w
    return vb.Box(left, y, total, vb.text.line_height(font))


def draw(n, cv):
    f = demo.font(104, 800)
    value = count_value(0, 1284507.25, demo.phase(n, 0.3, 2.5))
    right, top = demo.W / 2 + 330, demo.H / 2 - 62
    box = draw_counter(cv, value, f, right, top, demo.INK)
    cv.mark('number', *box)
    demo.word(cv, '$', demo.W / 2 - 375, demo.H / 2 + 4, size=64, color=demo.ACCENT)
    cv.line(demo.W / 2 - 410, top + box.h + 18, right + 10, top + box.h + 18, demo.LINE, width=2)
    demo.word(cv, 'TOTAL RAISED', demo.W / 2, top - 40, size=26, color=demo.MUTED, weight=700)


TECHNIQUE = Technique(
    id='decimal-counter-with-formatting',
    name='Decimal counter with formatting',
    family='typography',
    group='Counting',
    aliases=('currency counter', 'comma-grouped count', 'formatted number count-up'),
    definition='A number ticks up to its total while holding a fixed number of decimals and comma groups, '
               'its digits set in equal-width slots so the figure stays steady as it climbs.',
    phrasings=('count the dollar amount up with commas and two decimals',
               'animate the revenue figure rising without the digits wobbling',
               'a money total that rolls up to the final number, cents and all'),
    related=('odometer-roll', 'timecode-counter', 'seven-segment-display', 'stopwatch-count-up',
             'axis-rescale', 'floating-label'),
    api=('videobuilder.techniques.typography.decimal_counter_with_formatting.draw_counter',
         'videobuilder.techniques.typography.decimal_counter_with_formatting.format_count',
         'videobuilder.techniques.typography.decimal_counter_with_formatting.count_value'),
    demo=lambda: demo.film(draw),
)
