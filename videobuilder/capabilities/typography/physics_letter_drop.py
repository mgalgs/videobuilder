"""Physics letter drop: the letters of a word fall one after another under
gravity, tip and tumble as they hit the floor and each other, and come to
rest as a loose heap."""
import math
import random
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _corners(x, y, a, hw, hh):
    c, s = math.cos(a), math.sin(a)
    return [(x + px * c - py * s, y + px * s + py * c) for px in (-hw, hw) for py in (-hh, hh)]


def _contact(b, px, py, nx, ny, e, mu):
    """Impulse body `b` off a fixed surface with normal (nx, ny), touching at (px, py)."""
    rx, ry = px - b['x'], py - b['y']
    vx, vy = b['vx'] - b['w'] * ry, b['vy'] + b['w'] * rx
    vn = vx * nx + vy * ny
    if vn >= 0:
        return
    rn = rx * ny - ry * nx
    j = -(1 + e) * vn / (1 / b['m'] + rn * rn / b['I'])
    tx, ty = -ny, nx
    vt = vx * tx + vy * ty
    rt = rx * ty - ry * tx
    jt = max(-mu * j, min(mu * j, -vt / (1 / b['m'] + rt * rt / b['I'])))
    ix, iy = j * nx + jt * tx, j * ny + jt * ty
    b['vx'] += ix / b['m']
    b['vy'] += iy / b['m']
    b['w'] += (rx * iy - ry * ix) / b['I']


@lru_cache(maxsize=16)
def simulate(sizes, frames, fps=30, floor=500.0, left=0.0, right=960.0, drops=(), spawn_y=-60.0,
             gravity=2600.0, bounce=0.3, friction=0.6, seed=0, substeps=12):
    """Rigid-body poses for a row of letters dropped into a box.

    `sizes`: one `(half_width, half_height)` per letter; `drops`: one
    `(start_seconds, x)` per letter, where it is released above the frame
    with a little spin. Letters are boxes against the floor and the side
    walls and discs against each other. Returns, per frame, a tuple of
    `(x, y, angle)` for each letter (`None` before it is released). The same
    arguments give the same result, so it is computed once and cached."""
    rnd = random.Random(seed)
    bodies = []
    for (hw, hh), (t0, x) in zip(sizes, drops):
        m = 4 * hw * hh
        bodies.append(dict(x=x, y=spawn_y - hh, vx=rnd.uniform(-60, 60), vy=rnd.uniform(0, 150),
                           a=rnd.uniform(-0.4, 0.4), w=rnd.uniform(-3, 3), hw=hw, hh=hh, m=m,
                           I=m * (hw * hw + hh * hh) / 3, r=0.92 * max(hw, hh), t0=t0))
    dt = 1 / fps / substeps
    out = []
    for n in range(frames):
        for k in range(substeps):
            t = (n * substeps + k) * dt
            live = [b for b in bodies if t >= b['t0']]
            for b in live:
                b['vy'] += gravity * dt
                b['x'] += b['vx'] * dt
                b['y'] += b['vy'] * dt
                b['a'] += b['w'] * dt
            for i, b in enumerate(live):          # letter against letter, as discs
                for o in live[i + 1:]:
                    dx, dy = o['x'] - b['x'], o['y'] - b['y']
                    d, rr = math.hypot(dx, dy) or 1e-6, b['r'] + o['r']
                    if d >= rr:
                        continue
                    nx, ny = dx / d, dy / d
                    share = (rr - d) / (b['m'] + o['m'])
                    b['x'] -= nx * share * o['m']
                    b['y'] -= ny * share * o['m']
                    o['x'] += nx * share * b['m']
                    o['y'] += ny * share * b['m']
                    rv = (o['vx'] - b['vx']) * nx + (o['vy'] - b['vy']) * ny
                    if rv < 0:
                        j = -(1 + bounce) * rv / (1 / b['m'] + 1 / o['m'])
                        tv = ((o['vx'] - o['w'] * o['r'] * -ny) - (b['vx'] + b['w'] * b['r'] * -ny)) * -ny \
                            + ((o['vy'] - o['w'] * o['r'] * nx) - (b['vy'] + b['w'] * b['r'] * nx)) * nx
                        jt = max(-friction * j, min(friction * j, -tv / (1 / b['m'] + 1 / o['m'])))
                        for body, s in ((b, -1), (o, 1)):
                            body['vx'] += s * (j * nx - jt * ny) / body['m']
                            body['vy'] += s * (j * ny + jt * nx) / body['m']
                            body['w'] -= jt * body['r'] / body['I']
            for b in live:                        # box against floor and walls
                cs = _corners(b['x'], b['y'], b['a'], b['hw'], b['hh'])
                for wall, nx, ny, depth in ((floor, 0, -1, lambda p: p[1] - floor),
                                            (left, 1, 0, lambda p: left - p[0]),
                                            (right, -1, 0, lambda p: p[0] - right)):
                    deep = max(depth(p) for p in cs)
                    if deep <= 0:
                        continue
                    b['x'] += nx * deep
                    b['y'] += ny * deep
                    for p in cs:
                        if depth(p) > 0:
                            _contact(b, p[0], p[1], nx, ny, bounce, friction)
                    if ny:                        # resting on the floor: rolling drag, so it settles
                        b['w'] *= 0.985
                        b['vx'] *= 0.99
                    cs = _corners(b['x'], b['y'], b['a'], b['hw'], b['hh'])
        out.append(tuple((b['x'], b['y'], b['a']) if n / fps >= b['t0'] else None for b in bodies))
    return tuple(out)


def letter_boxes(text, font):
    """`(half_width, half_height)` of each non-space letter's body in `text`:
    its advance across, and the font's cap height up."""
    cap = 0.36 * font.size
    return tuple((vb.text.measure(ch, font) / 2, cap) for ch in text if not ch.isspace())


def draw_letter_drop(cv, text, font, poses, color, alpha=1.0):
    """Draw the non-space letters of `text` at `poses` (one frame of
    `simulate`), each rotated about its centre. Returns the Box around the
    letters on screen (empty before any falls)."""
    _, baseline = vb.text._content(font)
    cap = 0.36 * font.size
    xs, ys = [], []
    for ch, pose in zip([c for c in text if not c.isspace()], poses):
        if pose is None:
            continue
        x, y, a = pose
        w = vb.text.measure(ch, font)
        cv.ctx.save()
        cv.ctx.translate(x, y)
        cv.ctx.rotate(a)
        vb.text.draw(cv, [ch], font, -w / 2, -(baseline - cap), color, alpha=alpha)
        cv.ctx.restore()
        r = math.hypot(w / 2, cap)
        xs += [x - r, x + r]
        ys += [y - r, y + r]
    if not xs:
        return vb.Box(0, 0, 0, 0)
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


TEXT = 'GRAVITY'
FLOOR = demo.H - 90
BIN = (demo.W / 2 - 230, demo.W / 2 + 230)


def _font():
    return demo.font(110, 900)


def _poses():
    f = _font()
    sizes = letter_boxes(TEXT, f)
    rnd = random.Random(3)
    drops = tuple((0.1 + 0.16 * i, demo.W / 2 + rnd.uniform(-150, 150)) for i in range(len(sizes)))
    return simulate(sizes, round(demo.SECONDS * demo.FPS), demo.FPS, FLOOR, BIN[0], BIN[1], drops, seed=5)


def draw(n, cv):
    lo, hi = BIN
    cv.line(lo, 60, lo, FLOOR, demo.LINE, width=2)
    cv.line(hi, 60, hi, FLOOR, demo.LINE, width=2)
    demo.floor(cv, FLOOR)
    box = draw_letter_drop(cv, TEXT, _font(), _poses()[n], demo.INK)
    cv.mark('letters', *box)


CAPABILITY = Capability(
    id='physics-letter-drop',
    name='Physics letter drop',
    family='typography',
    group='Physics and particles',
    aliases=('gravity letters', 'letter collision physics', 'falling letters pile'),
    definition='The letters of a word drop in one by one under gravity, knock against the floor and '
               'each other, and settle into a jumbled heap.',
    phrasings=('the letters fall down and pile up at the bottom',
               'drop the word in letter by letter so they tumble into a heap',
               'make the text fall with real physics and crash into a pile'),
    related=('character-drop', 'gravity-drop', 'hover-letter-displacement', 'elastic-collisions',
             'letter-roll', 'falling-sand'),
    api=('videobuilder.capabilities.typography.physics_letter_drop.simulate',
         'videobuilder.capabilities.typography.physics_letter_drop.draw_letter_drop',
         'videobuilder.capabilities.typography.physics_letter_drop.letter_boxes'),
    demo=lambda: demo.film(draw),
)
