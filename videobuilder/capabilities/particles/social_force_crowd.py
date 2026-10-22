"""Social Force Crowd: a crowd of walkers, each pulled toward its own goal and
pushed off its neighbours and the walls, so the flow forms lanes and jams up
at narrow openings on its own."""
import math
import random

from .. import _demo as demo
from ..schema import Technique


def _wall_push(x, y, wall):
    """(distance, nx, ny) from (x, y) to the segment `wall` = (x0, y0, x1, y1),
    with (nx, ny) the unit vector pointing away from the wall."""
    x0, y0, x1, y1 = wall
    dx, dy = x1 - x0, y1 - y0
    span = dx * dx + dy * dy
    t = 0.0 if span == 0 else max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / span))
    px, py = x - (x0 + t * dx), y - (y0 + t * dy)
    d = math.hypot(px, py) or 1e-6
    return d, px / d, py / d


def simulate_crowd(starts, routes, walls=(), frames=90, fps=30, substeps=4, speed=110.0, radius=7.0,
                   relax=0.35, push=900.0, reach=10.0, wall_push=1400.0, wall_reach=8.0, arrive=24.0,
                   wall_width=0.0, max_speed=None, seed=0):
    """Run a social-force crowd and return one list of (x, y) positions per
    frame, `frames` long.

    `starts`: each agent's starting (x, y). `routes`: each agent's goal, either
    one (x, y) or a sequence of waypoints walked in order (e.g. a doorway, then
    the far side); an agent moves on once within `arrive` px of a waypoint.
    `walls`: segments (x0, y0, x1, y1), `wall_width` px thick, nobody walks through. Each agent steers
    toward its waypoint at `speed` px/s, catching up over `relax` seconds; its
    neighbours push it off with a force of `push` that falls off over `reach`
    px beyond touching (agents are `radius` px), and walls likewise with
    `wall_push` / `wall_reach`. `max_speed` (default 1.6 x `speed`) caps a
    shove. Units are pixels and seconds; the same inputs (and `seed`, which
    jitters each agent's preferred speed by +-15%) give the same frames."""
    rnd = random.Random(f'crowd:{seed}')
    pos = [list(p) for p in starts]
    vel = [[0.0, 0.0] for _ in pos]
    plans = [[tuple(r)] if isinstance(r[0], (int, float)) else [tuple(w) for w in r] for r in routes]
    leg = [0] * len(pos)
    pace = [speed * rnd.uniform(0.85, 1.15) for _ in pos]
    vmax = max_speed or speed * 1.6
    dt = 1.0 / (fps * substeps)
    cutoff = 2 * radius + 6 * reach
    out = [[tuple(p) for p in pos]]
    for _ in range(1, frames):
        for _ in range(substeps):
            force = []
            for i, (x, y) in enumerate(pos):
                plan = plans[i]
                if leg[i] < len(plan) - 1 and math.hypot(plan[leg[i]][0] - x, plan[leg[i]][1] - y) < arrive:
                    leg[i] += 1
                gx, gy = plan[leg[i]]
                gd = math.hypot(gx - x, gy - y)
                want = pace[i] * min(1.0, gd / arrive) if leg[i] == len(plan) - 1 else pace[i]
                ex, ey = ((gx - x) / gd, (gy - y) / gd) if gd > 1e-6 else (0.0, 0.0)
                fx = (want * ex - vel[i][0]) / relax
                fy = (want * ey - vel[i][1]) / relax
                for j, (ox, oy) in enumerate(pos):
                    if j == i:
                        continue
                    dx, dy = x - ox, y - oy
                    if abs(dx) > cutoff or abs(dy) > cutoff:
                        continue
                    d = math.hypot(dx, dy) or 1e-6
                    f = push * math.exp((2 * radius - d) / reach)
                    fx += f * dx / d
                    fy += f * dy / d
                for wall in walls:
                    d, nx, ny = _wall_push(x, y, wall)
                    d -= wall_width / 2
                    if d < radius + 6 * wall_reach:
                        f = wall_push * math.exp((radius - d) / wall_reach)
                        fx += f * nx
                        fy += f * ny
                force.append((fx, fy))
            for i, (fx, fy) in enumerate(force):
                v = vel[i]
                v[0] += fx * dt
                v[1] += fy * dt
                s = math.hypot(v[0], v[1])
                if s > vmax:
                    v[0], v[1] = v[0] * vmax / s, v[1] * vmax / s
                pos[i][0] += v[0] * dt
                pos[i][1] += v[1] * dt
        out.append([tuple(p) for p in pos])
    return out


# The demo: two crowds swap rooms through one narrow doorway in a dividing wall.
TOP, BOTTOM, MID = 70, 470, demo.W / 2
GAP = 46                          # half the doorway's height
THICK = 14
WALLS = ((60, TOP, demo.W - 60, TOP), (60, BOTTOM, demo.W - 60, BOTTOM),
         (MID, TOP, MID, demo.H / 2 - GAP), (MID, demo.H / 2 + GAP, MID, BOTTOM))
GOLD, VIOLET = '#f2b632', '#8c8cf5'
PER_SIDE = 45
FRAMES = round(demo.SECONDS * demo.FPS)
_RUN = []


def _crowd():
    rnd = random.Random('social-force-demo')
    starts, routes, colors = [], [], []
    door = demo.H / 2
    for side, color in ((-1, GOLD), (1, VIOLET)):
        for _ in range(PER_SIDE):
            x = MID + side * rnd.uniform(70, 400)
            y = rnd.uniform(TOP + 24, BOTTOM - 24)
            starts.append((x, y))
            colors.append(color)
            routes.append(((MID + side * 30, door), (MID - side * 260, door + rnd.uniform(-120, 120))))
    frames = simulate_crowd(starts, routes, WALLS, frames=FRAMES + 8, fps=demo.FPS, speed=170, radius=7,
                            arrive=40, wall_width=THICK, seed=3)
    return frames[8:], colors   # a few frames in, so everyone is already walking


def draw(n, cv):
    if not _RUN:
        _RUN.append(_crowd())
    frames, colors = _RUN[0]
    for x0, y0, x1, y1 in WALLS:
        cv.rect(min(x0, x1) - THICK / 2, min(y0, y1) - THICK / 2, abs(x1 - x0) + THICK, abs(y1 - y0) + THICK,
                demo.LINE, radius=THICK / 2)
    for y in (demo.H / 2 - GAP, demo.H / 2 + GAP):
        cv.line(MID - 12, y, MID + 12, y, demo.INK, width=3)
    now, before = frames[min(n, len(frames) - 1)], frames[max(0, min(n, len(frames) - 1) - 6)]
    for (x, y), (bx, by), color in zip(now, before, colors):
        cv.line(bx, by, x, y, color, width=4, alpha=0.3)   # a short tail shows which way each walker heads
        demo.dot(cv, x, y, 7, color=color)


TECHNIQUE = Technique(
    id='social-force-crowd',
    name='Social force crowd',
    family='particles',
    group='Swarms & agents',
    aliases=('pedestrian flow', 'crowd simulation', 'social force model'),
    definition='Many little walkers each head for their own goal while shoving off one another and the walls, '
               'so streams sort into lanes and pile up at narrow gaps.',
    phrasings=('two crowds squeezing past each other through a narrow door',
               'simulate people walking and jostling so they form queues at a bottleneck',
               'a swarm of dots that push away from each other on their way somewhere'),
    related=('force-directed-network-settle', 'overlapping-action', 'dashed-line-march', 'n-body-gravity',
             'reaction-diffusion', 'random-walk'),
    api=('videobuilder.techniques.particles.social_force_crowd.simulate_crowd',),
    demo=lambda: demo.film(draw),
)
