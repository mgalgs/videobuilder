"""Bar chart race: horizontal bars, one per item, grow as their values change
over time and slide past each other so the chart is always sorted, biggest
on top, while the axis rescales to the current leader."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

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


def race_ranks(values, softness=0.025):
    """A continuous rank for each item (0 = top) as `{label: rank}`: each
    other item counts as one place above when clearly bigger and none when
    clearly smaller, blended smoothly when the two are within `softness` of
    the leader's value -- so ranks never jump as values cross. Ties break by
    label order. Keep `softness` small: a wide band leaves close rows half
    swapped for a long time; `glide_ranks` paces the swap over time instead."""
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


def glide_ranks(series, t, glide=0.4, softness=0.025, samples=16):
    """Each item's rank at time `t` as `{label: rank}`, eased over time: the
    sharp `race_ranks` averaged over a window of `glide` keyframes centred on
    `t` with a smooth (raised-cosine) weight, so every overtake is one short
    ease-in-out of about `glide` keyframes, however close the two values run."""
    if glide <= 0:
        return race_ranks(race_values(series, t), softness)
    out = dict.fromkeys(series, 0.0)
    total = 0.0
    for s in range(samples):
        u = (s + 0.5) / samples
        w = math.sin(math.pi * u) ** 2
        for lab, r in race_ranks(race_values(series, t + (u - 0.5) * glide), softness).items():
            out[lab] += w * r
        total += w
    return {lab: r / total for lab, r in out.items()}


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
                  softness=0.025, headroom=1.12, glide=0.4):
    """Draw a bar chart race at time `t` (0 -> last keyframe of `series`)
    into `box`: one horizontal bar per item, sorted biggest first, each row
    gliding to its place over about `glide` keyframes (`glide_ranks`); values
    counted on the bar ends; an axis with gridlines along the top that
    rescales so the leader always nearly fills the width. While two rows
    cross, their name and value labels fade out so they never print over each
    other. `top` shows only that many rows (the rest fade as they slide out
    below, clipped to `box`). Each item keeps its colour from `colors` by its
    position in `series`. Returns `{label: rank}`."""
    vals = race_values(series, t)
    ranks = glide_ranks(series, t, glide, softness)
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

    def text_alpha(lab):  # labels fade while another shown row is within ~0.7 of a pitch, back by the end of the swap
        gap = min((abs(ranks[lab] - ranks[o]) for o in series if o != lab and ranks[o] < rows - 0.4), default=1.0)
        x = vb.clamp01((gap - 0.3) / 0.45)
        return x * x * (3 - 2 * x)

    order = sorted(series, key=lambda lab: -ranks[lab])  # lower rows first: in a swap the higher row draws on top
    with cv.clip(box.x, box.y, box.w, box.h):
        for lab in order:
            r = ranks[lab]
            fade = vb.clamp01((rows - 0.4 - r) / 0.6)  # gone before the row's bar can leave the box
            if fade <= 0:
                continue
            idx = list(series).index(lab)
            color = colors[idx % len(colors)]
            y = plot.y + r * pitch + (pitch - bar_h) / 2
            w = max(2.0, vals[lab] / scale * plot.w)
            ta = text_alpha(lab)
            with cv.layer(opacity=fade):
                cv.rect(plot.x, y, w, bar_h, color, radius=6)
                if ta > 0:
                    lh = vb.text.line_height(label_f)
                    vb.text.draw(cv, [lab], label_f, box.x, y + (bar_h - lh) / 2, demo.INK, align='right',
                                 width=label_w - 14, alpha=ta)
                    shown = f'{round(vals[lab]):,}'
                    vw = vb.text.measure(shown, value_f)
                    vh = vb.text.line_height(value_f)
                    inside = vw + 24 < w
                    vx = plot.x + w - vw - 12 if inside else plot.x + w + 10
                    vb.text.draw(cv, [shown], value_f, vx, y + (bar_h - vh) / 2, demo.BG if inside else demo.INK,
                                 alpha=ta)
            cv.mark(f'bar-{lab}', plot.x, y, w, bar_h)
    return ranks


SERIES = {
    'Lima':   [150, 250, 380, 520, 620],
    'Oslo':   [300, 340, 380, 430, 480],
    'Cairo':  [130, 170, 230, 340, 460],
    'Quito':  [220, 240, 265, 290, 315],
    'Hanoi':  [110, 150, 190, 235, 260],
    'Perth':  [260, 280, 300, 320, 335],
    'Accra':  [50, 80, 120, 190, 295],
}
YEARS = (2020, 2021, 2022, 2023, 2024)


def draw(n, cv):
    t = (len(YEARS) - 1) * demo.phase(n, 0.3, 3.2)
    vb.text.draw(cv, ['Riders per day'], demo.font(30, 800), 60, 34, demo.INK)
    year = YEARS[min(int(t + 0.5), len(YEARS) - 1)]
    f = demo.font(92, 800)
    vb.text.draw(cv, [str(year)], f, demo.W - 60 - vb.text.measure(str(year), f), demo.H - 140, demo.MUTED,
                 alpha=0.8)
    draw_bar_race(cv, vb.Box(60, 96, demo.W - 120, demo.H - 130), SERIES, t, top=6)


CAPABILITY = Capability(
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
    api=('videobuilder.capabilities.broadcast.bar_chart_race.draw_bar_race',
         'videobuilder.capabilities.broadcast.bar_chart_race.race_values',
         'videobuilder.capabilities.broadcast.bar_chart_race.race_ranks',
         'videobuilder.capabilities.broadcast.bar_chart_race.glide_ranks'),
    demo=lambda: demo.film(draw, seconds=3.6),
)
