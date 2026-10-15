"""Data: bar chart. A small bar chart grows each bar on its own beat, with
the value labelled directly at the end of the bar -- no legend. The hero bar
(the series' last item) lands last and is told apart by colour.

Ported and generalised from `examples/capabilities/bar-charts.py`.
"""
import videobuilder as vb
from videobuilder import Box, fr, text

from .. import kit
from ..schema import Component, Slot

GROW = vb.damped(0.65, hz=2.5)
FPB = 9
BAR_W_FRAC = 0.6


def _axis_max(data, series):
    given = data.get('axis_max')
    if given:
        return given
    return 1.2 * max(v for _, v in series)


def _bar_p(i, n):
    return max(0.0, vb.spring_at(n - i * FPB, 30, **GROW))


def _series(raw):
    """Series items as (label, value) pairs: a plain number is labelled by its
    1-based position."""
    return [item if isinstance(item, (list, tuple)) else (str(i + 1), item) for i, item in enumerate(raw)]


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    series = _series(data['series'])
    s = kit.safe(cv)
    title_f = kit.font(26, 700)
    title_box = text.draw(cv, text.wrap(data['title'], title_f, s.w), title_f, s.x, s.y, kit.INK)
    cv.mark('title', *title_box)

    name_f = kit.font(16, 600)
    value_f = kit.mono(20, 700)
    name_h = text.line_height(name_f) + 10
    plot_top = title_box.bottom + 30
    baseline_y = s.bottom - name_h
    plot = Box(s.x, plot_top, s.w, max(10, baseline_y - plot_top))
    gap = min(28, plot.w * 0.08)
    cols = plot.row(*([fr] * len(series)), gap=gap)
    bar_w = cols[0].w * BAR_W_FRAC
    cv.line(s.x, baseline_y, s.right, baseline_y, kit.LINE, width=2)
    axis_max = _axis_max(data, series)

    for i, (col, (name, value)) in enumerate(zip(cols, series)):
        box = text.draw(cv, [name], name_f, col.x, baseline_y + 8, kit.MUTED, align='center', width=col.w)
        cv.mark(f'name-{i}', *box)
        p = _bar_p(i, shot.f)
        if p <= 0.02:
            continue
        h = min(plot.h, value * p / axis_max * plot.h)
        y = baseline_y - h
        hero = i == len(series) - 1
        fill = data['accent'] if hero else kit.LINE
        cv.rect(col.cx - bar_w / 2, y, bar_w, h, fill, radius=8)
        if not hero:
            cv.outline(col.cx - bar_w / 2, y, bar_w, h, kit.MUTED, width=2, radius=8)
        cv.mark(f'bar-{i}', col.cx - bar_w / 2, y, bar_w, h)
        shown = f'{value * min(1.0, p):.1f}'
        vw, vh = text.block_size([shown], value_f)
        label_y = max(plot.y, y - vh - 6)
        box = text.draw(cv, [shown], value_f, col.cx - vw / 2, label_y, kit.INK)
        cv.mark(f'value-{i}', *box)


COMPONENT = Component(
    id='bar-chart',
    kind='data',
    description='A bar chart that grows each bar on its own beat, values labelled directly on the bars; the last series item is the hero.',
    tags=('data', 'chart', 'bars', 'comparison'),
    formats=('16x9', '9x16', '1x1'),
    beats=(3, 6),
    slots=(
        Slot('title', 'text', True, 'The chart\'s title.', max_length=40),
        Slot('series', 'series', True,
             '2 to 6 bars, in order, as (label, number) pairs; the last one is the hero bar.'),
        Slot('axis_max', 'number', False, 'Chart ceiling; defaults to 1.2x the largest value.'),
        Slot('accent', 'color', False, 'Colour of the hero (last) bar.'),
    ),
    sample={'title': 'Stage throughput', 'accent': kit.ACCENT,
           'series': [('Baseline', 1.0), ('Cache', 1.6), ('Batch', 2.1), ('Pipeline', 3.2)]},
    draw=draw,
)
