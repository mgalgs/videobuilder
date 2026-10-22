"""Fracture Shatter: a solid block is struck, breaks along its cracks into
rigid shards, and the shards fly off the hit, tumble under gravity, bounce
on the floor and come to rest in a heap of rubble."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ..shapes.shape_assemble_from_fragments import shatter


def _centroid(poly):
    return sum(x for x, _ in poly) / len(poly), sum(y for _, y in poly) / len(poly)


def launch(shards, impact, seed=0, speed=520.0, push=(1.0, 0.0), lift=380.0, spin=7.0):
    """Each shard's launch: a dict of `vx, vy` (px/s) and `spin` (rad/s).
    Shards fly away from the `impact` point (x, y), faster the closer they
    sit to it, carried along the direction `push` (the blow's direction,
    normalised) and thrown up by about `lift`. The same `seed` gives the
    same break."""
    rng = random.Random(f'fracture:{seed}')
    ix, iy = impact
    far = max(math.hypot(_centroid(s)[0] - ix, _centroid(s)[1] - iy) for s in shards) or 1.0
    pl = math.hypot(*push) or 1.0
    px, py = push[0] / pl, push[1] / pl
    out = []
    for s in shards:
        cx, cy = _centroid(s)
        dx, dy = cx - ix, cy - iy
        d = math.hypot(dx, dy) or 1.0
        near = 1 - d / far                                  # 1 at the hit, 0 at the far side
        v = speed * (0.45 + 0.9 * near) * rng.uniform(0.75, 1.25)
        vx = (dx / d * 0.55 + px * 0.75) * v + rng.uniform(-60, 60)
        vy = (dy / d * 0.55 + py * 0.75) * v - lift * rng.uniform(0.5, 1.2) * (0.5 + near)
        out.append(dict(vx=vx, vy=vy, spin=rng.uniform(-spin, spin) * (0.5 + near)))
    return out


def pose(shard, kick, t, floor=None, gravity=1900.0, bounce=0.3, friction=0.55, step=1 / 240):
    """Where a rigid `shard` (its points) is `t` seconds after the break,
    thrown by `kick` (one `launch` entry): `(dx, dy, turn)`, the offset of its
    centroid and its rotation about it. It falls under `gravity`; given a
    `floor` y, its lowest corner bounces off it (keeping `bounce` of its
    speed, `friction` of its slide and less of its spin) until it rests."""
    if t <= 0:
        return 0.0, 0.0, 0.0
    cx, cy = _centroid(shard)
    rel = [(x - cx, y - cy) for x, y in shard]
    x = y = a = 0.0
    vx, vy, w = kick['vx'], kick['vy'], kick['spin']
    for _ in range(int(t / step)):
        vy += gravity * step
        x, y, a = x + vx * step, y + vy * step, a + w * step
        if floor is None:
            continue
        ca, sa = math.cos(a), math.sin(a)
        low = max(px * sa + py * ca for px, py in rel)      # lowest corner below the centroid
        if cy + y + low > floor:
            y = floor - cy - low
            if vy > 0:
                vy = -vy * bounce if vy > 120 else 0.0
                vx *= friction
                w *= 0.4
            if abs(vy) < 1:
                vx *= 0.9
                w *= 0.8
    return x, y, a


def draw_fracture(cv, shards, kicks, t, color=demo.INK, floor=None, edge=demo.BG, crack=0.12, shade=0.14,
                  seed=0, **physics):
    """Draw `shards` (from `shatter`) breaking apart `t` seconds after the hit:
    before it (t < 0) they stand whole; for the first `crack` seconds the
    cracks flash in `edge` while the pieces hold; then each flies by its
    `kicks` entry (from `launch`) and tumbles to rest on `floor` (`pose`;
    `physics` passes through). Shards are toned up to `shade` lighter or
    darker so the pieces read as separate."""
    c = cv.ctx
    r, g, b, _ = vb.canvas.rgba(color)
    rng = random.Random(f'fracture-tone:{seed}')
    lines = 0.0 if t < 0 else (2.0 if t >= crack else 2.0 * t / crack)
    for s, kick in zip(shards, kicks):
        tone = rng.uniform(-shade, shade) * (0.0 if t < 0 else 1.0)
        mix = (lambda v: v + (1 - v) * tone) if tone > 0 else (lambda v: v * (1 + tone))
        dx, dy, turn = pose(s, kick, t - crack, floor, **physics)
        cx, cy = _centroid(s)
        c.save()
        c.translate(cx + dx, cy + dy)
        c.rotate(turn)
        c.new_path()
        for i, (x, y) in enumerate(s):
            (c.line_to if i else c.move_to)(x - cx, y - cy)
        c.close_path()
        c.set_source_rgba(mix(r), mix(g), mix(b))
        c.fill_preserve()
        if lines > 0:
            c.set_source_rgba(*vb.canvas.rgba(edge))
            c.set_line_width(lines)
        else:
            c.set_line_width(1.0)   # same-colour hairline hides seams while it's whole
        c.stroke()
        c.restore()


FLOOR = 440
BLOCK = (400, 170, 190, 270)   # x, y, w, h: stands on the floor
BALL_R = 34
HIT_AT = 0.7                   # seconds: when the ball meets the block
_bx, _by, _bw, _bh = BLOCK
IMPACT = (_bx, _by + _bh * 0.55)
SHARDS = shatter([[(_bx, _by), (_bx + _bw, _by), (_bx + _bw, _by + _bh), (_bx, _by + _bh)]], pieces=46, seed=5)
KICKS = launch(SHARDS, IMPACT, seed=5, speed=330, lift=320)


def _ball(t):
    """The ball flies straight in, then drops back off the block onto the floor."""
    start, contact = 100, _bx - BALL_R
    if t < HIT_AT:
        return start + (contact - start) * t / HIT_AT, IMPACT[1]
    u = t - HIT_AT
    return contact - 90 * (1 - math.exp(-3 * u)), min(FLOOR - BALL_R, IMPACT[1] + 950 * u * u)


def draw(n, cv):
    t = n / demo.FPS
    demo.floor(cv, FLOOR, demo.LINE)
    draw_fracture(cv, SHARDS, KICKS, t - HIT_AT, demo.INK, floor=FLOOR, seed=5)
    demo.dot(cv, *_ball(t), BALL_R, '#f2c14e')
    cv.mark('block', *BLOCK)


CAPABILITY = Capability(
    id='fracture-shatter',
    name='Fracture shatter',
    family='particles',
    group='Rigid bodies',
    aliases=('brittle fracture', 'pre-fractured breakup', 'rigid body shatter', 'object shatter'),
    definition='A solid object takes a hit, splits along cracks into hard-edged pieces, and the pieces '
               'fly off, tumble under gravity and settle into a pile.',
    phrasings=('smash the box into a pile of broken chunks',
               'the ball hits the wall and it breaks into pieces that fall to the floor',
               'make the block blow apart into tumbling fragments'),
    related=('shatter', 'impact', 'dam-break', 'type-explosion', 'impact-hit', 'smash-cut'),
    api=('videobuilder.capabilities.particles.fracture_shatter.draw_fracture',
         'videobuilder.capabilities.particles.fracture_shatter.launch',
         'videobuilder.capabilities.particles.fracture_shatter.pose',
         'videobuilder.capabilities.shapes.shape_assemble_from_fragments.shatter'),
    demo=lambda: demo.film(draw),
)
