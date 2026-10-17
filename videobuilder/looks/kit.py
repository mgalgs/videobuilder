"""Drawing helpers the looks share: polygon fills, round dabs, beams from a
beacon, a beat pulse, seeded grids. A new look reaches for these instead of
writing its own."""
import math
import random

import cairo

from ..canvas import rgba


def rgb(colour, alpha=1.0):
    """A colour as an (r, g, b, a) tuple for cairo, with `alpha` applied."""
    r, g, b, a = rgba(colour)
    return (r, g, b, a * alpha)


def mix(a, b, p):
    """Colour `a` blended towards `b` by `p` (0..1), as (r, g, b)."""
    a, b = rgba(a), rgba(b)
    return tuple(a[i] + (b[i] - a[i]) * p for i in range(3))


def inside(pts, x, y):
    """Whether (x, y) is inside the polygon `pts` (even-odd)."""
    hit = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def path(ctx, pts, close=True):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if close:
        ctx.close_path()


def fill(cv, pts, colour, alpha=1.0, outline=None, width=0):
    """Fills the polygon `pts`, with an optional round-joined `outline`."""
    c = cv.ctx
    path(c, pts)
    c.set_source_rgba(*rgb(colour, alpha))
    if outline:
        c.fill_preserve()
        c.set_source_rgba(*rgb(outline))
        c.set_line_width(width)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke()
    else:
        c.fill()


def outline(cv, pts, colour, width, alpha=1.0):
    c = cv.ctx
    path(c, pts)
    c.set_source_rgba(*rgb(colour, alpha))
    c.set_line_width(width)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.stroke()


class clip_to:
    """`with clip_to(cv, pts):` -- draw only inside the polygon `pts`."""

    def __init__(self, cv, pts):
        self.cv, self.pts = cv, pts

    def __enter__(self):
        self.cv.ctx.save()
        path(self.cv.ctx, self.pts)
        self.cv.ctx.clip()
        return self.cv

    def __exit__(self, *exc):
        self.cv.ctx.restore()


def disc(cv, x, y, r, colour, alpha=1.0):
    c = cv.ctx
    c.new_path()
    c.arc(x, y, max(0.1, r), 0, 2 * math.pi)
    c.set_source_rgba(*rgb(colour, alpha))
    c.fill()


def circle_pts(cx, cy, r, n=64, sy=1.0):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + sy * r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def dab(c, x, y, ang, length, colour, width):
    """One short round-capped brush stroke centred on (x, y). `colour` is an
    rgb() tuple; set the line cap to round once before a run of dabs."""
    dx, dy = math.cos(ang) * length / 2, math.sin(ang) * length / 2
    c.set_source_rgba(*colour)
    c.set_line_width(width)
    c.move_to(x - dx, y - dy)
    c.line_to(x + dx, y + dy)
    c.stroke()


def beams(scene, t, length=None, period=4.0):
    """The beacon's two opposite beams as it turns: [(polygon, strength)],
    strength 0..1. A beam pointing at us widens; one pointing away fades.
    [] with no beacon."""
    if not scene.beacon:
        return []
    u = scene.u
    length = length if length is not None else 0.85 * max(scene.w, scene.h)
    x0, y0 = scene.beacon
    out = []
    for a in (2 * math.pi * t / period, 2 * math.pi * t / period + math.pi):
        reach = length * math.cos(a)
        spread = (26 + 70 * abs(math.sin(a))) * u
        strength = 0.35 + 0.65 * abs(math.cos(a))
        lift = 30 * u * math.sin(a)
        out.append(([(x0, y0 - 10 * u), (x0 + reach, y0 - spread + lift), (x0 + reach, y0 + spread + lift),
                     (x0, y0 + 10 * u)], strength))
    return out


def pulse(t, bpm, every=1):
    """1 on each `every`-th beat, decaying within the beat: a beat accent."""
    return math.exp(-6 * since_beat(t, bpm, every) * bpm / 60.0)


def since_beat(t, bpm, every=1):
    """Seconds since the last `every`-th beat."""
    return t % (60.0 / bpm * every)


_GRIDS = {}


def jittered_grid(w, h, pitch, jitter, seed, extra=0):
    """Seeded, jittered grid points over (w, h) as (x, y, tone, phase, speed)
    -- the dab and dot layouts the painterly looks use. Cached by its
    arguments: worked out once, only the motion is per frame."""
    key = (round(w), round(h), round(pitch, 3), round(jitter, 3), seed, extra)
    pts = _GRIDS.get(key)
    if pts is None:
        rnd = random.Random(seed)
        pts = []
        y = -extra
        while y < h + extra + pitch:
            x = -extra
            while x < w + extra + pitch:
                pts.append((x + rnd.uniform(-jitter, jitter), y + rnd.uniform(-jitter, jitter), rnd.random(),
                            rnd.uniform(0, 2 * math.pi), rnd.uniform(1.5, 3.5)))
                x += pitch
            y += pitch
        if len(_GRIDS) > 32:
            _GRIDS.clear()
        _GRIDS[key] = pts
    return pts


def bands(cv, pts, colours, height, offset=0.0):
    """Horizontal bands of `colours` (cycling, `height` px each, shifted down
    by `offset`) inside the polygon `pts`: stripes on a tower, blocks on a
    building."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    with clip_to(cv, pts):
        k = int(math.floor((y0 - offset) / height))
        y = k * height + offset
        while y < y1:
            cv.rect(x0 - 1, y, x1 - x0 + 2, height, colours[k % len(colours)])
            y += height
            k += 1


class Turns:
    """Hands each region its fill from its role's palette in turn
    (`palettes`: role -> fills). A thin part -- narrower than `thin` px
    either way, such as a rail or a trim -- gets its role's `trims` colour
    instead, without using up a turn, so a second building gets the next
    full colour rather than the trim's."""

    def __init__(self, palettes, trims=None, thin=0.0):
        self.palettes, self.trims, self.thin = palettes, trims or {}, thin
        self.seen = {}

    def __call__(self, region):
        _, _, w, h = region.bbox
        if region.role in self.trims and min(w, h) < self.thin:
            return self.trims[region.role]
        k = self.seen.get(region.role, 0)
        self.seen[region.role] = k + 1
        fills = self.palettes[region.role]
        return fills[k % len(fills)]


def warp(pts, fn):
    return [fn(x, y) for x, y in pts]
