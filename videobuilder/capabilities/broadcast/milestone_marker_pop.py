"""Milestone Marker Pop: a horizontal timeline whose markers pop up one after
another, each growing a short stem that lifts its date and label into view,
while a progress line runs along the axis from marker to marker."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def milestone_markers(cv, milestones, p, x0, x1, y, color=demo.ACCENT, line=demo.TEAL,
                      track=demo.LINE, ink=demo.INK, r=16, stem=70, stagger=0.75):
    """Draw a timeline from `x0` to `x1` at height `y` with `milestones`, a
    list of `(date, label)` spaced evenly along it, at progress `p` (0 -> 1).

    Each marker gets an equal slot of the progress; within its slot it pops
    in with an overshoot (`vb.ease_out_back`), then its stem grows and the
    date and label rise into place. `stagger` < 1 lets the next marker start
    before the previous one has finished. The progress line reaches each
    marker as it pops. Returns the marker centres."""
    k = len(milestones)
    xs = [x0 + (x1 - x0) * (i + 0.5) / k for i in range(k)] if k > 1 else [(x0 + x1) / 2]
    slot = 1 / (1 + (k - 1) * stagger) if k else 1
    starts = [i * slot * stagger for i in range(k)]
    cv.line(x0, y, x1, y, track, width=4)
    # the progress line runs from the first marker to whichever marker is popping now
    for i in range(1, k):
        reach = vb.clamp01((p - starts[i] + slot * 0.2) / (slot * 0.25))
        if reach > 0:
            cv.line(xs[i - 1], y, xs[i - 1] + (xs[i] - xs[i - 1]) * vb.ease_out_quint(reach), y, line, width=5)
    df, lf = demo.font(22, 800), demo.font(30, 800)
    for i, (date, label) in enumerate(milestones):
        q = vb.clamp01((p - starts[i]) / slot)
        if q <= 0:
            continue
        pop = vb.ease_out_back(vb.clamp01(q / 0.35))
        grow = vb.ease_out_quint(vb.clamp01((q - 0.2) / 0.35))
        text = vb.ease_out_quint(vb.clamp01((q - 0.4) / 0.4))
        x = xs[i]
        if grow > 0:
            cv.line(x, y - r, x, y - r - stem * grow, line, width=4)
        if text > 0:
            top = y - r - stem - 16 + 24 * (1 - text)
            demo.word(cv, label, x, top - 18, font=lf, alpha=text)
            demo.word(cv, date, x, top - 58, font=df, color=color, alpha=text)
        if pop > 0:
            rr = r * pop
            demo.dot(cv, x, y, rr, color=color)
            demo.dot(cv, x, y, rr * 0.45, color=demo.BG)
            cv.mark(f'marker{i}', x - rr, y - rr, 2 * rr, 2 * rr)
    return xs


MILESTONES = (('FEB 03', 'Kickoff'), ('MAR 14', 'Prototype'), ('APR 22', 'Review'), ('JUN 06', 'Launch'))


def draw(n, cv):
    milestone_markers(cv, MILESTONES, demo.phase(n, 0.3, 2.6), 60, demo.W - 60, demo.H / 2 + 90)


TECHNIQUE = Technique(
    id='milestone-marker-pop',
    name='Milestone marker pop',
    family='broadcast',
    group='Process diagrams',
    aliases=('timeline milestone', 'event marker', 'timeline pop-in'),
    definition='Dots spring up one at a time along a timeline axis, each lifting a little stem '
               'that shows a date and a short name for that step.',
    phrasings=('show the project dates popping onto a timeline one by one',
               'animate the roadmap so each milestone appears in turn with its date',
               'a timeline where the key events pop in left to right'),
    related=('callout-highlight', 'circle-pop', 'numbered-hotspot-pins', 'circle-check-draw',
             'live-indicator-pulse', 'scatter-plot-point-appear'),
    api=('videobuilder.techniques.broadcast.milestone_marker_pop.milestone_markers',),
    demo=lambda: demo.film(draw),
)
