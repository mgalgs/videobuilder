"""Velocity-Preserving Retarget: when a move's destination changes mid-flight,
the new move starts from where the object is *and how fast it is going*, so
it curves round to the new target instead of stopping dead or kinking."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _hermite(s, p0, v0, p1, length):
    """Cubic from `p0` leaving at velocity `v0` (units/s) to rest at `p1`,
    `length` seconds long, at progress `s` in [0, 1]. Returns (position, velocity)."""
    s2, s3 = s * s, s * s * s
    pos = (2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * length * v0 + (3 * s2 - 2 * s3) * p1
    vel = ((6 * s2 - 6 * s) * p0 + (3 * s2 - 4 * s + 1) * length * v0 + (6 * s - 6 * s2) * p1) / length
    return pos, vel


def velocity_preserving_retarget(t, start, moves, duration=1.0, preserve=True):
    """Position at `t` seconds of something that starts at rest at `start`
    and is sent to a series of targets: `moves` is `[(at_seconds, target), ...]`
    in time order, each move lasting `duration` seconds and ending at rest.

    A move issued while the previous one is still running begins with the
    position *and velocity* it had at that instant, so the path bends
    smoothly onto the new target. `preserve=False` restarts each move from
    rest instead (the naive retarget, for comparison). Positions may be
    numbers or equal-length tuples such as `(x, y)`; a tuple is returned for
    tuples. Pure: call it every frame with that frame's `t`."""
    scalar = not isinstance(start, (tuple, list))
    pos = [float(start)] if scalar else [float(c) for c in start]
    vel = [0.0] * len(pos)
    for i, (at, target) in enumerate(moves):
        if t < at:
            break
        goal = [float(target)] if scalar else [float(c) for c in target]
        v0 = vel if preserve else [0.0] * len(pos)
        end = moves[i + 1][0] if i + 1 < len(moves) else None
        stop = t if end is None or t < end else end
        s = vb.clamp01((stop - at) / duration)
        state = [_hermite(s, p, v, g, duration) for p, v, g in zip(pos, v0, goal)]
        pos = [p for p, _ in state]
        vel = [v if s < 1 else 0.0 for _, v in state]
    return pos[0] if scalar else tuple(pos)


START = (150, 400)
MOVES = ((0.3, (800, 120)), (1.0, (800, 430)))  # heading up-right, then the target drops mid-flight
LENGTH = 1.5


def _target(cv, x, y, alpha, live):
    r = 26
    cv.arc(x, y, r, 0, 6.2832, demo.INK if live else demo.MUTED, width=3, alpha=alpha)
    cv.line(x - 8, y, x + 8, y, demo.INK if live else demo.MUTED, width=2, alpha=alpha)
    cv.line(x, y - 8, x, y + 8, demo.INK if live else demo.MUTED, width=2, alpha=alpha)


def _trail(cv, t, preserve, color, width, alpha):
    steps = max(2, int(t * demo.FPS * 2))
    pts = [velocity_preserving_retarget(t * k / steps, START, MOVES, LENGTH, preserve) for k in range(steps + 1)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(x0, y0, x1, y1, color, width=width, alpha=alpha)


def draw(n, cv):
    t = n / demo.FPS
    (a_at, a), (b_at, b) = MOVES
    switched = t >= b_at
    _target(cv, *a, alpha=0.35 if switched else 1.0, live=not switched)
    if switched:
        flash = 1 - demo.phase(n, b_at, b_at + 0.4)
        _target(cv, *b, alpha=1.0, live=True)
        cv.arc(*b, 26 + 30 * (1 - flash), 0, 6.2832, demo.INK, width=2, alpha=0.6 * flash)
    # the naive retarget, faint: it stops and turns a sharp corner
    _trail(cv, t, False, demo.MUTED, 2, 0.45)
    gx, gy = velocity_preserving_retarget(t, START, MOVES, LENGTH, preserve=False)
    demo.dot(cv, gx, gy, r=16, color=demo.MUTED, alpha=0.5)
    # the velocity-preserving one: the same targets, a smooth bend
    _trail(cv, t, True, demo.ACCENT, 4, 0.8)
    x, y = velocity_preserving_retarget(t, START, MOVES, LENGTH)
    demo.dot(cv, x, y, r=22)
    cv.mark('dot', x - 22, y - 22, 44, 44)
    f = demo.mono(18)
    vb.text.draw(cv, ['keeps its velocity'], f, 40, 30, demo.ACCENT)
    vb.text.draw(cv, ['restarts from rest'], f, 40, 58, demo.MUTED)


CAPABILITY = Capability(
    id='velocity-preserving-retarget',
    name='Velocity-Preserving Retarget',
    family='principles',
    group='Timing & spacing',
    aliases=('interruptible animation', 'velocity handoff', 'smooth retarget', 'additive retargeting'),
    definition='When something already in motion is given a new destination, it carries its current '
               'speed and direction into the new move and curves round to it, with no stop or sharp turn.',
    phrasings=('change where it is going halfway without it jerking',
               'if the target moves, let it swing over smoothly instead of snapping',
               'redirect the motion mid-flight and keep its momentum'),
    related=('retiming', 'momentum-fling', 'inertia', 'speed-ramp', 'reverse-playback', 'cut-on-action'),
    api=('videobuilder.capabilities.principles.velocity_preserving_retarget.velocity_preserving_retarget',),
    demo=lambda: demo.film(draw),
)
