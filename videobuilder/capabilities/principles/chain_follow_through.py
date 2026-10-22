"""Chain Follow-Through: a chain of links hangs from a point that moves; the
links lag behind it one after another, swing past when it stops, and settle."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def chain_follow_through(anchor, t, links=8, length=40.0, gravity=2000.0, drag=2.0, tip_mass=2.0,
                         iterations=8, hz=120):
    """The chain's joints at `t` seconds, anchor first: a list of `links + 1`
    (x, y) points. `anchor(t)` is where the top of the chain is at time `t`;
    the chain starts hanging straight down from `anchor(0)` and is stepped
    forward (Verlet, fixed `hz` steps, distance constraints) to `t`, so the
    same `t` always gives the same pose and frames can render in any order.

    `length` is one link's length in px; `gravity` in px/s^2; `drag` is the
    rate speed decays at (1/s); `tip_mass` weights the last joint
    (a bob) against the others, which weigh 1."""
    ax, ay = anchor(0.0)
    pts = [[ax, ay + i * length] for i in range(links + 1)]
    prev = [p[:] for p in pts]
    inv = [0.0] + [1.0] * (links - 1) + [1.0 / tip_mass]   # inverse masses; the anchor is pinned
    dt = 1.0 / hz
    keep = math.exp(-drag * dt)
    for k in range(1, round(t * hz) + 1):
        for i in range(1, links + 1):
            x, y = pts[i]
            px, py = prev[i]
            prev[i] = [x, y]
            pts[i] = [x + (x - px) * keep, y + (y - py) * keep + gravity * dt * dt]
        pts[0] = list(anchor(k * dt))
        for _ in range(iterations):
            for i in range(links):
                (x0, y0), (x1, y1) = pts[i], pts[i + 1]
                dx, dy = x1 - x0, y1 - y0
                d = math.hypot(dx, dy) or 1e-9
                w0, w1 = inv[i], inv[i + 1]
                s = (d - length) / d / (w0 + w1)
                pts[i] = [x0 + dx * s * w0, y0 + dy * s * w0]
                pts[i + 1] = [x1 - dx * s * w1, y1 - dy * s * w1]
    return [tuple(p) for p in pts]


RAIL_Y = 110
GLIDE = vb.bezier(0.45, 0, 0.55, 1)
STOPS = (demo.W / 2, demo.W / 2 - 150, demo.W / 2 + 150, demo.W / 2)
MOVES = ((0.15, 0.85), (1.05, 1.95), (2.05, 2.5))   # the anchor slides between STOPS, then holds


def anchor(t):
    for (s, e), x0, x1 in zip(MOVES, STOPS, STOPS[1:]):
        if t < e:
            return x0 + (x1 - x0) * GLIDE(vb.clamp01((t - s) / (e - s))), RAIL_Y
    return STOPS[-1], RAIL_Y


def draw(n, cv):
    pts = chain_follow_through(anchor, n / demo.FPS, links=8, length=38)
    cv.line(STOPS[1] - 80, RAIL_Y, STOPS[2] + 80, RAIL_Y, demo.LINE, width=3)
    for x in STOPS[:3]:
        cv.line(x, RAIL_Y - 8, x, RAIL_Y + 8, demo.LINE, width=3)
    c = cv.ctx
    c.save()
    c.set_line_join(1)  # round
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.set_source_rgba(*vb.canvas.rgba(demo.TEAL, 1.0))
    c.set_line_width(4)
    c.stroke()
    c.restore()
    for x, y in pts[1:-1]:
        demo.dot(cv, x, y, 7, demo.TEAL)
        demo.dot(cv, x, y, 3, demo.BG)
    bx, by = pts[-1]
    demo.dot(cv, bx, by, 38)
    cv.mark('bob', bx - 38, by - 38, 76, 76)
    ax, ay = pts[0]
    demo.dot(cv, ax, ay, 13, demo.INK)
    demo.dot(cv, ax, ay, 5, demo.BG)


CAPABILITY = Capability(
    id='chain-follow-through',
    name='Chain Follow-Through',
    family='principles',
    group='Physics',
    aliases=('verlet chain', 'multi-segment pendulum', 'rope physics'),
    definition='A string of joined links hangs from a point that moves, and each link trails the one above it, '
               'so the whole chain whips along late and keeps swinging after the point has stopped.',
    phrasings=('a weight on a chain that swings and lags behind when the top moves',
               'make it dangle like a rope and sway after it stops',
               'a hanging chain that follows through with a delay down its length'),
    related=('verlet-rope', 'follow-through', 'path-follow-motion', 'player-movement-trail',
             'force-directed-network-settle', 'cycle-diagram-rotation'),
    api=('videobuilder.capabilities.principles.chain_follow_through.chain_follow_through',),
    demo=lambda: demo.film(draw),
)
