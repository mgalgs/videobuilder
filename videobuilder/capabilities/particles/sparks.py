"""Sparks: hot streaks spray out of one point, arc down under gravity, cool
from white through yellow to orange, and wink out within a second."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

HOT = ((1.0, 1.0, 0.92), (1.0, 0.86, 0.35), (1.0, 0.48, 0.12))   # white-hot, yellow, orange


def sparks(t, x, y, angle=-0.35, spread=0.6, rate=90, speed=(900, 1700), life=(0.35, 0.8),
           gravity=2600, drag=1.2, floor=None, bounce=0.35, start=0.0, stop=None, seed=0, trail=0.03):
    """The live sparks at time `t` (seconds) from an emitter at (x, y), as
    `(x0, y0, x1, y1, heat)` streaks: tail to head, `heat` 1 when just born
    falling to 0 as the spark dies.

    Sparks leave at `rate` per second from `start` until `stop` (None: never
    stops), each aimed within `spread` radians either side of `angle`
    (radians, 0 = right, negative = up), at a speed drawn from `speed` px/s,
    living a time drawn from `life`. `gravity` pulls down in px/s^2; `drag`
    slows them (1/s). With `floor` set, a spark that reaches that y bounces
    once, keeping `bounce` of its fall speed. Each streak is the path over the
    last `trail` seconds, so faster sparks draw longer. Stateless: any `t` can
    be drawn on its own, and the same `seed` gives the same spray."""
    out = []
    first = max(0, math.ceil((t - life[1] - start) * rate))
    last = math.floor((t - start) * rate) if stop is None else math.floor((min(t, stop) - start) * rate)
    for i in range(first, last + 1):
        born = start + i / rate
        r = random.Random(f'{seed}:{i}')
        a = angle + r.uniform(-spread, spread)
        v = r.uniform(*speed)
        span = r.uniform(*life)
        age = t - born
        if age < 0 or age > span:
            continue
        vx, vy = v * math.cos(a), v * math.sin(a)
        head = _at(x, y, vx, vy, age, gravity, drag, floor, bounce)
        tail = _at(x, y, vx, vy, max(0.0, age - trail), gravity, drag, floor, bounce)
        out.append((tail[0], tail[1], head[0], head[1], 1 - age / span))
    return out


def _at(x, y, vx, vy, s, g, k, floor, bounce):
    """Where a spark launched from (x, y) at (vx, vy) is after `s` seconds,
    with linear drag `k` and gravity `g`; bounced once off `floor`."""
    def pos(x, y, vx, vy, s):
        e = math.exp(-k * s)
        px = x + vx * (1 - e) / k
        py = y + g / k * s + (vy - g / k) * (1 - e) / k
        return px, py, vx * e, g / k + (vy - g / k) * e
    px, py, _, _ = pos(x, y, vx, vy, s)
    if floor is None or py <= floor:
        return px, py
    lo, hi = 0.0, s   # find the moment it touched the floor, then relaunch from there
    for _ in range(24):
        mid = (lo + hi) / 2
        if pos(x, y, vx, vy, mid)[1] > floor:
            hi = mid
        else:
            lo = mid
    hx, _, hvx, hvy = pos(x, y, vx, vy, hi)
    px, py, _, _ = pos(hx, floor, hvx * 0.6, -abs(hvy) * bounce, s - hi)
    return px, min(py, floor)


def heat_color(heat):
    """The colour of a spark at `heat` 1 -> 0: white-hot, yellow, then orange."""
    u = (1 - vb.clamp01(heat)) * (len(HOT) - 1)
    i = min(int(u), len(HOT) - 2)
    f = u - i
    return tuple(a + (b - a) * f for a, b in zip(HOT[i], HOT[i + 1]))


def draw_sparks(cv, t, x, y, width=3.0, glow=True, **kw):
    """Draw the sparks of `sparks(t, x, y, **kw)` as additive streaks with
    round ends: bright where they cross, each fading and thinning as it cools,
    with a hot flare at the emitter while it is firing. Returns the streaks."""
    streaks = sparks(t, x, y, **kw)
    c = cv.ctx
    c.save()
    c.set_operator(cairo.OPERATOR_ADD)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for x0, y0, x1, y1, heat in streaks:
        r, g, b = heat_color(heat)
        alpha = min(1.0, heat * 1.6)
        if glow:
            c.set_source_rgba(r, g * 0.8, b * 0.5, alpha * 0.18)
            c.set_line_width(width * 3.5 * (0.5 + heat))
            c.move_to(x0, y0)
            c.line_to(x1, y1)
            c.stroke()
        c.set_source_rgba(r, g, b, alpha)
        c.set_line_width(width * (0.4 + 0.6 * heat))
        c.move_to(x0, y0)
        c.line_to(x1, y1)
        c.stroke()
    start, stop = kw.get('start', 0.0), kw.get('stop')
    if glow and t >= start and (stop is None or t <= stop):
        flicker = 0.75 + 0.25 * random.Random(f"{kw.get('seed', 0)}:{round(t * 60)}").random()
        for rad, a in ((width * 14, 0.12), (width * 6, 0.35), (width * 2.2, 1.0)):
            pat = cairo.RadialGradient(x, y, 0, x, y, rad * flicker)
            pat.add_color_stop_rgba(0, 1, 0.97, 0.85, a)
            pat.add_color_stop_rgba(1, 1, 0.6, 0.2, 0)
            c.set_source(pat)
            c.arc(x, y, rad * flicker, 0, 2 * math.pi)
            c.fill()
    c.restore()
    return streaks


def draw(n, cv):
    t = n / demo.FPS
    ground = demo.H * 0.78
    demo.floor(cv, ground, demo.LINE)
    # A grinding wheel standing in for the source: a disc edge-on to a bar.
    cx, cy = demo.W * 0.3, demo.H * 0.42
    cv.rect(cx - 260, cy - 14, 250, 28, demo.MUTED, radius=6)
    spin = t * 40
    demo.dot(cv, cx - 30, cy - 70, 90, demo.MUTED)
    for k in range(6):
        a = spin + k * math.pi / 3
        cv.line(cx - 30, cy - 70, cx - 30 + 80 * math.cos(a), cy - 70 + 80 * math.sin(a), demo.BG, width=3)
    draw_sparks(cv, t, cx + 55, cy - 30, angle=-0.3, spread=0.5, speed=(650, 1350), floor=ground, start=0.2, stop=2.4, seed=3)
    cv.mark('emitter', cx + 35, cy - 50, 40, 40)


CAPABILITY = Capability(
    id='sparks',
    name='Sparks',
    family='particles',
    group='Emitters',
    aliases=('spark shower', 'grinder sparks', 'welding sparks', 'spark overlay'),
    definition='A stream of tiny glowing streaks shoots out of one hot point, curves downward as it flies '
               'and burns out in well under a second.',
    phrasings=('sparks flying off it like from a metal grinder',
               'a shower of hot sparks spraying out and falling away',
               'make it throw off welding sparks'),
    related=('electric-arc', 'lightning-flash', 'lens-flare', 'lightning-bolt', 'fresnel-edge-glow',
             'diffraction-spikes'),
    api=('videobuilder.capabilities.particles.sparks.draw_sparks',
         'videobuilder.capabilities.particles.sparks.sparks',
         'videobuilder.capabilities.particles.sparks.heat_color'),
    demo=lambda: demo.film(draw),
)
