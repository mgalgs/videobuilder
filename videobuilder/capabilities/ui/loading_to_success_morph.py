"""Loading to Success Morph: a spinning loader arc closes into a full ring,
the ring fills with the success colour, and a check mark draws itself on --
one shape carrying the state from "working" to "done"."""
import math

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Technique


def _mix(a, b, t):
    """Hex colours `a` and `b` blended at `t` (0 -> `a`, 1 -> `b`)."""
    ca, cb = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in (a, b))
    return '#' + ''.join(f'{round(x + (y - x) * vb.clamp01(t)):02x}' for x, y in zip(ca, cb))


def _arc_points(cx, cy, r, a0, a1, step=0.05):
    n = max(2, int(abs(a1 - a0) / step) + 1)
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / (n - 1)), cy + r * math.sin(a0 + (a1 - a0) * i / (n - 1)))
            for i in range(n)]


def loading_to_success(cv, cx, cy, r, spin, p, color='#9397a1', success='#4fc3b0', ink='#f4f4f2',
                       track='#2a2c33', width=None):
    """Draw the loader at (cx, cy), radius `r`. `spin` is the loader's turn
    count so far (pass time x speed, e.g. `t * 1.2`, so it keeps rotating);
    `p` runs 0 -> 1 across the morph and is 0 while still loading.

    While loading, a `color` arc chases round a faint `track` ring, its length
    breathing. Over the morph the arc grows to close the ring and turns
    `success` (to 0.35), the disc fills in with a small overshoot (0.3 -> 0.6),
    then an `ink` check mark strokes on (0.5 -> 1). Returns the Box it covers."""
    width = width or r * 0.16
    p = vb.clamp01(p)
    close = vb.ease_in_out_quart(vb.clamp01(p / 0.35))
    fill = vb.clamp01((p - 0.3) / 0.3)
    tick = vb.clamp01((p - 0.5) / 0.5)
    pop = vb.ease_out_back(fill) if fill > 0 else 0.0

    paths.draw(cv, _arc_points(cx, cy, r, 0, 2 * math.pi), track, width=width, closed=True, alpha=1 - close)
    head = 2 * math.pi * spin - math.pi / 2
    span = 2 * math.pi * (0.12 + 0.5 * math.sin(math.pi * spin * 0.7) ** 2)  # breathing length while it spins
    span += (2 * math.pi - span) * close
    ring = _mix(color, success, close)
    if pop > 0:
        demo.dot(cv, cx, cy, (r + width / 2) * pop, color=success)
    if close < 1:
        paths.draw(cv, _arc_points(cx, cy, r, head - span, head), ring, width=width)
    elif pop < 1:
        paths.draw(cv, _arc_points(cx, cy, r, 0, 2 * math.pi), ring, width=width, closed=True)
    if tick > 0:
        s = r * 0.62
        check = [(cx - s * 0.62, cy + s * 0.02), (cx - s * 0.18, cy + s * 0.46), (cx + s * 0.66, cy - s * 0.42)]
        paths.draw(cv, paths.reveal(check, vb.ease_out_expo(tick)), ink, width=width * 1.05)
    out = r + width / 2
    return vb.Box(cx - out, cy - out, 2 * out, 2 * out)


MORPH_AT, MORPH_LEN = 1.4, 1.0


def draw(n, cv):
    t = n / demo.FPS
    box = loading_to_success(cv, demo.W / 2, demo.H / 2, 150, spin=t * 1.1,
                             p=demo.phase(n, MORPH_AT, MORPH_AT + MORPH_LEN),
                             color=demo.ACCENT, success=demo.TEAL, ink=demo.BG, track=demo.LINE, width=24)
    cv.mark('loader', *box)


TECHNIQUE = Technique(
    id='loading-to-success-morph',
    name='Loading to success morph',
    family='ui',
    group='Feedback & status',
    aliases=('spinner to checkmark', 'loader to check', 'success state animation', 'done check morph'),
    definition='A spinning loading arc closes into a complete ring, fills in with a confirming colour, '
               'and a check mark draws itself inside it.',
    phrasings=('the spinner turns into a tick when it finishes',
               'show it loading, then morph into a green check for success',
               'a loading circle that completes and becomes a done checkmark'),
    related=('loading-state-morph', 'shape-morph-loader', 'spinner-ring', 'progress-ring',
             'indeterminate-dash-morph', 'bouncing-dots'),
    api=('videobuilder.techniques.ui.loading_to_success_morph.loading_to_success',),
    demo=lambda: demo.film(draw),
)
