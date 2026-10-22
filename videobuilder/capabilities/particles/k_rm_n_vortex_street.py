"""Kármán vortex street: a steady stream meets a round obstacle and the wake
behind it rolls up into swirls that peel off one side, then the other, and
drift downstream in two staggered rows.

The flow is analytic, not solved: uniform flow plus the ideal flow round a
cylinder, plus point vortices of alternating spin born just behind it at a
steady beat and carried downstream. Dye released in lanes at the left edge is
advected through that field, and each lane's dye is drawn as one line, so the
swirls show the way smoke does in a wind tunnel. Pure Python, cached per
setting, so any frame can be drawn in any order."""
import functools
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def shed_vortices(t, radius=1.0, speed=1.0, period=2.0, drift=0.85, strength=3.0, spread=(0.3, 1.1),
                  reach=24.0):
    """The vortices alive at time `t` behind an obstacle of `radius` at the
    origin in a stream along +x at `speed`, as `(x, y, circulation)` tuples.
    One is shed every `period / 2`, alternately below and above the centre
    line (screen y down; the upper ones spin clockwise on screen). Each is
    born just behind the obstacle `spread[0]` radii off the line, moves out to
    `spread[1]` as it drifts downstream at `drift * speed`, grows to full
    `strength` over its first half period, and fades out `reach` radii on."""
    R, U = radius, speed
    half = period / 2
    born = 1.2 * R
    vel = drift * U
    newest = math.floor(t / half)
    out = []
    for i in range(newest - int(reach * R / (vel * half)) - 1, newest + 1):
        age = t - i * half
        if age < 0:
            continue
        side = 1 if i % 2 == 0 else -1
        grow = vb.clamp01(age / half)
        x = born + vel * age
        y = side * R * (spread[0] + (spread[1] - spread[0]) * vb.clamp01(age / period))
        fade = vb.clamp01((reach * R - (x - born)) / (4 * R))
        out.append((x, y, side * strength * U * R * grow * grow * (3 - 2 * grow) * fade))
    return out


def _velocity(x, y, vortices, R, U, core2):
    r2 = x * x + y * y
    k = R * R / (r2 * r2) if r2 > 1e-9 else 0.0
    u = U * (1 - k * (x * x - y * y))
    v = -U * k * 2 * x * y
    for vx, vy, g in vortices:
        dx, dy = x - vx, y - vy
        f = g / (2 * math.pi * (dx * dx + dy * dy + core2))
        u -= f * dy
        v += f * dx
    return u, v


def wake_velocity(x, y, t, radius=1.0, speed=1.0, core=0.6, **shedding):
    """Velocity (u, v) at (x, y) and time `t` of a vortex-street flow: the
    stream along +x at `speed`, the ideal flow round a cylinder of `radius`
    at the origin, and the vortices of `shed_vortices` (which `shedding`
    configures), each softened over `core` radii."""
    vort = shed_vortices(t, radius, speed, **shedding)
    return _velocity(x, y, vort, radius, speed, (core * radius) ** 2)


@functools.lru_cache(maxsize=8)
def _streaks(lanes, span, upstream, downstream, frames, fps, warmup, fine, kw):
    """Dye positions per frame: a tuple over frames of a tuple over lanes of
    (x, y) points, oldest dye first."""
    p = dict(kw)
    R, U, core2 = p.get('radius', 1.0), p.get('speed', 1.0), (p.pop('core', 0.6) * p.get('radius', 1.0)) ** 2
    ys = [span * (2 * (j + 0.5) / lanes - 1) for j in range(lanes)]
    every = [1 if abs(y) <= fine * R else 3 for y in ys]  # far lanes barely bend: coarser dye
    dye = [[] for _ in ys]
    h = 1.0 / fps
    out = []
    for f in range(-warmup, frames):
        t = f * h
        for j, y in enumerate(ys):
            if f % every[j] == 0:
                dye[j].append([upstream, y])
        now, mid = shed_vortices(t, **p), shed_vortices(t + h / 2, **p)
        for lane in dye:
            for pt in lane:
                x, y = pt
                u1, v1 = _velocity(x, y, now, R, U, core2)
                u2, v2 = _velocity(x + u1 * h / 2, y + v1 * h / 2, mid, R, U, core2)
                x, y = x + u2 * h, y + v2 * h
                r = math.hypot(x, y)
                if r < R:                     # a step that leaks into the obstacle: back out to its edge
                    x, y = x / r * R * 1.001, y / r * R * 1.001
                pt[0], pt[1] = x, y
            while lane and lane[0][0] > downstream:
                lane.pop(0)
        if f >= 0:
            out.append(tuple(tuple((x, y) for x, y in lane) + ((upstream, y0),)  # dye reaches the edge
                             for y0, lane in zip(ys, dye)))
    return tuple(out)


def vortex_street(frames, fps=30, lanes=24, span=6.0, upstream=-4.5, downstream=20.0, warmup_seconds=4.5,
                  speed=7.0, fine=3.0, **flow):
    """Simulate dye lanes through a vortex street for `frames` frames at
    `fps`, in obstacle-radius units (obstacle at the origin). `lanes` lanes
    start evenly across `+-span` at `upstream` and drop off past
    `downstream`; lanes beyond `fine` radii of the centre line carry coarser
    dye. `speed` is the stream in radii per second; the flow runs
    `warmup_seconds` before frame 0 so the street is already formed. `flow`
    goes to `wake_velocity` (radius, core) and `shed_vortices` (period,
    strength, spread...). Returns, per frame, per lane, the dye points oldest
    first. Cached, so every frame of a film shares one run."""
    flow.setdefault('period', 10 * flow.get('radius', 1.0) / speed)   # Strouhal number 0.2
    kw = tuple(sorted(dict(flow, speed=speed).items()))
    return _streaks(lanes, span, upstream, downstream, frames, fps, round(warmup_seconds * fps), fine, kw)


def draw_vortex_street(cv, streaks, cx, cy, unit, colors=(demo.TEAL, demo.ACCENT), width=1.6, alpha=0.85,
                       obstacle=demo.INK, radius=1.0):
    """Draw one frame of `vortex_street` output on `cv`, the obstacle centred
    at (cx, cy) with `unit` px per radius. Lanes cycle through `colors`; the
    obstacle is outlined in `obstacle` (None to skip it)."""
    c = cv.ctx
    c.save()
    c.set_line_width(width)
    c.set_line_cap(1)   # round
    c.set_line_join(1)
    for j, lane in enumerate(streaks):
        if len(lane) < 2:
            continue
        c.new_path()
        pts = [(cx + x * unit, cy + y * unit) for x, y in lane]
        c.move_to(*pts[0])
        mx, my = pts[0]
        for (ax, ay), (bx, by) in zip(pts[1:], pts[2:]):   # a quadratic through each point's midpoints
            nx, ny = (ax + bx) / 2, (ay + by) / 2
            c.curve_to(mx + (ax - mx) * 2 / 3, my + (ay - my) * 2 / 3, nx + (ax - nx) * 2 / 3,
                       ny + (ay - ny) * 2 / 3, nx, ny)
            mx, my = nx, ny
        c.line_to(*pts[-1])
        c.set_source_rgba(*rgba(colors[j % len(colors)], alpha))
        c.stroke()
    c.restore()
    if obstacle:
        demo.dot(cv, cx, cy, radius * unit, demo.BG)
        cv.arc(cx, cy, radius * unit, 0, 2 * math.pi, obstacle, width=3)


UNIT = 34         # px per obstacle radius in the demo
CX, CY = 190, demo.H / 2


def draw(n, cv):
    frames = round(demo.SECONDS * demo.FPS)
    streaks = vortex_street(frames, demo.FPS, span=(demo.H / 2 - 40) / UNIT, upstream=-(CX - 70) / UNIT,
                            downstream=(demo.W - 70 - CX) / UNIT + 1.5)
    with cv.clip(70, 40, demo.W - 140, demo.H - 80):
        draw_vortex_street(cv, streaks[n], CX, CY, UNIT)
    cv.mark('obstacle', CX - UNIT, CY - UNIT, 2 * UNIT, 2 * UNIT)


CAPABILITY = Capability(
    id='k-rm-n-vortex-street',
    name='Kármán vortex street',
    family='particles',
    group='Fluids',
    aliases=('vortex shedding', 'wake vortices', 'von Kármán street'),
    definition='A stream flowing past a round obstacle curls into swirls that break away from alternate '
               'sides and float downstream in two staggered rows.',
    phrasings=('smoke streaming past a pole and rolling into alternating eddies behind it',
               'flow lines that wrap round a circle and leave a wavy trail of swirls',
               'a wind-tunnel wake where vortices peel off one side then the other'),
    related=('swirl', 'curl-noise-flow', 'lightning-bolt', 'fountain', 'meteor-shower',
             'turbulence-displacement'),
    api=('videobuilder.capabilities.particles.k_rm_n_vortex_street.draw_vortex_street',
         'videobuilder.capabilities.particles.k_rm_n_vortex_street.vortex_street',
         'videobuilder.capabilities.particles.k_rm_n_vortex_street.wake_velocity'),
    demo=lambda: demo.film(draw),
)
