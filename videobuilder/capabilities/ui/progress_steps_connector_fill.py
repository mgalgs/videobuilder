"""Progress Steps Connector Fill: a row of step markers joined by grey tracks;
a coloured fill runs along each track in turn, and every marker it reaches
fills in and turns into a tick."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def step_states(count, p):
    """Where a stepper of `count` steps stands at progress `p` (0 -> 1, the
    first step done at 0, the last at 1): `(connectors, nodes)`, each a list
    of 0 -> 1 amounts. `connectors[i]` is how far the track from step `i` to
    `i + 1` has filled; `nodes[i]` is how far step `i` has filled in, rising
    over the last tenth of the track leading into it."""
    at = vb.clamp01(p) * (count - 1)
    connectors = [vb.clamp01(at - i) for i in range(count - 1)]
    nodes = [1.0] + [vb.clamp01((at - i + 0.1) / 0.1) for i in range(1, count)]
    return connectors, nodes


def _tick(cv, cx, cy, r, color, t):
    """A check mark inside a circle of radius `r`, drawn on over `t` 0 -> 1."""
    pts = [(cx - r * 0.42, cy + r * 0.02), (cx - r * 0.12, cy + r * 0.32), (cx + r * 0.45, cy - r * 0.3)]
    lens = [math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])]
    left = t * sum(lens)
    width = r * 0.2
    for (x0, y0), (x1, y1), seg in zip(pts, pts[1:], lens):
        k = min(1.0, left / seg) if seg else 1.0
        if k <= 0:
            break
        cv.line(x0, y0, x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, color, width=width)
        demo.dot(cv, x0, y0, width / 2, color)
        demo.dot(cv, x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, width / 2, color)
        left -= seg


def draw_progress_steps(cv, x0, x1, y, p, labels, r=30, track=8, done=demo.ACCENT, todo=demo.LINE,
                        ink=demo.INK, muted=demo.MUTED, font=None, label_font=None):
    """Draw a horizontal stepper from x0 to x1 (marker centres) on line `y` at
    progress `p` (see `step_states`). Each marker is a circle of radius `r`
    numbered 1..n; a reached marker fills with `done` and shows a tick, the
    one just reached gets a soft halo. `labels` (one per step, may be empty
    strings) sit under the markers. Returns the list of marker centres.

    In a film, drive `p` with whatever pacing suits: a plain ramp, or eased
    hops with holds on each step (as the demo does)."""
    count = len(labels)
    connectors, nodes = step_states(count, p)
    xs = [x0 + (x1 - x0) * i / (count - 1) for i in range(count)]
    font = font or demo.font(round(r * 0.9), 800)
    label_font = label_font or demo.font(round(r * 0.7), 600)
    for i, f in enumerate(connectors):
        a, b = xs[i] + r, xs[i + 1] - r
        cv.rect(a, y - track / 2, b - a, track, todo, radius=track / 2)
        if f > 0:
            cv.rect(a, y - track / 2, (b - a) * f, track, done, radius=track / 2)
    current = max(i for i, f in enumerate(nodes) if f >= 1)
    for i, (cx, f) in enumerate(zip(xs, nodes)):
        if i == current:
            demo.dot(cv, cx, y, r * 1.45, done, alpha=0.18)
        demo.dot(cv, cx, y, r, todo)
        cv.arc(cx, y, r - 1.5, 0, 2 * math.pi, muted, width=3, alpha=0.6 * (1 - f))
        if f > 0:
            demo.dot(cv, cx, y, r * vb.ease_out_back(f), done)
        if f < 1:
            num = str(i + 1)
            w, h = vb.text.block_size([num], font)
            vb.text.draw(cv, [num], font, cx - w / 2, y - h / 2, muted, alpha=1 - f)
        else:
            _tick(cv, cx, y, r, ink, 1.0)
        if labels[i]:
            w, h = vb.text.block_size([labels[i]], label_font)
            vb.text.draw(cv, [labels[i]], label_font, cx - w / 2, y + r * 1.9, ink if f >= 1 else muted)
    return xs


LABELS = ('Cart', 'Shipping', 'Payment', 'Confirm')


def demo_progress(t, count=len(LABELS), start=0.4, hop=0.45, hold=0.2):
    """The demo's pacing: from `start` s, an eased hop of `hop` s to each next
    step, then a `hold` s pause on it."""
    k = (t - start) / (hop + hold)
    if k <= 0:
        return 0.0
    i = min(int(k), count - 1)
    within = vb.clamp01((k - i) * (hop + hold) / hop) if i < count - 1 else 0.0
    return min(1.0, (i + vb.ease_in_out_quart(within)) / (count - 1))


def draw(n, cv):
    p = demo_progress(n / demo.FPS)
    xs = draw_progress_steps(cv, 170, demo.W - 170, demo.H / 2 - 20, p, LABELS)
    cv.mark('stepper', xs[0] - 30, demo.H / 2 - 50, xs[-1] - xs[0] + 60, 60)


TECHNIQUE = Technique(
    id='progress-steps-connector-fill',
    name='Progress steps connector fill',
    family='ui',
    group='Feedback & status',
    aliases=('stepper', 'step indicator', 'wizard progress', 'multi-step progress bar'),
    definition='A row of numbered step markers joined by empty tracks, where colour flows along each '
               'track in turn and fills in every marker it reaches as that step is completed.',
    phrasings=('a checkout progress bar where the line fills up to each step',
               'step 1, 2, 3 circles that light up as the bar between them fills',
               'show the user moving through the stages of a form, ticking each one off'),
    related=('step-by-step-process-reveal', 'progress-ring', 'flowchart-build', 'percentage-fill-bar',
             'steps-easing', 'icon-line-to-fill'),
    api=('videobuilder.techniques.ui.progress_steps_connector_fill.draw_progress_steps',
         'videobuilder.techniques.ui.progress_steps_connector_fill.step_states'),
    demo=lambda: demo.film(draw),
)
