"""Spinner ring: the busy indicator -- a round-capped arc chasing itself
around a faint circular track, its head and tail taking turns to lead so the
arc stretches and shrinks while the whole ring keeps turning."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def spinner_arc(t, period=1.5, turns=1.0, shortest=0.06, longest=0.72):
    """The arc a spinner shows at `t` seconds, as `(start, end)` angles in
    radians (clockwise from 12 o'clock, `end > start`). Each `period` the head
    runs ahead until the arc spans `longest` of a turn, then the tail catches
    up to `shortest`; meanwhile the whole thing turns `turns` times per
    period. Loops seamlessly, so a film can call it for as long as it likes."""
    k, u = divmod(t / period, 1.0)
    grow = longest - shortest
    head = grow * vb.ease_in_out_quart(vb.clamp01(u * 2))
    tail = grow * vb.ease_in_out_quart(vb.clamp01(u * 2 - 1))
    base = k * grow + (t / period) * turns
    start = (base + tail) * 2 * math.pi - math.pi / 2
    end = (base + head + shortest) * 2 * math.pi - math.pi / 2
    return start, end


def spinner_ring(cv, cx, cy, r, t, color=demo.ACCENT, track=demo.LINE, width=None, alpha=1.0, **kw):
    """Draw a spinner ring of radius `r` centred at (cx, cy) as it looks at
    `t` seconds: a faint full `track` circle (None for none) under a
    round-capped `color` arc from `spinner_arc(t, **kw)`. `width` defaults
    to a sixth of `r`. Returns the ring's Box."""
    width = width or r / 6
    if track is not None:
        cv.arc(cx, cy, r, 0, 2 * math.pi, track, width=width, alpha=alpha * 0.6)
    a0, a1 = spinner_arc(t, **kw)
    c = cv.ctx
    c.save()
    c.new_path()
    c.arc(cx, cy, r, a0, a1)
    c.set_source_rgba(*vb.rgba(color, alpha))
    c.set_line_width(width)
    c.set_line_cap(1)  # round
    c.stroke()
    c.restore()
    return vb.Box(cx - r - width / 2, cy - r - width / 2, 2 * r + width, 2 * r + width)


def draw(n, cv):
    t = n / demo.FPS
    fade = demo.phase(n, 0.0, 0.3)
    box = spinner_ring(cv, demo.W / 2, demo.H / 2 - 40, 120, t, alpha=fade)
    cv.mark('spinner', *box)
    demo.word(cv, 'Loading', demo.W / 2, demo.H / 2 + 170, size=44, color=demo.MUTED, weight=600, alpha=fade)


CAPABILITY = Capability(
    id='spinner-ring',
    name='Spinner ring',
    family='ui',
    group='Loaders',
    aliases=('loading spinner', 'circular progress indicator', 'activity indicator', 'throbber'),
    definition='A busy indicator in which a rounded arc races around a faint circle, '
               'stretching out and shrinking back as it goes.',
    phrasings=('a spinning circle that shows something is loading',
               'the round loading wheel while we wait',
               'a busy spinner like an app shows before content appears'),
    related=('rotating-rings', 'rotating-circular-text', 'radial-stagger', 'cycle-diagram-rotation', 'spin',
             'turntable-rotation'),
    api=('videobuilder.capabilities.ui.spinner_ring.spinner_ring',
         'videobuilder.capabilities.ui.spinner_ring.spinner_arc'),
    demo=lambda: demo.film(draw),
)
