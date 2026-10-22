"""Lotka-Volterra cycles: two crowds of particles, prey and predators, whose
numbers swell and crash out of step -- prey boom, predators follow, prey
collapse, predators starve -- driven by the classic predator-prey equations."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def lotka_volterra(t, prey=10.0, predators=10.0, growth=1.1, predation=0.4, conversion=0.1, death=0.4,
                   dt=0.01):
    """The (prey, predators) populations at model time `t`, starting from
    `prey` and `predators` at 0. Prey grow at `growth` and are eaten at
    `predation` per encounter; predators gain `conversion` per encounter and
    die off at `death`. Integrated with fixed-step RK4 of size `dt`."""
    def rate(x, y):
        return growth * x - predation * x * y, conversion * x * y - death * y

    x, y = float(prey), float(predators)
    steps = max(0, round(t / dt))
    h = t / steps if steps else 0.0
    for _ in range(steps):
        k1 = rate(x, y)
        k2 = rate(x + h / 2 * k1[0], y + h / 2 * k1[1])
        k3 = rate(x + h / 2 * k2[0], y + h / 2 * k2[1])
        k4 = rate(x + h * k3[0], y + h * k3[1])
        x += h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        y += h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
    return x, y


def lotka_volterra_series(duration, samples, **kw):
    """`samples` evenly spaced (prey, predators) pairs over model time 0 ->
    `duration`, for driving a film frame by frame (index by progress). `kw`
    passes through to `lotka_volterra`."""
    dt = kw.pop('dt', 0.01)
    out, x, y = [], kw.pop('prey', 10.0), kw.pop('predators', 10.0)
    step = duration / max(1, samples - 1)
    for i in range(samples):
        out.append((x, y))
        x, y = lotka_volterra(step, x, y, dt=dt, **kw)
    return out


def population_particles(cv, count, slots, box, t, color, r=3.5, alpha=1.0):
    """Draw `count` of a population's `slots` (fixed per-particle seeds from
    `slots_for`) drifting inside `box` (x, y, w, h) at time `t` seconds. Slot
    `i` shows when `count > i`, fading in over its last unit, so the crowd
    thickens and thins smoothly as the count moves."""
    x0, y0, w, h = box
    for i, (u, v, a, sp, ph) in enumerate(slots):
        vis = vb.clamp01(count - i)
        if vis <= 0:
            continue
        px = x0 + ((u + sp * math.cos(a) * t + 0.012 * math.sin(2.3 * t + ph)) % 1.0) * w
        py = y0 + ((v + sp * math.sin(a) * t + 0.012 * math.cos(1.9 * t + ph)) % 1.0) * h
        demo.dot(cv, px, py, r * (0.4 + 0.6 * vis), color=color, alpha=alpha * vis)


def slots_for(n, seed, speed=0.03):
    """`n` particle seeds for `population_particles`: position, heading,
    drift speed (fraction of the box per second) and wobble phase."""
    rnd = random.Random(seed)
    return [(rnd.random(), rnd.random(), rnd.uniform(0, 2 * math.pi), speed * rnd.uniform(0.5, 1.5),
             rnd.uniform(0, 2 * math.pi)) for _ in range(n)]


PREY, PRED = demo.TEAL, demo.ACCENT
SAMPLES = round(demo.SECONDS * demo.FPS)
SERIES = lotka_volterra_series(18.0, SAMPLES, prey=6.0, predators=1.5)  # nearly two full cycles
TOP = (max(x for x, _ in SERIES), max(y for _, y in SERIES))  # each population scaled to its own peak
MAX_PREY, MAX_PRED = 460, 170
PREY_SLOTS, PRED_SLOTS = slots_for(MAX_PREY, 1), slots_for(MAX_PRED, 2, speed=0.06)
FIELD = (40, 24, demo.W - 80, 316)
CHART = (60, 410, demo.W - 120, 100)


def draw(n, cv):
    t = n / demo.FPS
    prey, pred = SERIES[min(n, SAMPLES - 1)]
    population_particles(cv, MAX_PREY * prey / TOP[0], PREY_SLOTS, FIELD, t, PREY, r=3.2)
    population_particles(cv, MAX_PRED * pred / TOP[1], PRED_SLOTS, FIELD, t, PRED, r=4.6)
    cv.mark('field', *FIELD)

    cx, cy, cw, ch = CHART
    cv.line(cx, cy + ch, cx + cw, cy + ch, demo.LINE, width=2)
    upto = min(n, SAMPLES - 1)
    for k, color in ((0, PREY), (1, PRED)):
        c = cv.ctx
        c.new_path()
        for i in range(upto + 1):
            px = cx + cw * i / (SAMPLES - 1)
            py = cy + ch - ch * SERIES[i][k] / TOP[k]
            (c.line_to if i else c.move_to)(px, py)
        c.set_source_rgba(*vb.canvas.rgba(color))
        c.set_line_width(3)
        c.stroke()
        demo.dot(cv, cx + cw * upto / (SAMPLES - 1), cy + ch - ch * SERIES[upto][k] / TOP[k], 6, color=color)
    f = demo.font(18, 700)
    vb.text.draw(cv, ['prey'], f, cx, cy - 40, PREY)
    vb.text.draw(cv, ['predators'], f, cx + 70, cy - 40, PRED)
    cv.mark('chart', *CHART)


TECHNIQUE = Technique(
    id='lotka-volterra-cycles',
    name='Lotka-Volterra cycles',
    family='particles',
    group='Swarms & agents',
    aliases=('predator-prey dynamics', 'population cycles', 'predator-prey cycles'),
    definition='Two crowds of drifting particles, prey and predators, that swell and thin out in '
               'repeating waves, the predators always peaking just after the prey they feed on.',
    phrasings=('show predators and prey booming and crashing in turn',
               'two populations of dots that rise and fall in a chasing cycle',
               'a predator-prey simulation where the hunters lag behind the hunted'),
    related=('voronoi-cells', 'pollen-drift', 'cyclic-cellular-automaton', 'day-night-cycle', 'hop-cycle',
             'voronoi-relaxation'),
    api=('videobuilder.techniques.particles.lotka_volterra_cycles.lotka_volterra',
         'videobuilder.techniques.particles.lotka_volterra_cycles.lotka_volterra_series',
         'videobuilder.techniques.particles.lotka_volterra_cycles.population_particles',
         'videobuilder.techniques.particles.lotka_volterra_cycles.slots_for'),
    demo=lambda: demo.film(draw),
)
