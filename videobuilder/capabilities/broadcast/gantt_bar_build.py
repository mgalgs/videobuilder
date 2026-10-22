"""Gantt Bar Build: a schedule chart fills in row by row, each task's bar
growing along the time axis from its start to its end."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def gantt_bars(cv, tasks, box, p, span=None, colors=(demo.ACCENT, demo.TEAL), ticks=6, stagger=0.55,
               label_w=110, header_h=44, ease=vb.ease_out_quint):
    """Draw a Gantt chart in `box` (a `vb.Box`) at progress `p` (0 -> 1).

    `tasks` is a list of `(label, start, end)` in axis units; `span` is the
    axis range `(lo, hi)` (default: 0 to the latest end). Rows build top to
    bottom: each bar grows from its start to its end, eased by `ease`, and
    `stagger` (0 -> 1) is how much the rows overlap in time -- 0 builds them
    one after another, 1 grows them all together. Bars take `colors` in turn.
    Returns the Box of each bar as drawn this frame."""
    lo, hi = span or (0, max(end for _, _, end in tasks))
    rows = len(tasks)
    plot = vb.Box(box.x + label_w, box.y + header_h, box.w - label_w, box.h - header_h)
    row_h = plot.h / rows
    to_x = lambda v: plot.x + (v - lo) / (hi - lo) * plot.w  # noqa: E731

    tick_f, row_f, val_f = demo.mono(16, 600), demo.font(24, 800), demo.mono(18, 700)
    for i in range(ticks + 1):
        v = lo + (hi - lo) * i / ticks
        x = to_x(v)
        cv.line(x, plot.y, x, plot.bottom, demo.LINE, width=2)
        s = f'{v:g}'
        vb.text.draw(cv, [s], tick_f, x - vb.text.measure(s, tick_f) / 2, box.y + 8, demo.MUTED)
    cv.line(plot.x, plot.y, plot.right, plot.y, demo.MUTED, width=2, alpha=0.6)

    # Each row gets an equal slot; slots overlap by `stagger` so the build flows.
    slot = 1 / (rows - (rows - 1) * stagger) if rows > 1 else 1.0
    bar_h = row_h * 0.56
    out = []
    for i, (label, start, end) in enumerate(tasks):
        cy = plot.y + row_h * (i + 0.5)
        t0 = i * slot * (1 - stagger)
        q = vb.clamp01((p - t0) / slot)
        vb.text.draw(cv, [label], row_f, box.x, cy - vb.text.line_height(row_f) / 2,
                     demo.INK, alpha=0.35 + 0.65 * vb.clamp01(q * 4))
        if q <= 0:
            continue
        x0, x1 = to_x(start), to_x(end)
        e = ease(q)
        w = max(bar_h * 0.3, (x1 - x0) * e)
        y = cy - bar_h / 2
        cv.rect(x0, y, w, bar_h, colors[i % len(colors)], radius=6)
        val = f'{(end - start) * e:.0f}'
        vw = vb.text.measure(val, val_f)
        if w > vw + 24:
            vb.text.draw(cv, [val], val_f, x0 + w - vw - 12, cy - vb.text.line_height(val_f) / 2, demo.BG)
        out.append(vb.Box(x0, y, w, bar_h))
    return out


TASKS = [('Plan', 0, 18), ('Design', 10, 42), ('Build', 30, 78), ('Test', 60, 96), ('Launch', 90, 112)]


def draw(n, cv):
    box = vb.Box(90, 70, demo.W - 180, demo.H - 140)
    for i, b in enumerate(gantt_bars(cv, TASKS, box, demo.phase(n, 0.3, 2.6), span=(0, 120))):
        cv.mark(f'bar-{i}', *b)


TECHNIQUE = Technique(
    id='gantt-bar-build',
    name='Gantt bar build',
    family='broadcast',
    group='Charts',
    aliases=('gantt chart', 'schedule bars', 'timeline bars'),
    definition='A project schedule draws itself one row at a time, each task bar stretching sideways '
               'across a time scale from the day it begins to the day it ends.',
    phrasings=('animate a project timeline with the task bars growing in one after another',
               'build up a schedule chart where each bar slides out from its start date',
               'show the roadmap phases filling in across the weeks'),
    related=('percentage-fill-bar', 'copper-bars', 'isometric-bar-rise', 'audio-waveform-bars',
             'flowchart-build', 'refresh-bar'),
    api=('videobuilder.techniques.broadcast.gantt_bar_build.gantt_bars',),
    demo=lambda: demo.film(draw),
)
