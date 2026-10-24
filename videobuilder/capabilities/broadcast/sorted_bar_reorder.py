"""Sorted Bar Reorder: the same idea as Bar Chart Race (`bar_chart_race.py`,
which keeps the capability) -- a ranked horizontal bar chart that re-sorts
itself as values change, bars sliding past each other into their new ranks,
with a simpler demo that skips the rescaling axis. This module's own code
stays (a film may still import it), but it is no longer a capability of its
own."""
import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'bar-chart-race'

COLORS = (demo.ACCENT, demo.TEAL, '#8b8ff7', '#f2b84b', '#6fa8dc')


def _smooth(x):
    x = vb.clamp01(x)
    return x * x * (3 - 2 * x)


def values_at(keys, t):
    """Every item's value at time `t` through `keys`, a list of keyframes,
    each a list of every item's value (items in a fixed order). `t` runs
    0 -> len(keys) - 1 and values change linearly between keyframes."""
    last = len(keys) - 1
    t = min(max(t, 0.0), float(last))
    k = min(int(t), max(last - 1, 0))
    u = t - k
    a, b = keys[k], keys[min(k + 1, last)]
    return [va + (vb_ - va) * u for va, vb_ in zip(a, b)]


def race_slots(values, band=0.08):
    """Each item's slot (0 = top, a float while moving) for a chart sorted
    biggest first: the number of items bigger than it, counted softly, so
    when two values cross they trade slots smoothly across a value gap of
    `band` (a fraction of the largest value) instead of jumping. Equal
    values keep input order."""
    width = max(band * max(abs(v) for v in values), 1e-9)
    eps = width * 1e-6
    return [sum(_smooth(0.5 + (vj - vi + (eps if j < i else -eps)) / width)
                for j, vj in enumerate(values) if j != i)
            for i, vi in enumerate(values)]


def race_state(keys, t, band=0.08):
    """The chart at time `t` through `keys` (see `values_at`): `[(value,
    slot), ...]` per item, slots from `race_slots`."""
    values = values_at(keys, t)
    return list(zip(values, race_slots(values, band)))


def draw_bar_race(cv, labels, keys, t, x, y, w, row_h, spacing=14, colors=COLORS, label_w=130,
                  font=None, value_font=None, fmt='{:,.0f}', band=0.08):
    """Draw a sorted horizontal bar chart from its top-left (x, y), `w` wide,
    at time `t` through `keys` (see `values_at`). Each row is `row_h` tall,
    `spacing` apart: a label in the left `label_w`, then a bar scaled to the
    current leader with its value (`fmt`) at the tip. Whenever one value
    overtakes another the two rows slide past each other, the one moving up
    drawn on top; `band` sets how gradual the swap is (see `race_slots`). Returns each
    item's row Box, in `labels` order."""
    font = font or demo.font(round(row_h * 0.42), 700)
    value_font = value_font or demo.mono(round(row_h * 0.36), 700)
    state = race_state(keys, t, band)
    top = max(v for v, _ in state) or 1.0
    track = w - label_w - vb.text.measure(fmt.format(top) + '00', value_font)
    pitch = row_h + spacing
    boxes = [None] * len(labels)
    # draw rows moving down first, then still ones, then climbers, so overtakers pass in front
    climb = [later - now for (_, now), (_, later) in zip(state, race_state(keys, t + 0.02, band))]
    for i in sorted(range(len(labels)), key=lambda i: -climb[i]):
        v, slot = state[i]
        ry = y + slot * pitch
        box = vb.Box(x, ry, w, row_h)
        boxes[i] = box
        lh = vb.text.line_height(font)
        vb.text.draw(cv, [labels[i]], font, x + label_w - 14 - vb.text.measure(labels[i], font),
                     ry + (row_h - lh) / 2, demo.INK)
        bw = max(row_h * 0.2, track * v / top)
        cv.rect(x + label_w, ry, bw, row_h, colors[i % len(colors)], radius=6)
        shown = fmt.format(v)
        vh = vb.text.line_height(value_font)
        vb.text.draw(cv, [shown], value_font, x + label_w + bw + 10, ry + (row_h - vh) / 2, demo.MUTED)
        cv.mark(f'bar-{i}', *box)
    return boxes


LABELS = ('Rivera', 'Okafor', 'Lindqvist', 'Tanaka', 'Moreau')
KEYS = (
    (820, 610, 540, 400, 300),
    (900, 1010, 640, 560, 520),
    (980, 1240, 1300, 760, 610),
    (1060, 1380, 1520, 1180, 1590),
)


def draw(n, cv):
    t = (len(KEYS) - 1) * demo.phase(n, 0.25, 2.75)
    w, row_h, spacing = 800, 54, 14
    rows = len(LABELS)
    x = (demo.W - w) / 2
    y = (demo.H - (rows * row_h + (rows - 1) * spacing)) / 2 + 26
    f = demo.mono(26, 800)
    year = f'{2021 + round(t)}'
    vb.text.draw(cv, [year], f, x + w - vb.text.measure(year, f), y - 62, demo.MUTED)
    vb.text.draw(cv, ['Points scored'], demo.font(26, 800), x, y - 62, demo.INK)
    draw_bar_race(cv, LABELS, KEYS, t, x, y, w, row_h, spacing=spacing)
