"""Bar chart race: horizontal bars, one per item, grow as their values change
over time and slide past each other so the chart is always sorted, biggest
on top, while the axis rescales to the current leader."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

COLORS = ('#ef5b4c', '#4fc3b0', '#f2b84b', '#7b8cff', '#d27ce8', '#6cc56a', '#e8875a', '#5bb8e8')


def race_values(series, t):
    """Each item's value at time `t`, as `{label: value}`. `series` maps a
    label to its values at keyframes 0, 1, 2...; `t` runs 0 -> last keyframe
    and values are interpolated linearly between neighbouring keyframes."""
    out = {}
    for label, vals in series.items():
        t_ = min(max(t, 0.0), len(vals) - 1)
        i = min(int(t_), len(vals) - 2) if len(vals) > 1 else 0
        k = t_ - i
        out[label] = vals[i] + (vals[min(i + 1, len(vals) - 1)] - vals[i]) * k
    return out


def race_ranks(values, softness=0.08):
    """A continuous rank for each item (0 = top) as `{label: rank}`: each
    other item counts as one place above when clearly bigger and none when
    clearly smaller, blended smoothly when the two are within `softness` of
    the leader's value -- so rows glide past each other as their values cross
    instead of jumping. Ties break by label order."""
    peak = max((abs(v) for v in values.values()), default=0.0) or 1.0
    eps = softness * peak
    labels = list(values)
    ranks = {}
    for i, a in enumerate(labels):
        r = 0.0
        for j, b in enumerate(labels):
            if a == b:
                continue
            d = (values[b] - values[a]) / eps + (1e-6 if j < i else -1e-6)
            x = vb.clamp01((d + 1) / 2)
            r += x * x * (3 - 2 * x)
        ranks[a] = r
    return ranks


def _nice_step(span, ticks=4):
    raw = span / ticks
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def _short(v):
    if abs(v) >= 1e6:
        return f'{v / 1e6:g}M'
    if abs(v) >= 1e3:
        return f'{v / 1e3:g}k'
    return f'{v:g}'


def draw_bar_race(cv, box, series, t, top=None, colors=COLORS, label_font=None, value_font=None,
                  softness=0.08, headroom=1.12):
    """Draw a bar chart race at time `t` (0 -> last keyframe of `series`)
    into `box`: one horizontal bar per item, sorted biggest first by
    `race_ranks`, each row gliding to its place; values counted on the bar
    ends; an axis with gridlines along the top that rescales so the leader
    always nearly fills the width. `top` shows only that many rows (the rest
    slide out below and fade). Each item keeps its colour from `colors` by
    its position in `series`. Returns `{label: rank}`."""
    vals = race_values(series, t)
    ranks = race_ranks(vals, softness)
    n = len(series)
    rows = min(top or n, n)
    label_f = label_font or demo.font(20, 700)
    value_f = value_font or demo.mono(17, 700)
    label_w = max(vb.text.measure(lab, label_f) for lab in series) + 18
    axis_h = 28
    plot = vb.Box(box.x + label_w, box.y + axis_h, box.w - label_w, box.h - axis_h)
    pitch = plot.h / rows
    bar_h = pitch * 0.74
    scale = max(max(vals.values()), 1e-9) * headroom

    tick_f = demo.mono(13, 500)
    step = _nice_step(scale)
    k = 0
    while k * step <= scale:
        x = plot.x + k * step / scale * plot.w
        cv.line(x, plot.y - 4, x, plot.bottom, demo.LINE, width=1.5)
        vb.text.draw(cv, [_short(k * step)], tick_f, x - 40, box.y, demo.MUTED, align='center', width=80)
        k += 1

    order = sorted(series, key=lambda lab: -ranks[lab])  # lower rows first: in a swap the higher row draws on top
    for lab in order:
        r = ranks[lab]
        fade = vb.clamp01(rows - r)
        if fade <= 0:
            continue
        idx = list(series).index(lab)
        color = colors[idx % len(colors)]
        y = plot.y + r * pitch + (pitch - bar_h) / 2
        w = max(2.0, vals[lab] / scale * plot.w)
        with cv.layer(opacity=fade):
            cv.rect(plot.x, y, w, bar_h, color, radius=6)
            lh = vb.text.line_height(label_f)
            vb.text.draw(cv, [lab], label_f, box.x, y + (bar_h - lh) / 2, demo.INK, align='right',
                         width=label_w - 14)
            shown = f'{round(vals[lab]):,}'
            vw = vb.text.measure(shown, value_f)
            vh = vb.text.line_height(value_f)
            inside = vw + 24 < w
            vx = plot.x + w - vw - 12 if inside else plot.x + w + 10
            vb.text.draw(cv, [shown], value_f, vx, y + (bar_h - vh) / 2, demo.BG if inside else demo.INK)
        cv.mark(f'bar-{lab}', plot.x, y, w, bar_h)
    return ranks


SERIES = {
    'Lima':   [120, 260, 430, 560, 640],
    'Oslo':   [300, 390, 450, 500, 540],
    'Cairo':  [60, 180, 380, 620, 900],
    'Quito':  [210, 330, 360, 380, 400],
    'Hanoi':  [160, 200, 300, 470, 760],
    'Perth':  [250, 280, 310, 330, 350],
    'Accra':  [40, 90, 160, 280, 470],
}
YEARS = (2020, 2021, 2022, 2023, 2024)


def draw(n, cv):
    t = (len(YEARS) - 1) * demo.phase(n, 0.25, 2.75)
    vb.text.draw(cv, ['Riders per day'], demo.font(30, 800), 60, 34, demo.INK)
    year = YEARS[min(int(t + 0.5), len(YEARS) - 1)]
    f = demo.font(92, 800)
    vb.text.draw(cv, [str(year)], f, demo.W - 60 - vb.text.measure(str(year), f), demo.H - 140, demo.MUTED,
                 alpha=0.8)
    draw_bar_race(cv, vb.Box(60, 96, demo.W - 120, demo.H - 130), SERIES, t, top=6)


TECHNIQUE = Technique(
    id='bar-chart-race',
    name='Bar chart race',
    family='broadcast',
    group='Charts',
    aliases=('racing bar chart', 'ranked bar race', 'bar race'),
    definition='Horizontal bars for several items grow with their changing values over time and slide '
               'past one another, so the chart stays sorted with the biggest always on top.',
    phrasings=('animate the rankings over the years with bars overtaking each other',
               'a sorted bar chart where the bars swap places as the numbers change',
               'show which item pulls ahead over time as a race of bars'),
    related=('leaderboard-row-swap', 'percentage-fill-bar', 'audio-waveform-bars', 'refresh-bar',
             'balance-bar-tug', 'poll-result-bar-fill'),
    api=('videobuilder.techniques.broadcast.bar_chart_race.draw_bar_race',
         'videobuilder.techniques.broadcast.bar_chart_race.race_values',
         'videobuilder.techniques.broadcast.bar_chart_race.race_ranks'),
    demo=lambda: demo.film(draw),
)
