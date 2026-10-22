"""Curl noise flow: particles carried by the curl of a smooth noise field, a
velocity field with no sources or sinks, so they swirl round slow eddies and
along winding currents while staying evenly spread, like stirred smoke or ink.

The field is the 2-D curl of a scalar noise "stream function" psi: velocity
is (d psi / dy, -d psi / dx), which is divergence-free by construction. The
noise drifts through a third (time) axis so the eddies slowly reshape."""
import math
import random
from functools import lru_cache

from ...canvas import rgba
from .. import _demo as demo
from ..schema import Capability


_GRADS = ((1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0), (1, 0, 1), (-1, 0, 1), (1, 0, -1), (-1, 0, -1),
          (0, 1, 1), (0, -1, 1), (0, 1, -1), (0, -1, -1))


def _grad(i, j, k, seed):
    """A deterministic gradient (one of the 12 cube edges) for lattice point (i, j, k)."""
    h = (i * 374761393 + j * 668265263 + k * 1440662683 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return _GRADS[(h ^ (h >> 16)) % 12]


def _fade(f):
    """Quintic fade and its derivative, so the noise has smooth slopes."""
    return f * f * f * (f * (f * 6 - 15) + 10), 30 * f * f * (f * (f - 2) + 1)


def noise3(u, v, w, seed=0):
    """Smooth 3-D gradient (Perlin) noise at (u, v, w), roughly in [-1, 1],
    with its exact partial derivatives along `u` and `v`: returns
    (value, d/du, d/dv)."""
    i, j, k = math.floor(u), math.floor(v), math.floor(w)
    fx, fy, fz = u - i, v - j, w - k
    sx, dsx = _fade(fx)
    sy, dsy = _fade(fy)
    sz, _ = _fade(fz)
    val = du = dv = 0.0
    for cx in (0, 1):
        wx, dwx = (sx, dsx) if cx else (1 - sx, -dsx)
        for cy in (0, 1):
            wy, dwy = (sy, dsy) if cy else (1 - sy, -dsy)
            for cz in (0, 1):
                wz = sz if cz else 1 - sz
                gx, gy, gz = _grad(i + cx, j + cy, k + cz, seed)
                dot = gx * (fx - cx) + gy * (fy - cy) + gz * (fz - cz)
                val += wx * wy * wz * dot
                du += wz * (dwx * wy * dot + wx * wy * gx)
                dv += wz * (wx * dwy * dot + wx * wy * gy)
    return val, du, dv


def curl_noise(x, y, t=0.0, seed=0, scale=260.0, speed=0.25, strength=140.0, octaves=2):
    """The curl-noise velocity at pixel (x, y) and time `t` seconds, in px per
    second, as (vx, vy). `scale`: px across one noise cell (the eddy size).
    `speed`: how fast the field reshapes. `strength`: roughly the typical
    speed. `octaves`: layers of finer, weaker eddies on top. The field is
    divergence-free, so anything it carries neither clumps nor thins out."""
    dpx = dpy = norm = 0.0
    freq, amp = 1.0 / scale, 1.0
    for o in range(octaves):
        _, du, dv = noise3(x * freq + 31.7 * o, y * freq - 17.3 * o, t * speed * (1 + o), seed + o)
        dpx += amp * du
        dpy += amp * dv
        norm += amp
        freq, amp = freq * 2, amp * 0.5
    s = strength / norm
    return dpy * s, -dpx * s


def flow_tracks(count, seconds, bounds, fps=30, substeps=2, seed=0, **field):
    """Advect `count` particles through `curl_noise` for `seconds`, starting
    from seeded random spots spread evenly inside `bounds` (x, y, w, h).
    Returns one track per particle: a list of (x, y) per frame, `fps` frames a
    second, with `None` where the particle wrapped round an edge (re-entering
    on the far side so the field stays full). `field` goes to `curl_noise`.
    Deterministic for a given `seed`; integrate once, then draw any frame."""
    bx, by, bw, bh = bounds
    rnd = random.Random(f'curl:{seed}')
    cols = max(1, round(math.sqrt(count * bw / bh)))
    rows = math.ceil(count / cols)
    pts = []
    for n in range(count):  # jittered grid: even coverage from the first frame
        c, r = n % cols, n // cols
        pts.append([bx + (c + rnd.random()) * bw / cols, by + (r + rnd.random()) * bh / rows])
    tracks = [[(x, y)] for x, y in pts]
    dt = 1.0 / (fps * substeps)
    frames = round(seconds * fps)
    for f in range(frames):
        for s in range(substeps):
            t = (f * substeps + s) * dt
            for p, track in zip(pts, tracks):
                x, y = p
                vx, vy = curl_noise(x, y, t, seed, **field)  # midpoint (RK2) step
                mx, my = curl_noise(x + vx * dt / 2, y + vy * dt / 2, t + dt / 2, seed, **field)
                x, y = x + mx * dt, y + my * dt
                if not (bx <= x < bx + bw and by <= y < by + bh):
                    x, y = bx + (x - bx) % bw, by + (y - by) % bh
                    track.append(None)
                p[0], p[1] = x, y
        for p, track in zip(pts, tracks):
            track.append((p[0], p[1]))
    return tracks


def draw_flow(cv, tracks, frame, tail=18, colors=(demo.INK,), width=1.6, alpha=0.85, seed=0):
    """Draw every track at `frame` as a streak through its last `tail` frames,
    fading towards the back, each in one of `colors` (picked by seed). Wraps
    (`None`) break the streak."""
    c = cv.ctx
    c.set_line_width(width)
    c.set_line_cap(1)  # round
    rnd = random.Random(f'flow-colors:{seed}')
    pieces = 3  # the streak is drawn as a few segments of rising opacity
    for track in tracks:
        color = rnd.choice(colors)
        end = _index(track, frame)
        start = _index(track, max(0, frame - tail))
        seg = track[start:end + 1]
        for k in range(pieces):
            part = seg[len(seg) * k // pieces:len(seg) * (k + 1) // pieces + 1]
            _stroke(c, part, rgba(color, alpha * (k + 1) / pieces))


def _index(track, frame):
    """Position in `track` of frame `frame`, skipping the `None` wrap markers."""
    seen = -1
    for i, p in enumerate(track):
        if p is not None:
            seen += 1
            if seen == frame:
                return i
    return len(track) - 1


def _stroke(c, pts, color):
    c.new_path()
    pen = False
    for p in pts:
        if p is None:
            pen = False
        elif pen:
            c.line_to(*p)
        else:
            c.move_to(*p)
            pen = True
    c.set_source_rgba(*color)
    c.stroke()


MARGIN = 260   # the flow runs past the frame so edge wraps happen off screen
WARMUP = 24    # frames simulated before the demo opens, so frame 0 already shows streaks


@lru_cache(maxsize=1)
def _demo_tracks():
    bounds = (-MARGIN, -MARGIN, demo.W + 2 * MARGIN, demo.H + 2 * MARGIN)
    return flow_tracks(1500, demo.SECONDS + WARMUP / demo.FPS, bounds, fps=demo.FPS, substeps=1, seed=7,
                       scale=320.0, strength=190.0, speed=0.3)


def draw(n, cv):
    draw_flow(cv, _demo_tracks(), n + WARMUP, tail=20,
              colors=(demo.INK, demo.INK, demo.TEAL, demo.ACCENT, demo.MUTED), width=2.0, seed=7)


CAPABILITY = Capability(
    id='curl-noise-flow',
    name='Curl noise flow',
    family='particles',
    group='Noise & fields',
    aliases=('divergence-free flow', 'curl field particles', 'curl noise', 'flow field particles'),
    definition='A dense field of particles streams along curling, eddying currents that never pile up '
               'or leave gaps, so the whole frame churns like stirred smoke or ink in water.',
    phrasings=('fill the screen with particles swirling around like smoke',
               'make thousands of little streaks flow in lazy whirlpools',
               'an inky, marbled flow where specks drift in curls without clumping'),
    related=('turbulence-displacement', 'smoke-simulation', 'smoke-puffs', 'swirl', 'wind-field', 'line-boil'),
    api=('videobuilder.capabilities.particles.curl_noise_flow.curl_noise',
         'videobuilder.capabilities.particles.curl_noise_flow.flow_tracks',
         'videobuilder.capabilities.particles.curl_noise_flow.draw_flow',
         'videobuilder.capabilities.particles.curl_noise_flow.noise3'),
    demo=lambda: demo.film(draw),
)
