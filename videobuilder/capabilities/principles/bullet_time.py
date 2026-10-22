"""Bullet Time: the action slows almost to a standstill at its peak while the
camera keeps moving at full speed, swinging round the frozen moment, then
time picks up again. Two pieces a film can use apart: `bullet_time` remaps
the clock, `orbit_project` turns a world point into a frame point for a
camera circling a pivot."""
import math
import random

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique


def _smooth(u):
    u = vb.clamp01(u)
    return u * u * (3 - 2 * u)


def _smooth_integral(u):
    """The integral of smoothstep (3u^2 - 2u^3) from 0 to `u` in [0, 1]."""
    u = vb.clamp01(u)
    return u ** 3 - u ** 4 / 2


def bullet_time(t, start, end, slow=0.04, ramp=0.3):
    """Film time `t` (s) -> scene time (s) for a bullet-time hold between
    `start` and `end`: the scene runs at full speed, eases down to `slow`
    times speed over `ramp` seconds, holds there, and eases back up to full
    speed by `end`. Returns `(scene_t, speed)`; `speed` (1 outside the hold,
    `slow` at its depth) is handy for motion streaks and blur.

    Closed form, so any frame evaluates alone. Drive the action from
    `scene_t` and the camera from `t`, and the camera keeps moving while
    the action all but stops."""
    ramp = min(ramp, (end - start) / 2)
    drop = 1 - slow

    def held(x):  # how much the hold has slowed things, integrated from `start` to `x`
        if x <= start:
            return 0.0
        x = min(x, end)
        total = 0.0
        a = min(x, start + ramp)
        total += ramp * _smooth_integral((a - start) / ramp)
        if x > start + ramp:
            total += min(x, end - ramp) - (start + ramp)
        if x > end - ramp:
            total += ramp * (0.5 - _smooth_integral(1 - (x - (end - ramp)) / ramp))
        return total * drop

    if t <= start or t >= end:
        w = 0.0
    elif t < start + ramp:
        w = _smooth((t - start) / ramp)
    elif t > end - ramp:
        w = _smooth((end - t) / ramp)
    else:
        w = 1.0
    return t - held(t), 1 - drop * w


def orbit_project(x, y, z, yaw, pitch=0.22, distance=1500.0, focal=1300.0, cx=None, cy=None):
    """World point (x, y, z), y down, round a pivot at the origin -> frame
    point `(sx, sy, depth)` seen by a camera orbiting the pivot: `yaw`
    radians round the vertical axis, tilted down by `pitch`, `distance`
    from the pivot, with perspective `focal`. Sort by `depth` (larger is
    farther) to draw back to front. `cx, cy` default to the frame centre."""
    cx = demo.W / 2 if cx is None else cx
    cy = demo.H / 2 if cy is None else cy
    c, s = math.cos(yaw), math.sin(yaw)
    x, z = x * c - z * s, x * s + z * c
    c, s = math.cos(pitch), math.sin(pitch)
    y, z = y * c - z * s, y * s + z * c
    depth = max(distance + z, 1.0)
    k = focal / depth
    return cx + x * k, cy + y * k, depth


# ---- the demo: a slug punches through a pane; the moment hangs while the camera circles it ----

START, END = 0.7, 2.45          # film seconds of the hold
YAW0, YAW1 = -0.55, -2.15        # the camera swings ~90 degrees across the hold
FLOOR = 190
SLUG_V = 1700.0                  # world px per scene second
FOCAL = 1800.0


def _clock(t):
    return bullet_time(t, START, END, slow=0.03, ramp=0.28)


IMPACT = _clock(START + 0.16)[0]   # the slug reaches the pane just as time drains away


def _shards():
    rnd = random.Random(7)
    out, cols, rows, w, h = [], 5, 4, 300, 220
    for i in range(cols):
        for j in range(rows):
            z0 = -w / 2 + (i + 0.5) * w / cols
            y0 = -h / 2 + (j + 0.5) * h / rows - 40
            dist = math.hypot(z0, y0 + 40) + 30
            out.append(dict(z=z0, y=y0, hw=w / cols / 2 * 0.94, hh=h / rows / 2 * 0.94,
                            vx=rnd.uniform(250, 700), vy=(y0 + 40) / dist * rnd.uniform(200, 520) - 120,
                            vz=z0 / dist * rnd.uniform(200, 520), spin=rnd.uniform(-9, 9),
                            tint=rnd.uniform(0.75, 1.0)))
    return out


SHARDS = _shards()


def _poly(cv, pts, color, alpha=1.0):
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0][:2])
    for p in pts[1:]:
        c.line_to(*p[:2])
    c.close_path()
    c.set_source_rgba(*rgba(color, alpha))
    c.fill()


def draw(n, cv):
    t = n / demo.FPS
    tau, speed = _clock(t)
    yaw = vb.interpolate(t, [START - 0.15, END + 0.1], [YAW0, YAW1], ease=_smooth)
    proj = lambda x, y, z: orbit_project(x, y, z, yaw, focal=FOCAL)  # noqa: E731

    # the floor grid: what makes the camera's swing readable
    for k in range(-6, 7):
        a, b = proj(k * 120, FLOOR, -720), proj(k * 120, FLOOR, 720)
        cv.line(a[0], a[1], b[0], b[1], demo.LINE, width=2, alpha=0.8)
        a, b = proj(-720, FLOOR, k * 120), proj(720, FLOOR, k * 120)
        cv.line(a[0], a[1], b[0], b[1], demo.LINE, width=2, alpha=0.8)

    items = []  # (depth, painter)
    dt = tau - IMPACT
    for s in SHARDS:
        if dt <= 0:
            x, y, z, ang = 0.0, s['y'], s['z'], 0.0
        else:
            x, y, z = s['vx'] * dt, s['y'] + s['vy'] * dt + 600 * dt * dt, s['z'] + s['vz'] * dt
            ang = s['spin'] * dt
        ca, sa = math.cos(ang), math.sin(ang)
        corners = []
        for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            du, dv = u * s['hw'], v * s['hh']   # spin in the shard's own plane, tipped forward as it goes
            corners.append(proj(x + dv * sa * 0.6, y + dv * ca, z + du))
        depth = sum(p[2] for p in corners) / 4
        items.append((depth, lambda cv, c=corners, s=s: _poly(cv, c, demo.TEAL, alpha=0.55 + 0.4 * s['tint'])))

    # the slug, its streak shrinking as time slows, and the air rings it leaves behind
    sx = SLUG_V * dt + 40   # through the pane (x = 0) at IMPACT
    head = proj(sx, -40, 0)
    tail = proj(sx - 40 - 360 * speed, -40, 0)

    def slug(cv, head=head, tail=tail):
        cv.line(tail[0], tail[1], head[0], head[1], demo.ACCENT, width=10 * FOCAL / head[2], alpha=0.45)
        demo.dot(cv, head[0], head[1], 15 * FOCAL / head[2], color=demo.INK)
    items.append((head[2], slug))
    for rx in (-600, -400, -200, 160, 360):
        age = (sx - rx) / SLUG_V
        if age <= 0 or age > 1.2:
            continue
        r = 30 + 150 * age
        ring = [proj(rx, -40 + r * math.sin(a), r * math.cos(a)) for a in
                (2 * math.pi * i / 32 for i in range(33))]
        alpha = 0.6 * (1 - age / 1.2)

        def paint(cv, ring=ring, alpha=alpha):
            c = cv.ctx
            c.new_path()
            c.move_to(*ring[0][:2])
            for p in ring[1:]:
                c.line_to(*p[:2])
            c.set_source_rgba(*rgba(demo.INK, alpha))
            c.set_line_width(3)
            c.stroke()
        items.append((sum(p[2] for p in ring) / len(ring), paint))

    for _, paint in sorted(items, key=lambda it: -it[0]):
        paint(cv)
    cv.mark('slug', head[0] - 15, head[1] - 15, 30, 30)

    # the clock readout: the scene's speed against the film's
    f = demo.mono(30)
    vb.text.draw(cv, [f'time  {speed:4.2f}x'], f, 60, demo.H - 90, demo.MUTED)
    cv.rect(60, demo.H - 44, 260, 8, demo.LINE, radius=4)
    cv.rect(60, demo.H - 44, 260 * speed, 8, demo.ACCENT, radius=4)


TECHNIQUE = Technique(
    id='bullet-time',
    name='Bullet Time',
    family='principles',
    group='Time remapping',
    aliases=('frozen moment', 'time slice', 'time freeze orbit', 'flow-motion'),
    definition='The action slows to a near standstill at its peak while the camera keeps travelling '
               'round it at normal speed, then the action speeds back up.',
    phrasings=('freeze the moment and swing the camera around it',
               'slow it right down mid-action and circle the camera round it',
               'hang the explosion in the air while we circle it'),
    related=('hyperlapse', 'delay', 'timing', 'scatter-time-playback', 'orbit-shot', 'orbital-pulse'),
    api=('videobuilder.techniques.principles.bullet_time.bullet_time',
         'videobuilder.techniques.principles.bullet_time.orbit_project'),
    demo=lambda: demo.film(draw),
)
