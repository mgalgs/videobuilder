"""Hold: motion stops on a pose and stays there for a beat before the next
move, so the eye has time to read where the thing has landed."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _mix(a, b, p):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * p for x, y in zip(a, b))
    return a + (b - a) * p


def hold(t, stops, ease=vb.ease_in_out_quart, drift=0.0):
    """The value at time `t` along `stops`, a list of `(arrive, leave, value)`
    sorted by time: each value is held from `arrive` to `leave`, and between
    one stop's `leave` and the next's `arrive` it moves there on `ease`.
    `value` is a number or a tuple of numbers. `drift` (0..1) makes it a
    moving hold: through each hold it creeps that fraction of the way toward
    the next stop, so a long hold never goes dead. Before the first stop,
    its value; after the last, the last."""
    if not stops:
        raise ValueError('hold needs at least one stop')
    for i, (arrive, leave, value) in enumerate(stops):
        nxt = stops[i + 1] if i + 1 < len(stops) else None
        if t < arrive:
            return value
        if t <= leave or nxt is None:
            if not drift or nxt is None or leave <= arrive:
                return value
            return _mix(value, nxt[2], drift * vb.clamp01((t - arrive) / (leave - arrive)))
        if t < nxt[0]:
            start = _mix(value, nxt[2], drift) if drift else value
            return _mix(start, nxt[2], ease(vb.clamp01((t - leave) / (nxt[0] - leave))))
    return stops[-1][2]


def holding(t, stops):
    """Whether `t` falls inside one of `stops`' holds."""
    return any(arrive <= t <= leave for arrive, leave, _ in stops)


GAP = demo.W * 0.3
STATIONS = (demo.W / 2 - GAP, demo.W / 2, demo.W / 2 + GAP)
STOPS = ((0.0, 0.35, STATIONS[0]), (0.75, 1.75, STATIONS[1]), (2.15, 3.0, STATIONS[2]))
CW, CH = demo.W * 0.2, demo.W * 0.125
CY = demo.H * 0.36


def draw(n, cv):
    t = n / demo.FPS
    for x in STATIONS:  # where each hold lands
        cv.outline(x - CW / 2, CY - CH / 2, CW, CH, demo.MUTED, width=2, radius=18, alpha=0.4)
    on = holding(t, STOPS)
    demo.card(cv, hold(t, STOPS), CY, w=CW, h=CH, color=demo.ACCENT)

    # the timeline: moves as thin rails, holds as thick bars, with a playhead
    y, x0, x1 = demo.H * 0.8, demo.W * 0.12, demo.W * 0.88
    sx = lambda s: x0 + (x1 - x0) * s / demo.SECONDS  # noqa: E731
    cv.line(x0, y, x1, y, demo.LINE, width=3)
    for arrive, leave, _ in STOPS:
        cv.rect(sx(arrive), y - 12, sx(leave) - sx(arrive), 24, demo.TEAL, radius=12,
                alpha=1.0 if arrive <= t <= leave else 0.4)
    cv.line(sx(t), y - 30, sx(t), y + 30, demo.INK, width=4)
    demo.word(cv, 'HOLD' if on else 'move', demo.W / 2, demo.H * 0.64, size=44,
              color=demo.TEAL if on else demo.MUTED, weight=800 if on else 500)


TECHNIQUE = Technique(
    id='hold',
    name='Hold',
    family='principles',
    group='Principle sub-techniques',
    aliases=('hold frame', 'held pose', 'moving hold', 'pose hold', 'beat'),
    definition='A move comes to a full stop and the subject stays put on that pose for a beat, '
               'letting it register before the next move begins.',
    phrasings=('let it sit still for a moment after it lands',
               'pause on that pose for a beat before it moves again',
               'stop, hold, then carry on to the next spot'),
    related=('freeze-frame', 'cut-on-action', 'interruptible-motion', 'seamless-loop', 'handheld-shake',
             'play-pause-morph'),
    api=('videobuilder.techniques.principles.hold.hold',
         'videobuilder.techniques.principles.hold.holding'),
    demo=lambda: demo.film(draw),
)
