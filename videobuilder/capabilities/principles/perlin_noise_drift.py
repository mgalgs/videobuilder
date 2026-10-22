"""Perlin Noise Drift: a thing wanders on its own, its position (or angle, or
scale) read from smooth gradient noise over time, so it floats about in slow,
unrepeating curves rather than moving in straight lines or a loop."""
import math
import random

from .. import _demo as demo
from ..schema import Capability


def _gradients(seed, count=256):
    rnd = random.Random(f'perlin:{seed}')
    return [rnd.uniform(-1, 1) for _ in range(count)]


_CACHE = {}


def perlin1d(t, seed=0):
    """1-D Perlin (gradient) noise at `t`, roughly in [-1, 1]: a random slope
    at every integer, blended with the quintic fade, so it is smooth, passes
    through 0 at each integer and repeats only after 256 units. The same
    `seed` gives the same curve."""
    g = _CACHE.get(seed)
    if g is None:
        g = _CACHE[seed] = _gradients(seed)
    i = math.floor(t)
    f = t - i
    a = g[i % 256] * f
    b = g[(i + 1) % 256] * (f - 1)
    u = f * f * f * (f * (f * 6 - 15) + 10)
    return 2 * (a + (b - a) * u)


def noise_drift(t, seed=0, amount=1.0, speed=1.0, octaves=2):
    """Smooth wander at time `t` seconds, in [-`amount`, `amount`]: Perlin
    noise read at `t * speed`, with `octaves` layers each twice as fast and
    half as strong for a little fine detail. Use one seed per channel (x, y,
    rotation, ...) and per object so each drifts on its own."""
    total, norm, freq, amp = 0.0, 0.0, speed, 1.0
    for k in range(octaves):
        total += amp * perlin1d(t * freq + 17.3 * k, seed=f'{seed}:{k}')
        norm += amp
        freq, amp = freq * 2, amp / 2
    return amount * max(-1.0, min(1.0, total / norm))


def drift_xy(t, seed=0, amount=40.0, speed=0.6, octaves=2):
    """An (dx, dy) offset in pixels drifting on smooth noise: add it to an
    object's resting position to make it float about."""
    return (noise_drift(t, f'{seed}:x', amount, speed, octaves),
            noise_drift(t, f'{seed}:y', amount, speed, octaves))


DOTS = ((-300, -140, demo.TEAL), (300, 140, demo.TEAL), (-290, 150, demo.MUTED), (310, -150, demo.MUTED))

SPEED = 0.8


def draw(n, cv):
    t = 4.3 + n / demo.FPS  # start mid-wander, not at the noise's zero crossing
    cx, cy = demo.W / 2, demo.H / 2
    trail = 2.0  # seconds of path shown behind each mover
    movers = [(cx, cy, 'card', 220, demo.ACCENT)] + [(cx + x, cy + y, i, 170, c) for i, (x, y, c) in enumerate(DOTS)]
    for x0, y0, seed, amount, color in movers:
        cv.sector(x0, y0, 5, 0, 2 * math.pi, demo.LINE)  # the rest position it wanders around
        steps = 40
        pts = [drift_xy(t - trail * (1 - k / steps), seed, amount, SPEED) for k in range(steps + 1)]
        for k in range(steps):
            (ax, ay), (bx, by) = pts[k], pts[k + 1]
            cv.line(x0 + ax, y0 + ay, x0 + bx, y0 + by, color, width=5, alpha=0.5 * (k + 1) / steps)
    for x0, y0, seed, amount, color in movers[1:]:
        dx, dy = drift_xy(t, seed, amount, SPEED)
        demo.dot(cv, x0 + dx, y0 + dy, 26, color=color)
    dx, dy = drift_xy(t, 'card', 220, SPEED)
    demo.card(cv, cx + dx, cy + dy)


CAPABILITY = Capability(
    id='perlin-noise-drift',
    name='Perlin Noise Drift',
    family='principles',
    group='Physics',
    aliases=('noise drift', 'wiggle', 'organic drift', 'random float'),
    definition='Objects float around their resting spot along smooth, never-repeating wandering paths '
               'driven by noise, as if carried by a gentle current.',
    phrasings=('make it float around a bit on its own, organically',
               'give the shapes a slow random wander so they feel alive',
               'have the elements drift lazily like they are underwater'),
    related=('perlin-noise-field', 'fractal-brownian-motion', 'turbulence-displacement', 'wiggle-path',
             'noise-vertex-wobble', 'gradient-mesh-drift'),
    api=('videobuilder.capabilities.principles.perlin_noise_drift.drift_xy',
         'videobuilder.capabilities.principles.perlin_noise_drift.noise_drift',
         'videobuilder.capabilities.principles.perlin_noise_drift.perlin1d'),
    demo=lambda: demo.film(draw),
)
