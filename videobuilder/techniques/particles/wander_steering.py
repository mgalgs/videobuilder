"""Wander Steering: autonomous agents that cruise about with a will of their
own. Each step an agent projects a small circle a little way ahead of itself,
nudges a target point randomly around that circle, and steers towards it --
so its heading drifts in smooth, purposeful curves rather than jittering like
a random walk."""
import math
import random

from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique


def wander(steps, seed=0, start=(0.0, 0.0), heading=0.0, speed=6.0, distance=60.0, radius=30.0,
           jitter=0.35, force=0.6, bounds=None, margin=120.0):
    """Simulate one wandering agent for `steps` steps; returns one
    `(x, y, heading, target)` per step, `target` being the (x, y) on the
    wander circle it steered towards. Each step the target's angle on a circle
    of `radius`, `distance` ahead along the velocity, moves by up to
    `jitter` radians; the agent steers towards it by at most `force` px/step
    and cruises at `speed` px/step. `bounds` (x, y, w, h) keeps it in: past
    `margin` from an edge it is turned back in. The same `seed` gives the
    same path."""
    rnd = random.Random(f'wander:{seed}')
    x, y = start
    vx, vy = speed * math.cos(heading), speed * math.sin(heading)
    theta = rnd.uniform(-math.pi, math.pi)
    out = []
    for _ in range(steps):
        theta += rnd.uniform(-jitter, jitter)
        h = math.atan2(vy, vx)
        cx, cy = x + distance * math.cos(h), y + distance * math.sin(h)
        tx, ty = cx + radius * math.cos(h + theta), cy + radius * math.sin(h + theta)
        sx, sy = tx - x, ty - y
        if bounds:
            bx, by, bw, bh = bounds
            if x < bx + margin:
                sx += (bx + margin - x) * 0.5
            elif x > bx + bw - margin:
                sx -= (x - (bx + bw - margin)) * 0.5
            if y < by + margin:
                sy += (by + margin - y) * 0.5
            elif y > by + bh - margin:
                sy -= (y - (by + bh - margin)) * 0.5
        d = math.hypot(sx, sy) or 1.0
        f = min(force, d)
        vx, vy = vx + sx / d * f, vy + sy / d * f
        v = math.hypot(vx, vy) or 1.0
        vx, vy = vx / v * speed, vy / v * speed
        x, y = x + vx, y + vy
        out.append((x, y, math.atan2(vy, vx), (tx, ty)))
    return out


def draw_agent(cv, x, y, heading, size=22, color=demo.ACCENT, alpha=1.0):
    """A dart-shaped agent at (x, y) pointing along `heading` (radians)."""
    c = cv.ctx
    ch, sh = math.cos(heading), math.sin(heading)
    pts = ((size, 0), (-size * 0.7, size * 0.6), (-size * 0.35, 0), (-size * 0.7, -size * 0.6))
    c.new_path()
    for i, (px, py) in enumerate(pts):
        X, Y = x + px * ch - py * sh, y + px * sh + py * ch
        (c.move_to if i == 0 else c.line_to)(X, Y)
    c.close_path()
    c.set_source_rgba(*rgba(color, alpha))
    c.fill()


AGENTS = 7
TRAIL = 40
WARM = 30
BOUNDS = (0, 0, demo.W, demo.H)
_PATHS = {}


def _paths():
    if not _PATHS:
        steps = WARM + round(demo.SECONDS * demo.FPS)
        rnd = random.Random('wander-demo')
        for i in range(AGENTS):
            start = (rnd.uniform(300, demo.W - 300), rnd.uniform(220, demo.H - 220))
            _PATHS[i] = wander(steps, seed=i, start=start, heading=rnd.uniform(-math.pi, math.pi),
                               bounds=BOUNDS, margin=160)
    return _PATHS


def draw(n, cv):
    k = WARM + n
    for i, path in _paths().items():
        lead = i == 0
        color = demo.ACCENT if lead else demo.TEAL
        trail = path[max(0, k - TRAIL):k + 1]
        for j in range(1, len(trail)):
            a = j / len(trail)
            cv.line(trail[j - 1][0], trail[j - 1][1], trail[j][0], trail[j][1], color,
                    width=6 if lead else 4, alpha=0.55 * a)
        x, y, h, (tx, ty) = path[k]
        if lead:  # the steering rig: the wander circle ahead and the target on it
            cx, cy = x + 60 * math.cos(h), y + 60 * math.sin(h)
            cv.line(x, y, cx, cy, demo.MUTED, width=2)
            cv.arc(cx, cy, 30, 0, 2 * math.pi, demo.MUTED, width=2)
            cv.line(x, y, tx, ty, demo.INK, width=2, alpha=0.6)
            demo.dot(cv, tx, ty, r=7, color=demo.INK)
        draw_agent(cv, x, y, h, size=30 if lead else 22, color=color)


TECHNIQUE = Technique(
    id='wander-steering',
    name='Wander steering',
    family='particles',
    group='Swarms & agents',
    aliases=('wander behavior', 'steering wander', 'autonomous wander', 'Reynolds wander'),
    definition='Little agents roam the frame on their own, each steering towards a point that '
               'drifts randomly on a circle just ahead of it, so they swerve in smooth, lifelike curves.',
    phrasings=('make the little creatures swim around aimlessly but naturally',
               'arrows that meander around the screen like they are exploring',
               'agents that roam with gentle random turns instead of jittering'),
    related=('random-walk', 'arcs', 'path-emitter', 'path-follow-motion', 'wiggle-path',
             'rossler-attractor'),
    api=('videobuilder.techniques.particles.wander_steering.wander',
         'videobuilder.techniques.particles.wander_steering.draw_agent'),
    demo=lambda: demo.film(draw),
)
