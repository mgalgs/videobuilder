"""N-body gravity: a handful of heavy bodies pull on each other and on a
cloud of light specks, so they swing round one another in looping orbits,
slingshot past on close encounters and drag their dust along with them."""
import math
import random

from .. import _demo as demo
from ..schema import Technique


def body(x, y, vx=0.0, vy=0.0, mass=0.0):
    """One body for `simulate`: position (px), velocity (px/s) and `mass`.
    A body of mass 0 is a test particle: gravity moves it, but it pulls on nothing."""
    return dict(x=x, y=y, vx=vx, vy=vy, mass=mass)


def circular(around, r, angle, spin=1, g=1.0, mass=0.0):
    """A body of `mass` at distance `r` and `angle` from `around`, moving at
    the speed of a circular orbit about it (plus `around`'s own velocity)."""
    v = math.sqrt(g * around['mass'] / r) * spin
    return body(around['x'] + r * math.cos(angle), around['y'] + r * math.sin(angle),
                around['vx'] - v * math.sin(angle), around['vy'] + v * math.cos(angle), mass)


def simulate(bodies, seconds, fps=30, g=1.0, soft=12.0, substeps=8):
    """Run the bodies forward under their mutual gravity: every body with mass
    pulls on every other body with force `g * m1 * m2 / (d^2 + soft^2)`.
    Returns one list per frame (`seconds * fps + 1` frames, frame 0 the
    start) of `(x, y)` per body, in `bodies`' order. Leapfrog integration,
    `substeps` steps per frame; `soft` (px) keeps close passes finite.
    Deterministic: the same bodies give the same paths, so simulate once and
    index the result by frame."""
    xs = [b['x'] for b in bodies]
    ys = [b['y'] for b in bodies]
    vxs = [b['vx'] for b in bodies]
    vys = [b['vy'] for b in bodies]
    heavy = [(i, b['mass']) for i, b in enumerate(bodies) if b['mass'] > 0]
    s2 = soft * soft
    dt = 1.0 / (fps * substeps)

    def accel():
        ax, ay = [0.0] * len(xs), [0.0] * len(xs)
        for j, m in heavy:
            xj, yj = xs[j], ys[j]
            for i in range(len(xs)):
                if i == j:
                    continue
                dx, dy = xj - xs[i], yj - ys[i]
                d2 = dx * dx + dy * dy + s2
                f = g * m / (d2 * math.sqrt(d2))
                ax[i] += f * dx
                ay[i] += f * dy
        return ax, ay

    out = [list(zip(xs, ys))]
    ax, ay = accel()
    for _ in range(round(seconds * fps)):
        for _ in range(substeps):
            for i in range(len(xs)):
                vxs[i] += ax[i] * dt / 2
                vys[i] += ay[i] * dt / 2
                xs[i] += vxs[i] * dt
                ys[i] += vys[i] * dt
            ax, ay = accel()
            for i in range(len(xs)):
                vxs[i] += ax[i] * dt / 2
                vys[i] += ay[i] * dt / 2
        out.append(list(zip(xs, ys)))
    return out


def draw_bodies(cv, frames, n, radii, colors, trail=12, trail_alpha=0.5):
    """Draw frame `n` of a `simulate` result: each body a dot of its radius and
    colour, with a fading trail of its last `trail` frames behind it. Bodies
    with radius 0 are skipped."""
    n = max(0, min(n, len(frames) - 1))
    start = max(0, n - trail)
    for i, (r, color) in enumerate(zip(radii, colors)):
        if r <= 0:
            continue
        path = [frames[k][i] for k in range(start, n + 1)]
        for k in range(1, len(path)):
            a = trail_alpha * k / len(path)
            cv.line(*path[k - 1], *path[k], color, width=max(1.0, r * 0.6), alpha=a)
        demo.dot(cv, *path[-1], r, color)


def _scene():
    k = 1.3                                   # time scale: g * k^2 and velocities * k run the same paths faster
    g = 2.0e5 * k * k
    # Three unequal suns, momentum balanced about the frame centre, on a bound
    # tangle that brings two of them close mid-way.
    suns = [body(600, 230, 22.7 * k, 34.6 * k, 1.0), body(374, 387, -82.6 * k, -56.7 * k, 0.8),
            body(416, 174, 79.0 * k, 19.6 * k, 0.6)]
    rnd = random.Random('n-body')
    dust = [circular(s, rnd.uniform(22, 50), rnd.uniform(0, 2 * math.pi), g=g)
            for s in suns for _ in range(24)]
    comet = body(-20, demo.H - 60, 260, -150)
    bodies = suns + dust + [comet]
    radii = [17, 15, 12] + [2.2] * len(dust) + [5]
    colors = ['#f2c14e', demo.ACCENT, demo.TEAL] + ['#a9b3ff'] * len(dust) + [demo.INK]
    return simulate(bodies, demo.SECONDS, demo.FPS, g=g), radii, colors


_SCENE = None


def draw(n, cv):
    global _SCENE
    if _SCENE is None:
        _SCENE = _scene()
    frames, radii, colors = _SCENE
    draw_bodies(cv, frames, n, radii, colors, trail=14)
    for i in range(3):
        x, y = frames[min(n, len(frames) - 1)][i]
        cv.mark(f'body{i}', x - radii[i], y - radii[i], 2 * radii[i], 2 * radii[i])


TECHNIQUE = Technique(
    id='n-body-gravity',
    name='N-body gravity',
    family='particles',
    group='Space',
    aliases=('gravitational n-body', 'orbital simulation', 'n-body simulation'),
    definition='Several masses all tug on one another at once, so they loop around each other, '
               'whip past on near misses and drag smaller particles into swirling orbits.',
    phrasings=('a few planets pulling on each other and swinging around chaotically',
               'simulate stars attracting each other with little particles orbiting them',
               'bodies in space that orbit and slingshot off each other by gravity'),
    related=('gravity-well-attraction', 'orbit', 'elastic-collisions', 'orbiting-characters', 'gravity-drop',
             'orbit-loader'),
    api=('videobuilder.techniques.particles.n_body_gravity.simulate',
         'videobuilder.techniques.particles.n_body_gravity.body',
         'videobuilder.techniques.particles.n_body_gravity.circular',
         'videobuilder.techniques.particles.n_body_gravity.draw_bodies'),
    demo=lambda: demo.film(draw),
)
