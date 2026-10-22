"""Player movement trail: a tracked player runs across the pitch with a line
behind them showing where they were over the last second or so, thick and
bright at their feet and thinning to nothing at its tail."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def trail_points(path, t, window=1.5, step=1 / 60):
    """The tracked object's recent positions at time `t` (seconds), oldest
    first, as `(x, y, age)` with `age` 0 (now) -> 1 (`window` seconds ago).

    `path(s)` is the object's (x, y) at time `s`, or None while it is not
    tracked; the trail starts after the last untracked moment, so it never
    reaches back past where tracking began. Sampled every `step` seconds and
    stateless: any frame renders alone."""
    out = []
    k = 0
    while k * step <= window:
        s = t - k * step
        at = path(s)
        if at is None:
            break
        out.append((at[0], at[1], k * step / window))
        k += 1
    if out and out[-1][2] < 1:
        tail = path(t - window)
        if tail is not None:
            out.append((tail[0], tail[1], 1.0))
    return out[::-1]


def draw_movement_trail(cv, path, t, color, width=7, window=1.5, fade=1.6, step=1 / 60):
    """Draw the trail of `path` at time `t`: the last `window` seconds of its
    track as a line `width` px wide at the head, narrowing and fading
    (`fade`: the curve of the falloff, higher drops sooner) to nothing at the
    tail. Draws no marker on the object itself, so a film puts its own
    player chip on top. Returns the trail points (see `trail_points`)."""
    pts = trail_points(path, t, window, step)
    for (x0, y0, a0), (x1, y1, a1) in zip(pts, pts[1:]):
        keep = 1 - (a0 + a1) / 2
        if keep > 0:
            cv.line(x0, y0, x1, y1, color, width=max(width * keep ** 0.6, 0.5), alpha=keep ** fade)
    return pts


# The demo: a striker and a defender on a top-down pitch, each with a
# tracking chip and a trail of their own last 1.2 seconds.
PITCH = '#1d3a2c'
STRIPE = '#21412f'
CHALK = '#cfe3d6'


def _pitch(cv):
    cv.fill(PITCH)
    for i in range(0, 12, 2):
        cv.rect(i * demo.W / 12, 0, demo.W / 12, demo.H, STRIPE)
    m = 40
    cv.outline(m, m, demo.W - 2 * m, demo.H - 2 * m, CHALK, width=2, alpha=0.5)
    cv.line(demo.W / 2, m, demo.W / 2, demo.H - m, CHALK, width=2, alpha=0.5)
    cv.arc(demo.W / 2, demo.H / 2, 70, 0, 2 * math.pi, CHALK, width=2, alpha=0.5)
    box_h = 240
    cv.outline(demo.W - m - 130, (demo.H - box_h) / 2, 130, box_h, CHALK, width=2, alpha=0.5)
    cv.arc(demo.W - m - 130, demo.H / 2, 60, math.pi / 2 + 0.93, 3 * math.pi / 2 - 0.93, CHALK, width=2, alpha=0.5)


def _curve(points):
    """A smooth (Catmull-Rom) run through `points`, as `u` 0 -> 1 -> (x, y)."""
    n = len(points) - 1

    def at(u):
        u = vb.clamp01(u) * n
        i = min(int(u), n - 1)
        f = u - i
        p0, p1, p2, p3 = (points[max(i - 1, 0)], points[i], points[i + 1], points[min(i + 2, n)])
        return tuple(0.5 * (2 * b + (-a + c) * f + (2 * a - 5 * b + 4 * c - d) * f * f
                            + (-a + 3 * b - 3 * c + d) * f ** 3) for a, b, c, d in zip(p0, p1, p2, p3))
    return at


_STRIKER = _curve([(150, 420), (300, 360), (420, 250), (560, 330), (700, 250), (820, 280)])
_DEFENDER = _curve([(640, 110), (600, 180), (620, 260), (700, 300), (760, 290)])


def striker(s):
    return _STRIKER(vb.clamp01((s - 0.2) / 2.6))


def defender(s):
    p = vb.clamp01((s - 0.8) / 2.0)
    return _DEFENDER(p * p * (3 - 2 * p))


def _chip(cv, x, y, color, label):
    demo.dot(cv, x, y, 22, color=color, alpha=0.25)
    demo.dot(cv, x, y, 15, color=demo.INK)
    demo.dot(cv, x, y, 12, color=color)
    demo.word(cv, label, x, y, size=13, weight=800, color=demo.INK)
    cv.arc(x, y, 22, 0, 2 * math.pi, color, width=2)


def draw(n, cv):
    t = n / demo.FPS
    _pitch(cv)
    draw_movement_trail(cv, defender, t, demo.TEAL, width=6, window=1.2)
    draw_movement_trail(cv, striker, t, '#ffcc33', width=7, window=1.2)
    for path, color, label in ((defender, demo.TEAL, '4'), (striker, '#ffcc33', '9')):
        x, y = path(t)
        _chip(cv, x, y, color, label)
        cv.mark(f'player {label}', x - 22, y - 22, 44, 44)


CAPABILITY = Capability(
    id='player-movement-trail',
    name='Player movement trail',
    family='broadcast',
    group='Sports graphics',
    aliases=('motion trail overlay', 'tracking path', 'player tracking trail'),
    definition='A tracked player is followed by a line marking only their last moments of movement, '
               'bright at their position and thinning away to nothing behind them.',
    phrasings=('show the run each player just made as a line behind them',
               'draw a fading tail behind the player so we can see where they came from',
               'tracking lines that follow the players around the pitch'),
    related=('cursor-particle-trail', 'path-emitter', 'follow-cam', 'map-route-draw', 'per-line-fade-in',
             'tracking-shot'),
    api=('videobuilder.capabilities.broadcast.player_movement_trail.draw_movement_trail',
         'videobuilder.capabilities.broadcast.player_movement_trail.trail_points'),
    demo=lambda: demo.film(draw),
)
