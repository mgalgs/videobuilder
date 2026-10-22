"""Verlet Rope: a rope made of many short fixed-length segments, pinned at one
end and let go; it falls, swings and drapes itself over whatever is in its way."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def verlet_rope(start, t, pins=(0,), gravity=1800.0, drag=1.2, iterations=12, hz=120, circles=()):
    """The rope's points at `t` seconds: a list of (x, y), one per entry of
    `start`. `start` is the rope's rest pose at t = 0 (consecutive points
    are joined by segments that keep their starting lengths); the indices in
    `pins` stay where they began. Each step moves every free point by its
    last velocity (position Verlet) plus `gravity` (px/s^2), then relaxes
    the segment lengths `iterations` times and pushes points out of each
    `(cx, cy, r)` in `circles`, so the rope swings and wraps around them.

    The rope is stepped from rest at fixed `hz`, so the same `t` always
    gives the same pose and frames can render in any order. `drag` is the
    rate speed decays at (1/s)."""
    pts = [list(p) for p in start]
    prev = [p[:] for p in pts]
    rest = [math.dist(a, b) for a, b in zip(start, start[1:])]
    pinned = {i % len(pts) for i in pins}
    free = [i for i in range(len(pts)) if i not in pinned]
    dt = 1.0 / hz
    keep = math.exp(-drag * dt)
    g = gravity * dt * dt
    for _ in range(round(t * hz)):
        for i in free:
            x, y = pts[i]
            px, py = prev[i]
            prev[i] = [x, y]
            pts[i] = [x + (x - px) * keep, y + (y - py) * keep + g]
        for _ in range(iterations):
            for i, length in enumerate(rest):
                (x0, y0), (x1, y1) = pts[i], pts[i + 1]
                dx, dy = x1 - x0, y1 - y0
                d = math.hypot(dx, dy) or 1e-9
                w0, w1 = (i not in pinned), (i + 1 not in pinned)
                if not w0 + w1:
                    continue
                s = (d - length) / d / (w0 + w1)
                pts[i] = [x0 + dx * s * w0, y0 + dy * s * w0]
                pts[i + 1] = [x1 - dx * s * w1, y1 - dy * s * w1]
            for cx, cy, r in circles:
                for i in free:
                    x, y = pts[i]
                    d = math.hypot(x - cx, y - cy)
                    if d < r:
                        k = r / (d or 1e-9)
                        pts[i] = [cx + (x - cx) * k, cy + (y - cy) * k]
    return [tuple(p) for p in pts]


PIN = (demo.W * 0.32, 150)
SEGMENTS, SPAN = 26, 480
START = [(PIN[0] + SPAN * i / SEGMENTS, PIN[1]) for i in range(SEGMENTS + 1)]
PEG = (demo.W * 0.32 + 190, 400, 60)
_poses = {}


def pose(n):
    if n not in _poses:
        _poses[n] = verlet_rope(START, n / demo.FPS, circles=(PEG,))
    return _poses[n]


def draw(n, cv):
    cx, cy, r = PEG
    demo.dot(cv, cx, cy, r, demo.LINE)
    demo.dot(cv, cx, cy, 6, demo.MUTED)
    pts = pose(n)
    c = cv.ctx
    c.save()
    c.set_line_join(1)  # round
    c.set_line_cap(1)
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.set_source_rgba(*vb.canvas.rgba(demo.ACCENT, 1.0))
    c.set_line_width(7)
    c.stroke()
    c.restore()
    for x, y in pts[1:-1:2]:
        demo.dot(cv, x, y, 2.5, demo.INK, alpha=0.7)
    ex, ey = pts[-1]
    demo.dot(cv, ex, ey, 16)
    cv.mark('rope end', ex - 16, ey - 16, 32, 32)
    demo.dot(cv, *PIN, 13, demo.INK)
    demo.dot(cv, *PIN, 5, demo.BG)


CAPABILITY = Capability(
    id='verlet-rope',
    name='Verlet rope',
    family='particles',
    group='Soft bodies & cloth',
    aliases=('rope simulation', 'chain physics', 'verlet chain'),
    definition='A line built from many short links that never stretch falls from where it is pinned, '
               'swings loosely under gravity and drapes itself over anything it hits.',
    phrasings=('a rope pinned at one end that drops and swings realistically',
               'let a string fall and hang over a peg like real rope',
               'a dangling cable that sways and settles with physics'),
    related=('chain-follow-through', 'newton-s-cradle', 'line-weave', 'bezier-handle-bend',
             'ping-pong-loop', 'seamless-loop'),
    api=('videobuilder.capabilities.particles.verlet_rope.verlet_rope',),
    demo=lambda: demo.film(draw),
)
