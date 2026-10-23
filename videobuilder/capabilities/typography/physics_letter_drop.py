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


def _overlap(b, o, pad):
    """Separating-axis test between two letter boxes. Returns `None` if they
    are apart, else `(depth, nx, ny, owner)`: the shallowest way out, with the
    normal pointing from `b` to `o`, and `owner` the box whose face it is.
    Each box is grown by `pad` all round."""
    best = None
    for owner in (b, o):
        c, s = math.cos(owner['a']), math.sin(owner['a'])
        for ax, ay in ((c, s), (-s, c)):
            pb = [px * ax + py * ay for px, py in _corners(b['x'], b['y'], b['a'], b['hw'] + pad, b['hh'] + pad)]
            po = [px * ax + py * ay for px, py in _corners(o['x'], o['y'], o['a'], o['hw'] + pad, o['hh'] + pad)]
            depth = min(max(pb), max(po)) - max(min(pb), min(po))
            if depth <= 0:
                return None
            if best is None or depth < best[0]:
                if (o['x'] - b['x']) * ax + (o['y'] - b['y']) * ay < 0:
                    ax, ay = -ax, -ay
                best = (depth, ax, ay, owner)
    return best


def _collide(b, o, e, mu, pad):
    """Push two overlapping letter boxes apart along their shallowest axis
    and trade an impulse, with friction and spin, at the corners that dug in."""
    hit = _overlap(b, o, pad)
    if hit is None:
        return
    depth, nx, ny, owner = hit
    total = b['m'] + o['m']
    b['x'] -= nx * depth * o['m'] / total
    b['y'] -= ny * depth * o['m'] / total
    o['x'] += nx * depth * b['m'] / total
    o['y'] += ny * depth * b['m'] / total
    # the contact is at the other box's corners that reach furthest past the owner's face
    other, sign = (o, -1) if owner is b else (b, 1)
    cs = _corners(other['x'], other['y'], other['a'], other['hw'] + pad, other['hh'] + pad)
    reach = [sign * (px * nx + py * ny) for px, py in cs]
    top = max(reach)
    pts = [p for p, r in zip(cs, reach) if r > top - 0.25 * depth - 0.5]
    for px, py in pts:
        rbx, rby, rox, roy = px - b['x'], py - b['y'], px - o['x'], py - o['y']
        vx = (o['vx'] - o['w'] * roy) - (b['vx'] - b['w'] * rby)
        vy = (o['vy'] + o['w'] * rox) - (b['vy'] + b['w'] * rbx)
        vn = vx * nx + vy * ny
        if vn >= 0:
            continue
        def kick(tx, ty):
            rb, ro = rbx * ty - rby * tx, rox * ty - roy * tx
            return 1 / b['m'] + 1 / o['m'] + rb * rb / b['I'] + ro * ro / o['I']
        j = -(1 + e) * vn / kick(nx, ny) / len(pts)
        tx, ty = -ny, nx
        jt = max(-mu * j, min(mu * j, -(vx * tx + vy * ty) / kick(tx, ty) / len(pts)))
        ix, iy = j * nx + jt * tx, j * ny + jt * ty
        for body, rx, ry, s in ((b, rbx, rby, -1), (o, rox, roy, 1)):
            body['vx'] += s * ix / body['m']
            body['vy'] += s * iy / body['m']
            body['w'] += s * (rx * iy - ry * ix) / body['I']


@lru_cache(maxsize=16)
def simulate(sizes, frames, fps=30, floor=500.0, left=0.0, right=960.0, drops=(), spawn_y=-60.0,
             gravity=2600.0, bounce=0.3, friction=0.6, seed=0, substeps=12, gap=4.0):
    """Rigid-body poses for a row of letters dropped into a box.

    `sizes`: one `(half_width, half_height)` per letter; `drops`: one
    `(start_seconds, x)` per letter, where it is released above the frame
    with a little spin. Letters are boxes against the floor and the side
    walls and against each other, so
    they stack without passing through one another (`gap` pixels apart, so
    two heavy letters never read as one). Returns, per frame, a tuple of
    `(x, y, angle)` for each letter (`None` before it is released). The same
    arguments give the same result, so it is computed once and cached."""
    rnd = random.Random(seed)
    bodies = []
    for (hw, hh), (t0, x) in zip(sizes, drops):
        m = 4 * hw * hh
        bodies.append(dict(x=x, y=spawn_y - hh, vx=rnd.uniform(-60, 60), vy=rnd.uniform(0, 150),
                           a=rnd.uniform(-0.4, 0.4), w=rnd.uniform(-3, 3), hw=hw, hh=hh, m=m,
                           I=m * (hw * hw + hh * hh) / 3, t0=t0))
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
            for i, b in enumerate(live):          # letter against letter, as boxes
                for o in live[i + 1:]:
                    _collide(b, o, bounce, friction, gap / 2)
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
    drops = tuple((0.15 * i, demo.W / 2 + rnd.uniform(-150, 150)) for i in range(len(sizes)))
    # released just above the top edge, so the first letter is already falling into view on frame 0
    return simulate(sizes, round(demo.SECONDS * demo.FPS), demo.FPS, FLOOR, BIN[0], BIN[1], drops, spawn_y=0.0,
                    seed=5)


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
