"""Capability: self-drawing line chart with a callout. Axes first, then every
series draws itself on along its own path (`videobuilder.paths.reveal`), the
background series in grey and only the hero series in the accent colour, then
one callout -- a dot, a leader line and a short label -- calls out the point
that matters. Axes are honest: the baseline is zero and the scale is labelled.

    python -m videobuilder preview examples/capabilities/line-chart-callout.py

LOOP = True: the chart rests on empty axes at both ends -- the lines draw on,
the callout arrives, holds, then both retract in reverse, exactly as
bar-charts.py grows and shrinks its bars.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, paths, text  # noqa: E402

LOOP = True
FPS = 30
AXES_HOLD = 6     # frames of empty axes before the lines start
DRAW = 36         # frames for both lines to draw on
CALLOUT = 20      # frames for the callout to animate in
HOLD = 20         # frames holding the finished, called-out chart
RETRACT_CALLOUT = 10
RETRACT_LINES = 20
TAIL = 6          # rest frames on empty axes again

T_DRAW = AXES_HOLD + DRAW
T_CALLOUT = T_DRAW + CALLOUT
T_HOLD = T_CALLOUT + HOLD
T_RC = T_HOLD + RETRACT_CALLOUT
T_RL = T_RC + RETRACT_LINES
TOTAL = T_RL + TAIL

TITLE_F = _kit.font(32, 700)
AXIS_F = _kit.font(18, 600)
CAT_F = _kit.font(18, 500)
CALLOUT_F = _kit.font(22, 700, family=_kit.MONO)

WEEKS = ('W1', 'W2', 'W3', 'W4', 'W5', 'W6')
PLAN = (1.0, 1.3, 1.5, 1.7, 1.8, 2.0)
ACTUAL = (1.0, 1.4, 1.9, 2.3, 2.9, 3.6)
AXIS_MAX = 4.0
HERO_LABEL = f'{ACTUAL[-1] / PLAN[-1]:.1f}x plan'
LABEL_WEEK = 4  # W5: the two lines are well separated here, clear of the W6 callout

# The two series share one plot area by construction, so their bounding
# boxes overlap; the dot sits on the hero line it calls out, and the
# direct series labels sit over both lines by the same construction.
OVERLAP_OK = {('plan-line', 'hero-line'), ('hero-line', 'callout-dot'), ('plan-line', 'callout-dot'),
              ('plan-line', 'plan-label'), ('hero-line', 'plan-label'), ('hero-line', 'actual-label')}


def bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def draw_axes(cv, plot, baseline_y):
    """Baseline (zero, unlabelled -- the chart rests on it) plus one labelled
    gridline at the honest top of the scale."""
    cv.line(plot.x, baseline_y, plot.right, baseline_y, _kit.LINE, width=2)
    cv.line(plot.x, plot.y, plot.right, plot.y, _kit.LINE, width=1)
    _kit.text_marked(cv, 'axis-max', [f'{AXIS_MAX:g}x'], AXIS_F, plot.x - 54, plot.y - 9, _kit.MUTED,
                     align='right', width=44)
    for i, name in enumerate(WEEKS):
        x = plot.x + i / (len(WEEKS) - 1) * plot.w
        _kit.text_marked(cv, f'cat-{name}', [name], CAT_F, x - 14, baseline_y + 10, _kit.MUTED,
                         align='center', width=28)


def series_points(values, plot, baseline_y):
    return [(plot.x + i / (len(values) - 1) * plot.w, baseline_y - v / AXIS_MAX * plot.h)
            for i, v in enumerate(values)]


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Line chart with a callout', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)

    plot = Box(s.x + 76, s.y + 106, 330, 330)
    baseline_y = plot.bottom
    draw_axes(cv, plot, baseline_y)

    plan_pts = series_points(PLAN, plot, baseline_y)
    hero_pts = series_points(ACTUAL, plot, baseline_y)

    if n < AXES_HOLD:
        draw_frac = 0.0
    elif n < T_DRAW:
        draw_frac = vb.interpolate(n, [AXES_HOLD, T_DRAW], [0, 1], ease=vb.ease_out_quint)
    elif n < T_HOLD:
        draw_frac = 1.0
    elif n < T_RC:
        draw_frac = 1.0
    elif n < T_RL:
        draw_frac = vb.interpolate(n, [T_RC, T_RL], [1, 0], ease=vb.ease_in_expo)
    else:
        draw_frac = 0.0

    if draw_frac > 0.0:
        plan_rev, hero_rev = paths.reveal(plan_pts, draw_frac), paths.reveal(hero_pts, draw_frac)
        paths.draw(cv, plan_rev, _kit.MUTED, width=3)
        paths.draw(cv, hero_rev, _kit.ACCENT, width=4)
        cv.mark('plan-line', *bbox(plan_rev))
        cv.mark('hero-line', *bbox(hero_rev))

        # Direct labels on each line -- colour-blind safety: the two series
        # must not be told apart by grey-vs-accent hue alone.
        series_label_p = vb.clamp01((draw_frac - 0.75) / 0.25)
        if series_label_p > 0.01:
            px, py = plan_pts[LABEL_WEEK]
            hx, hy = hero_pts[LABEL_WEEK]
            _kit.text_marked(cv, 'plan-label', ['Plan'], CAT_F, px - 18, py - 28, _kit.MUTED, alpha=series_label_p)
            _kit.text_marked(cv, 'actual-label', ['Actual'], CAT_F, hx - 20, hy - 28, _kit.ACCENT, alpha=series_label_p)

    if n < T_DRAW:
        callout_p = 0.0
    elif n < T_CALLOUT:
        callout_p = vb.interpolate(n, [T_DRAW, T_CALLOUT], [0, 1], ease=vb.ease_out_back)
    elif n < T_HOLD:
        callout_p = 1.0
    elif n < T_RC:
        callout_p = vb.interpolate(n, [T_HOLD, T_RC], [1, 0], ease=vb.ease_in_expo)
    else:
        callout_p = 0.0

    if callout_p > 0.01:
        dot = hero_pts[-1]
        dot_r = 6 * min(1.0, callout_p * 2)
        cv.rect(dot[0] - dot_r, dot[1] - dot_r, 2 * dot_r, 2 * dot_r, _kit.INK, radius=dot_r)
        leader_end = (dot[0] + 40, dot[1] - 46)
        leader_p = vb.clamp01((callout_p - 0.3) / 0.7)
        if leader_p > 0:
            lx = dot[0] + (leader_end[0] - dot[0]) * leader_p
            ly = dot[1] + (leader_end[1] - dot[1]) * leader_p
            cv.line(dot[0], dot[1], lx, ly, _kit.INK, width=2)
            if leader_p >= 0.999:
                box = _kit.text_marked(cv, 'callout', [HERO_LABEL], CALLOUT_F, leader_end[0] + 8,
                                        leader_end[1] - 12, _kit.INK, alpha=callout_p)
                cv.mark('callout-dot', dot[0] - dot_r, dot[1] - dot_r, 2 * dot_r, 2 * dot_r)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((T_DRAW - 2, 'drawn'), (T_CALLOUT + 4, 'called out')))

if __name__ == '__main__':
    vb.main(__file__)
