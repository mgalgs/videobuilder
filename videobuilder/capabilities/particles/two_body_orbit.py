"""Two-body orbit: a small body swings round a heavy one on an ellipse, the
heavy one sitting at a focus, so the body dawdles at the far end and whips
through the near end (Kepler's equal areas in equal times)."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def kepler_orbit(cx, cy, a, e, t, period=1.0, phase=0.0, rotation=0.0, spin=1):
    """Where an orbiting body is at time `t`: `(x, y, speed)`. The heavy body
    sits at (cx, cy), one focus of an ellipse with semi-major axis `a` and
    eccentricity `e` (0 = circle, near 1 = long and thin). One lap takes
    `period` (in `t`'s units); `phase` is where the lap starts in turns of
    time (0 = closest approach, 0.5 = farthest point); `rotation` turns the
    ellipse (radians, 0 = closest approach to the right of the focus);
    `spin` is 1 or -1 for the direction. `speed` is the body's speed relative
    to its mean speed, about `(1 + e) / (1 - e)` at closest approach: use it
    to stretch a trail or brighten a glow."""
    m = 2 * math.pi * (t / period + phase)  # mean anomaly: uniform in time
    ea = m
    for _ in range(12):  # Newton's method on Kepler's equation E - e sin E = M
        ea -= (ea - e * math.sin(ea) - m) / (1 - e * math.cos(ea))
    b = a * math.sqrt(1 - e * e)
    px, py = a * (math.cos(ea) - e), spin * b * math.sin(ea)
    c, s = math.cos(rotation), math.sin(rotation)
    r = math.hypot(px, py)
    speed = math.sqrt(max(0.0, 2 * a / r - 1)) if r else 0.0
    return cx + px * c - py * s, cy + px * s + py * c, speed


def kepler_path(cx, cy, a, e, rotation=0.0, n=128):
    """The orbit's ellipse as points, for `vb.paths.draw(..., closed=True)`."""
    b = a * math.sqrt(1 - e * e)
    c, s = math.cos(rotation), math.sin(rotation)
    out = []
    for i in range(n):
        u = 2 * math.pi * i / n
        px, py = a * (math.cos(u) - e), b * math.sin(u)
        out.append((cx + px * c - py * s, cy + px * s + py * c))
    return out


A, E = 300, 0.7
STAR = (demo.W / 2 + A * E, demo.H / 2)  # the focus, so the ellipse sits centred in frame


def draw(n, cv):
    cx, cy = STAR
    t = n / demo.FPS
    pos = lambda tt: kepler_orbit(cx, cy, A, E, tt, period=demo.SECONDS, phase=0.5)  # noqa: E731
    vb.paths.draw(cv, kepler_path(cx, cy, A, E), demo.MUTED, width=2, closed=True, alpha=0.35)
    for k in range(6, 0, -1):  # the star's soft glow
        demo.dot(cv, cx, cy, 30 + 7 * k, color=demo.ACCENT, alpha=0.05)
    demo.dot(cv, cx, cy, 30, color=demo.ACCENT)
    cv.mark('star', cx - 30, cy - 30, 60, 60)
    trail = [pos(t - k * 0.012) for k in range(40)]  # a fixed time span: long when fast, short when slow
    for k in range(len(trail) - 1, 0, -1):
        (x0, y0, _), (x1, y1, _) = trail[k], trail[k - 1]
        cv.line(x0, y0, x1, y1, demo.TEAL, width=4 * (1 - k / 40), alpha=0.8 * (1 - k / 40))
    x, y, speed = trail[0]
    glow = min(1.0, speed / 3)
    demo.dot(cv, x, y, 14 + 8 * glow, color=demo.TEAL, alpha=0.25)
    demo.dot(cv, x, y, 9, color=demo.TEAL)
    cv.mark('planet', x - 9, y - 9, 18, 18)


CAPABILITY = Capability(
    id='two-body-orbit',
    name='Two-body orbit',
    family='particles',
    group='Space',
    aliases=('Kepler orbit', 'elliptical orbit'),
    definition='A small body loops round a heavier one on an oval path, drifting slowly at the far end '
               'and sweeping fast past the heavy body at the near end.',
    phrasings=('a planet going round the sun on a stretched loop, faster when it gets close',
               'make a moon swing around like real gravity, slow far away and quick up close',
               'an elliptical orbit that speeds up near the star'),
    related=('orbit', 'orbiting-characters', 'orbit-loader', 'orbital-pulse', 'orbit-shot', 'phyllotaxis'),
    api=('videobuilder.capabilities.particles.two_body_orbit.kepler_orbit',
         'videobuilder.capabilities.particles.two_body_orbit.kepler_path'),
    demo=lambda: demo.film(draw),
)
