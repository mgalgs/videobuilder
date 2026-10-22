"""Gravity Well Attraction: a field of particles is pulled toward one point,
speeding up as it falls in, swirling round it and spiralling down into it."""
import math
import random
from functools import lru_cache

from .. import _demo as demo
from ..schema import Technique


@lru_cache(maxsize=8)
def gravity_well(well, count=160, frames=90, fps=30, seed=0, inner=120.0, outer=480.0, strength=2.4e7,
                 swirl=0.7, drag=0.6, soften=40.0, capture=14.0, substeps=4):
    """Paths of `count` particles falling into a well at `well` (x, y), one
    position per frame for `frames` frames: a tuple per particle of `(x, y)`,
    or `None` once it has been swallowed (closer than `capture`).

    Particles start scattered in a ring between `inner` and `outer` from the
    well, nearly at rest, with a little sideways speed (`swirl`, as a share of
    circular-orbit speed) so they curve into orbit rather than fall straight
    in. The pull is `strength / (r^2 + soften^2)`; `drag` (per second) bleeds
    their energy so the orbits tighten and collapse into the centre. The same
    arguments give the same paths, so a film can call this on every frame."""
    rng = random.Random(seed)
    wx, wy = well
    dt = 1.0 / (fps * substeps)
    state = []
    for _ in range(count):
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.uniform(inner * inner, outer * outer))  # even over the ring's area
        v = swirl * math.sqrt(strength / r) * rng.uniform(0.6, 1.3)
        state.append([wx + r * math.cos(a), wy + r * math.sin(a), -v * math.sin(a), v * math.cos(a)])
    paths = [[] for _ in range(count)]
    for _ in range(frames):
        for i, s in enumerate(state):
            if s is None:
                paths[i].append(None)
                continue
            paths[i].append((s[0], s[1]))
            for _ in range(substeps):
                dx, dy = wx - s[0], wy - s[1]
                d2 = dx * dx + dy * dy
                d = math.sqrt(d2) or 1e-9
                acc = strength / (d2 + soften * soften)
                s[2] += (acc * dx / d - drag * s[2]) * dt
                s[3] += (acc * dy / d - drag * s[3]) * dt
                s[0] += s[2] * dt
                s[1] += s[3] * dt
            if math.hypot(wx - s[0], wy - s[1]) < capture:
                state[i] = None
    return tuple(tuple(p) for p in paths)


def draw_gravity_well(cv, paths, n, well, color=demo.INK, trail=8, r=4.0, core=demo.ACCENT, core_r=16.0):
    """Draw frame `n` of `paths` (from `gravity_well`): each particle as a dot
    with a fading streak over its last `trail` frames, then the well itself as
    a glowing `core` at `well`."""
    for path in paths:
        if n >= len(path) or path[n] is None:
            continue
        pts = [p for p in path[max(0, n - trail):n + 1] if p is not None]
        for k in range(1, len(pts)):
            cv.line(*pts[k - 1], *pts[k], color, width=max(1.0, r * 0.5), alpha=0.35 * k / len(pts))
        demo.dot(cv, *pts[-1], r, color=color)
    wx, wy = well
    for k, alpha in ((3.2, 0.08), (2.2, 0.16), (1.5, 0.3)):
        demo.dot(cv, wx, wy, core_r * k, color=core, alpha=alpha)
    demo.dot(cv, wx, wy, core_r, color=core)
    cv.arc(wx, wy, core_r * 1.6, 0, 2 * math.pi, core, width=3)


WELL = (demo.W / 2, demo.H / 2)
FRAMES = round(demo.SECONDS * demo.FPS)


def draw(n, cv):
    paths = gravity_well(WELL, count=180, frames=FRAMES, fps=demo.FPS, seed=3)
    draw_gravity_well(cv, paths, n, WELL, color=demo.INK)
    cv.mark('well', WELL[0] - 16, WELL[1] - 16, 32, 32)


TECHNIQUE = Technique(
    id='gravity-well-attraction',
    name='Gravity well attraction',
    family='particles',
    group='Forces',
    aliases=('attractor', 'magnet attraction', 'gravity well'),
    definition='A scatter of particles is drawn toward a single point, gathering speed as it nears, '
               'whirling round it and spiralling down into the centre.',
    phrasings=('the dots get sucked into the middle like water down a drain',
               'particles swirl in toward a glowing point and vanish into it',
               'a little black hole pulling everything around it inward'),
    related=('magnetic-snap', 'n-body-gravity', 'hopalong-attractor', 'gravity-drop', 'lorenz-attractor',
             'rossler-attractor'),
    api=('videobuilder.techniques.particles.gravity_well_attraction.gravity_well',
         'videobuilder.techniques.particles.gravity_well_attraction.draw_gravity_well'),
    demo=lambda: demo.film(draw),
)
