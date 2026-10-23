"""Rigid body pile: boxes drop in one after another, knock into the floor and
each other, tip over and come to rest as a heap that leans and settles."""
import math
import random
from functools import lru_cache

from .. import _demo as demo
from ..schema import Capability


def _axes(b):
    c, s = math.cos(b['a']), math.sin(b['a'])
    return (c, s), (-s, c)


def _corners(b):
    (ux, uy), (vx, vy) = _axes(b)
    return [(b['x'] + px * ux + py * vx, b['y'] + px * uy + py * vy)
            for px, py in ((-b['hw'], -b['hh']), (b['hw'], -b['hh']), (b['hw'], b['hh']), (-b['hw'], b['hh']))]


def _samples(b):
    """The corners and edge midpoints of `b`: the points tested against
    other boxes, so edge-on-edge hits are caught as well as corner hits."""
    cs = _corners(b)
    return cs + [((p[0] + q[0]) / 2, (p[1] + q[1]) / 2) for p, q in zip(cs, cs[1:] + cs[:1])]


def _inside(p, b):
    """If point `p` is inside box `b`: (depth, nx, ny), the shortest way out of
    `b` (normal pointing away from `b`). Otherwise None."""
    (ux, uy), (vx, vy) = _axes(b)
    dx, dy = p[0] - b['x'], p[1] - b['y']
    lx, ly = dx * ux + dy * uy, dx * vx + dy * vy
    ox, oy = b['hw'] - abs(lx), b['hh'] - abs(ly)
    if ox <= 0 or oy <= 0:
        return None
    if ox < oy:
        s = 1 if lx >= 0 else -1
        return ox, s * ux, s * uy
    s = 1 if ly >= 0 else -1
    return oy, s * vx, s * vy


def _contacts(bodies, floor, left, right):
    """Every contact this step: (a, b, px, py, nx, ny, depth), the normal
    pointing from `b` to `a`; `b` is None for the floor and walls."""
    out = []
    for a in bodies:
        for p in _corners(a):
            if p[1] > floor:
                out.append((a, None, p[0], p[1], 0.0, -1.0, p[1] - floor))
            if p[0] < left:
                out.append((a, None, p[0], p[1], 1.0, 0.0, left - p[0]))
            if p[0] > right:
                out.append((a, None, p[0], p[1], -1.0, 0.0, p[0] - right))
    for i, a in enumerate(bodies):
        for o in bodies[i + 1:]:
            if math.hypot(a['x'] - o['x'], a['y'] - o['y']) > a['r'] + o['r']:
                continue
            for mover, other in ((a, o), (o, a)):
                for p in _samples(mover):
                    hit = _inside(p, other)
                    if hit:
                        depth, nx, ny = hit
                        out.append((mover, other, p[0], p[1], nx, ny, depth))
    return out


def _velocity_at(b, px, py):
    if b is None:
        return 0.0, 0.0
    return b['vx'] - b['w'] * (py - b['y']), b['vy'] + b['w'] * (px - b['x'])


def _push(b, ix, iy, px, py):
    if b is None:
        return
    b['vx'] += ix * b['im']
    b['vy'] += iy * b['im']
    b['w'] += ((px - b['x']) * iy - (py - b['y']) * ix) * b['ii']


def _mass_along(b, px, py, nx, ny):
    if b is None:
        return 0.0
    rn = (px - b['x']) * ny - (py - b['y']) * nx
    return b['im'] + rn * rn * b['ii']


def _resolve(c, bounce, friction):
    a, b, px, py, nx, ny, _ = c
    ax, ay = _velocity_at(a, px, py)
    bx, by = _velocity_at(b, px, py)
    rx, ry = ax - bx, ay - by
    vn = rx * nx + ry * ny
    if vn >= 0:
        return
    e = bounce if vn < -120 else 0.0  # slow contacts don't bounce, so stacks can rest
    j = -(1 + e) * vn / (_mass_along(a, px, py, nx, ny) + _mass_along(b, px, py, nx, ny))
    tx, ty = -ny, nx
    vt = rx * tx + ry * ty
    kt = _mass_along(a, px, py, tx, ty) + _mass_along(b, px, py, tx, ty)
    jt = max(-friction * j, min(friction * j, -vt / kt))
    ix, iy = j * nx + jt * tx, j * ny + jt * ty
    _push(a, ix, iy, px, py)
    _push(b, -ix, -iy, px, py)


@lru_cache(maxsize=16)
def simulate_pile(sizes, drops, frames, fps=30, floor=980.0, left=0.0, right=1920.0, spawn_y=-80.0,
                  gravity=2400.0, bounce=0.2, friction=0.7, seed=0, substeps=10, iterations=4):
    """Rigid-body poses for boxes dropped one by one onto a floor between two walls.

    `sizes`: one `(half_width, half_height)` per box; `drops`: one
    `(start_seconds, x)` per box, released from `spawn_y` with a small random
    tilt, spin and sideways drift (from `seed`). Boxes collide as boxes with
    the floor, the walls and each other, with friction, so they stack, lean,
    tip off one another and settle into a heap. A box whose drop spot is
    still occupied waits until it clears. Returns, per frame, a tuple of
    `(x, y, angle)` per box (`None` before it is released). The same
    arguments give the same result, so it is computed once and cached."""
    rnd = random.Random(seed)
    bodies = []
    for (hw, hh), (t0, x) in zip(sizes, drops):
        m = 4 * hw * hh
        bodies.append(dict(x=x, y=spawn_y - hh, vx=rnd.uniform(-80, 80), vy=rnd.uniform(0, 200),
                           a=rnd.uniform(-0.6, 0.6), w=rnd.uniform(-2.5, 2.5), hw=hw, hh=hh,
                           im=1 / m, ii=3 / (m * (hw * hw + hh * hh)), r=math.hypot(hw, hh) * 2, t0=t0, live=False))
    dt = 1 / fps / substeps
    out = []
    for n in range(frames):
        for k in range(substeps):
            t = (n * substeps + k) * dt
            for b in bodies:  # released on time, or as soon as its drop spot is clear of earlier boxes
                if not b['live'] and t >= b['t0'] and all(
                        math.hypot(o['x'] - b['x'], o['y'] - b['y']) > (o['r'] + b['r']) / 2
                        for o in bodies if o['live']):
                    b['live'] = True
            live = [b for b in bodies if b['live']]
            for b in live:
                b['vy'] += gravity * dt
            contacts = _contacts(live, floor, left, right)
            for _ in range(iterations):
                for c in contacts:
                    _resolve(c, bounce, friction)
            for b in live:
                b['x'] += b['vx'] * dt
                b['y'] += b['vy'] * dt
                b['a'] += b['w'] * dt
            for a, b, px, py, nx, ny, depth in contacts:  # ease overlaps apart
                fix = max(0.0, depth - 0.3) * 0.6 / (a['im'] + (b['im'] if b else 0.0))
                a['x'] += nx * fix * a['im']
                a['y'] += ny * fix * a['im']
                if b:
                    b['x'] -= nx * fix * b['im']
                    b['y'] -= ny * fix * b['im']
            for b in live:  # a little air and rolling drag, so the heap comes to rest
                b['w'] *= 0.998
        out.append(tuple((b['x'], b['y'], b['a']) if b['live'] else None for b in bodies))
    return tuple(out)


def draw_pile(cv, sizes, poses, colors, radius=6, alpha=1.0):
    """Draw one frame of `simulate_pile`: each box of `sizes` at its pose,
    rotated about its centre, coloured from `colors` in turn."""
    for i, ((hw, hh), pose) in enumerate(zip(sizes, poses)):
        if pose is None:
            continue
        x, y, a = pose
        cv.ctx.save()
        cv.ctx.translate(x, y)
        cv.ctx.rotate(a)
        cv.rect(-hw, -hh, 2 * hw, 2 * hh, colors[i % len(colors)], radius=radius, alpha=alpha)
        cv.ctx.restore()


COLORS = (demo.ACCENT, demo.TEAL, '#f2b632', '#7c83f2')
FLOOR = demo.H - 110
COUNT = 10
LANES, LANE_GAP = 4, 130


def _setup():
    """Ten boxes dropped 0.06 s apart, hopping between four lanes so no box
    waits on the one before it: the last lands by about 1.2 s and the heap is
    still from about 1.75 s, holding for the rest of the clip."""
    rnd = random.Random(7)
    sizes = tuple((s, s) for s in (rnd.uniform(36, 52) for _ in range(COUNT)))
    lanes = [(i * (LANES // 2 + 1)) % LANES for i in range(COUNT)]
    drops = tuple((0.05 + 0.06 * i, demo.W / 2 + (lane - (LANES - 1) / 2) * LANE_GAP + rnd.uniform(-25, 25))
                  for i, lane in enumerate(lanes))
    return sizes, drops


def draw(n, cv):
    sizes, drops = _setup()
    poses = simulate_pile(sizes, drops, round(demo.SECONDS * demo.FPS), demo.FPS, FLOOR, 80.0, demo.W - 80.0,
                          seed=2)[n]
    demo.floor(cv, FLOOR)
    draw_pile(cv, sizes, poses, COLORS)
    live = [(p, s) for p, s in zip(poses, sizes) if p is not None]
    if live:
        xs = [p[0] for p, _ in live]
        ys = [p[1] for p, _ in live]
        r = max(s[0] for _, s in live) * 1.5
        cv.mark('pile', min(xs) - r, min(ys) - r, max(xs) - min(xs) + 2 * r, max(ys) - min(ys) + 2 * r)


CAPABILITY = Capability(
    id='rigid-body-pile',
    name='Rigid body pile',
    family='particles',
    group='Rigid bodies',
    aliases=('box stack', 'pile collapse', 'falling boxes'),
    definition='Solid boxes tumble down one after another, crash into the ground and into each other, '
               'and come to rest as a lopsided heap that can tip and slide.',
    phrasings=('drop a bunch of boxes so they bounce around and pile up on the floor',
               'have blocks fall with real physics and land in a messy stack',
               'make cubes rain down and settle into a heap'),
    related=('shape-stacking-drop', 'falling-sand', 'ragdoll', 'physics-letter-drop', 'circle-packing',
             'momentum-fling'),
    api=('videobuilder.capabilities.particles.rigid_body_pile.simulate_pile',
         'videobuilder.capabilities.particles.rigid_body_pile.draw_pile'),
    demo=lambda: demo.film(draw),
)
