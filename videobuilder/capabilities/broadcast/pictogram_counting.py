"""Pictogram counting: a chart whose quantities are rows of identical little
icons, one icon per unit, laid down one at a time so the tally visibly piles
up while a number beside each row counts along with it."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def person(c):
    """A filled person pictogram in a unit box about the origin (head and a
    rounded body), for `draw_pictogram`."""
    c.new_sub_path()
    c.arc(0, -0.58, 0.3, 0, 2 * math.pi)
    c.new_sub_path()
    c.move_to(-0.55, 0.95)
    c.line_to(-0.55, 0.05)
    c.curve_to(-0.55, -0.22, -0.35, -0.2, 0, -0.2)
    c.curve_to(0.35, -0.2, 0.55, -0.22, 0.55, 0.05)
    c.line_to(0.55, 0.95)
    c.close_path()


def draw_pictogram(cv, glyph, cx, cy, size, color, alpha=1.0, scale=1.0):
    """Fill `glyph` (any `f(ctx)` building a path in a unit box about the
    origin, like `person`) centred at (cx, cy), `size` px tall, grown by
    `scale` about its centre."""
    if alpha <= 0 or scale <= 0:
        return
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.scale(size * scale / 2, size * scale / 2)
    c.new_path()
    glyph(c)
    c.restore()
    c.set_source_rgba(*rgba(color, alpha))
    c.fill()


def shown(p, count, pop=0.12):
    """How many of `count` icons are at least half in at progress `p`
    (0 -> 1), and the progress of icon `i` as `f(i)`: icons arrive one
    after another at an even beat, each taking `pop` of the run to grow in."""
    beat = (1 - pop) / max(1, count - 1) if count > 1 else 0

    def q(i):
        return vb.clamp01((p - i * beat) / pop)
    return sum(1 for i in range(count) if q(i) >= 0.5), q


def pictogram_row(cv, count, x, y, p, glyph=person, size=34, gap=8, per_line=20, color=demo.ACCENT,
                  ghost=None, ease=vb.ease_out_back):
    """Draw one row of `count` icons from top-left (x, y) at progress `p`
    (0 -> 1): icon after icon pops in at an even beat, wrapping after
    `per_line`. `ghost`, if given, is a colour for the empty slots still to
    fill. Returns how many icons are at least half in -- the number to show
    beside it."""
    done, q = shown(p, count)
    step = size * 0.62 + gap
    for i in range(count):
        cx = x + (i % per_line) * step + size * 0.31
        cy = y + (i // per_line) * (size + gap) + size / 2
        k = q(i)
        if ghost and k < 1:
            draw_pictogram(cv, glyph, cx, cy, size, ghost, alpha=0.35)
        if k > 0:
            draw_pictogram(cv, glyph, cx, cy, size, color, alpha=min(1, k * 3), scale=ease(k))
    return done


def pictogram_chart(cv, rows, x, y, p, label_font=None, count_font=None, row_gap=72, width=820,
                    inset=110, stagger=0.25, ink=demo.INK, **kw):
    """Draw `rows` -- (label, count, colour) tuples -- as a pictogram chart
    whose top-left is (x, y), `width` px from the labels to the right-aligned
    counts (icons start `inset` px in), at progress `p` (0 -> 1). Row `i`
    fills over its own slice of the run, each slice starting `stagger` of a
    slice after the last; each count ticks up with its icons. `kw` goes to
    `pictogram_row`. Returns each row's Box."""
    lf = label_font or demo.font(24, 800)
    cf = count_font or demo.mono(26, 700)
    n = len(rows)
    span = 1 / (1 + stagger * (n - 1)) if n > 1 else 1
    boxes = []
    for i, (label, count, color) in enumerate(rows):
        ry = y + i * row_gap
        q = vb.clamp01((p - i * stagger * span) / span)
        vb.text.draw(cv, [label], lf, x, ry + 2, ink)
        done = pictogram_row(cv, count, x + inset, ry, q, color=color, **kw)
        text = str(done)
        tw, _ = vb.text.block_size([text], cf)
        vb.text.draw(cv, [text], cf, x + width - tw, ry + 2, ink if done else demo.MUTED)
        cv.line(x, ry + row_gap - 16, x + width, ry + row_gap - 16, demo.LINE, width=2)
        boxes.append(vb.Box(x, ry, width, row_gap - 16))
    return boxes


ROWS = (('North', 14, demo.ACCENT), ('East', 9, demo.TEAL), ('South', 18, demo.ACCENT),
        ('West', 6, demo.TEAL))


def draw(n, cv):
    width, gap = 820, 76
    x = (demo.W - width) / 2
    y = demo.H / 2 - 2 * gap + 55
    draw_pictogram(cv, person, x + 9, y - 44, 24, demo.ACCENT)
    vb.text.draw(cv, ['= 1 person'], demo.font(20, 700), x + 26, y - 56, demo.MUTED)
    boxes = pictogram_chart(cv, ROWS, x, y, demo.phase(n, 0.25, 2.6), width=width, row_gap=gap,
                            size=36, gap=6, ghost=demo.LINE)
    for i, box in enumerate(boxes):
        cv.mark(f'row{i}', *box)


CAPABILITY = Capability(
    id='pictogram-counting',
    name='Pictogram counting',
    family='broadcast',
    group='Charts',
    aliases=('isotype', 'icon array count', 'unit icon chart', 'pictograph chart'),
    definition='Each quantity is shown as a row of identical small icons, one per unit, that drop in '
               'one after another while a number beside the row ticks up with them.',
    phrasings=('show the numbers as little people icons that pile up one by one',
               'a chart where each figure is counted out in rows of icons',
               'fill each row with tiny symbols until it reaches its total'),
    related=('symbol-to-letter-decode', 'infographic-icon-sequence', 'isometric-bar-rise',
             'decimal-counter-with-formatting', 'number-count-up', 'pixel-sorting'),
    api=('videobuilder.capabilities.broadcast.pictogram_counting.pictogram_chart',
         'videobuilder.capabilities.broadcast.pictogram_counting.pictogram_row',
         'videobuilder.capabilities.broadcast.pictogram_counting.draw_pictogram',
         'videobuilder.capabilities.broadcast.pictogram_counting.person'),
    demo=lambda: demo.film(draw),
)
