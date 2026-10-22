"""Waterfall build: a waterfall (bridge) chart assembled bar by bar. The first
bar rises from the baseline as the starting value; each change after it
hangs from the running level, a connector line reaching across to it before
it drops down (a loss) or climbs up (a gain); a full-height total bar lands
last."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def waterfall_levels(steps):
    """`steps` as (label, value) pairs -- the first a starting amount, the rest
    changes -- -> one (label, low, high, kind) per bar, plus a closing total.
    `kind` is 'start', 'up', 'down' or 'total'."""
    (label, level), *changes = steps
    bars = [(label, min(0, level), max(0, level), 'start')]
    for name, delta in changes:
        new = level + delta
        bars.append((name, min(level, new), max(level, new), 'up' if delta >= 0 else 'down'))
        level = new
    bars.append(('Total', min(0, level), max(0, level), 'total'))
    return bars


def waterfall_build(cv, box, steps, progress, up=demo.TEAL, down=demo.ACCENT, ends=demo.MUTED,
                    ink=demo.INK, overlap=0.35, ceiling=None, fmt='{:+g}'):
    """Draw a waterfall chart of `steps` (see `waterfall_levels`) inside `box`
    with the build `progress` 0 -> 1 through it. Bars arrive in order, each
    over its own slice of `progress` (neighbours overlap by `overlap` of a
    slice): a connector reaches from the previous bar's level, then the bar
    grows from that level toward its new one with a little overshoot, and its
    value fades in. `ceiling` fixes the chart's top value (default: the
    tallest running level plus headroom)."""
    bars = waterfall_levels(steps)
    count = len(bars)
    top = ceiling or 1.15 * max(high for _, _, high, _ in bars)
    floor_y = box.bottom - 34
    scale = (floor_y - box.y - 40) / top
    y_of = lambda v: floor_y - v * scale  # noqa: E731
    col = box.w / count
    bar_w = col * 0.62
    span = 1 / (count - (count - 1) * overlap)  # each bar's slice of progress
    label_f, value_f = demo.font(17, 600), demo.mono(18, 700)
    cv.line(box.x, floor_y, box.right, floor_y, demo.MUTED, width=2)
    values = [v for _, v in steps] + [sum(v for _, v in steps)]
    for i, (name, low, high, kind) in enumerate(bars):
        cx = box.x + col * (i + 0.5)
        vb.text.draw(cv, [name], label_f, cx - col / 2, floor_y + 8, demo.MUTED, align='center', width=col)
        start = i * span * (1 - overlap)
        p = vb.clamp01((progress - start) / span)
        if p <= 0:
            continue
        reach = vb.ease_out_expo(vb.clamp01(p / 0.3))      # connector draws across first
        grow = vb.ease_out_back(vb.clamp01((p - 0.15) / 0.7))  # then the bar hangs/rises from it
        color = {'up': up, 'down': down}.get(kind, ends)
        if i:  # connector from the previous bar's end level
            _, plow, phigh, pkind = bars[i - 1]
            level = plow if pkind == 'down' else phigh
            x0 = cx - col + bar_w / 2
            x1 = x0 + (col - bar_w) * reach
            cv.line(x0, y_of(level), x1, y_of(level), demo.MUTED, width=2, alpha=0.8)
        # grow from the anchor (previous level, or the baseline for start/total)
        anchor = {'up': low, 'down': high}.get(kind, 0)
        target = {'up': high, 'down': low}.get(kind, high)
        end = anchor + (target - anchor) * grow
        ya, yb = sorted((y_of(anchor), y_of(end)))
        if yb - ya > 0.5:
            cv.rect(cx - bar_w / 2, ya, bar_w, yb - ya, color, radius=4)
            cv.mark(f'bar-{i}', cx - bar_w / 2, ya, bar_w, yb - ya)
        tag = fmt.format(values[i]) if kind in ('up', 'down') else f'{values[i]:g}'
        a = vb.clamp01((p - 0.55) / 0.3)
        if a > 0:
            vw, vh = vb.text.block_size([tag], value_f)
            vb.text.draw(cv, [tag], value_f, cx - vw / 2, y_of(high) - vh - 8, ink, alpha=a)


STEPS = [('Q1', 40), ('Sales', 26), ('Returns', -9), ('Costs', -15), ('Upsell', 18), ('Tax', -8)]


def draw(n, cv):
    demo.word(cv, 'Profit bridge', demo.W / 2, 52, size=32, weight=700)
    box = vb.Box(90, 90, demo.W - 180, demo.H - 120)
    waterfall_build(cv, box, STEPS, demo.phase(n, 0.25, 2.6))


CAPABILITY = Capability(
    id='waterfall-build',
    name='Waterfall build',
    family='broadcast',
    group='Charts',
    aliases=('waterfall chart', 'bridge chart', 'cascade chart', 'walk chart'),
    definition='A chart whose bars appear one after another, each gain or loss hanging off the level '
               'the previous bar left, so a starting figure visibly steps up and down to a final total.',
    phrasings=('build up a bridge chart showing how we got from the starting number to the final one',
               'animate the gains and losses stepping down to the total, one bar at a time',
               'show each change floating off the last one until we reach the end total'),
    related=('flowchart-build', 'org-chart-grow', 'shape-stacking-drop', 'isometric-bar-rise',
             'audio-waveform-bars', 'dam-break'),
    api=('videobuilder.capabilities.broadcast.waterfall_build.waterfall_build',
         'videobuilder.capabilities.broadcast.waterfall_build.waterfall_levels'),
    demo=lambda: demo.film(draw),
)
