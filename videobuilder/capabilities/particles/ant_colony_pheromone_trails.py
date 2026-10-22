"""Ant colony pheromone trails: a swarm of simple agents wanders out of a nest,
and the ones that find food lay a fading scent on the way home that the others
follow, so glowing trails grow between the nest and each food source."""
import functools
import math

import numpy as np
from PIL import Image as PILImage, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


class AntColony:
    """A seeded stigmergy simulation over a `width` x `height` px field.

    Ants leave `nest` searching; a searcher steers by three sensors (ahead,
    left, right) towards the strongest food scent, otherwise wanders. One that
    walks into a food source (`foods`: (x, y, radius) each) turns home,
    carrying a crumb, and deposits food scent as it goes, strongest near the
    food so the trail points the way. Searchers lay a faint home scent that
    carriers follow alongside their sense of the nest's direction. Both
    scents evaporate by `decay` and blur slightly each step, so trails that
    stop being walked fade out. `cell` is the scent grid's pitch in px;
    `speed` is px per step; `follow` the chance a sensing ant heeds the scent
    on a given step.
    """

    def __init__(self, width, height, nest, foods, ants=260, speed=5.0, cell=4, decay=0.988,
                 nest_radius=18.0, follow=0.8, seed=1):
        self.width, self.height, self.cell = width, height, cell
        self.nest, self.nest_radius = np.array(nest, float), nest_radius
        self.foods = np.array(foods, float).reshape(-1, 3)
        self.speed, self.decay, self.follow = speed, decay, follow
        self.rng = np.random.default_rng(seed)
        gw, gh = math.ceil(width / cell), math.ceil(height / cell)
        self.food_scent = np.zeros((gh, gw))   # laid by carriers: "food this way"
        self.home_scent = np.zeros((gh, gw))   # laid by searchers: "nest this way"
        self.heading = self.rng.uniform(0, 2 * math.pi, ants)
        self.pos = self.nest + np.stack([np.cos(self.heading), np.sin(self.heading)], 1) * nest_radius
        self.carrying = np.zeros(ants, bool)
        self.since = np.zeros(ants)             # steps since leaving nest or food
        self.launch = self.rng.uniform(0, 30, ants)  # stagger the spill out of the nest
        self.t = 0

    def _sample(self, field, xy):
        gx = np.clip((xy[:, 0] / self.cell).astype(int), 0, field.shape[1] - 1)
        gy = np.clip((xy[:, 1] / self.cell).astype(int), 0, field.shape[0] - 1)
        return field[gy, gx]

    def _deposit(self, field, xy, amount):
        gx = np.clip((xy[:, 0] / self.cell).astype(int), 0, field.shape[1] - 1)
        gy = np.clip((xy[:, 1] / self.cell).astype(int), 0, field.shape[0] - 1)
        np.add.at(field, (gy, gx), amount)

    def step(self):
        """Advance one simulation step."""
        rng, n = self.rng, len(self.heading)
        active = self.launch <= self.t
        reach, spread = self.speed * 3.5, 0.55
        sensed = []
        for da in (-spread, 0.0, spread):
            a = self.heading + da
            probe = self.pos + np.stack([np.cos(a), np.sin(a)], 1) * reach
            sensed.append(np.where(self.carrying, self._sample(self.home_scent, probe),
                                   self._sample(self.food_scent, probe)))
        left, ahead, right = sensed
        turn = np.where((left > ahead) & (left > right), -0.35, 0.0)
        turn = np.where((right > ahead) & (right > left), 0.35, turn)
        turn *= rng.random(n) < self.follow  # the rest of the time, explore
        self.heading += turn + rng.normal(0, 0.22, n)
        # Carriers also know roughly where home is.
        to_nest = np.arctan2(self.nest[1] - self.pos[:, 1], self.nest[0] - self.pos[:, 0])
        off = (to_nest - self.heading + math.pi) % (2 * math.pi) - math.pi
        self.heading += np.where(self.carrying, 0.18 * off, 0.0)
        step = np.stack([np.cos(self.heading), np.sin(self.heading)], 1) * self.speed
        self.pos += step * active[:, None]
        # Walls turn ants back in.
        for k, hi in ((0, self.width), (1, self.height)):
            out = (self.pos[:, k] < 4) | (self.pos[:, k] > hi - 4)
            self.pos[:, k] = np.clip(self.pos[:, k], 4, hi - 4)
            if k == 0:
                self.heading = np.where(out, math.pi - self.heading, self.heading)
            else:
                self.heading = np.where(out, -self.heading, self.heading)
        self.since += active
        strength = np.exp(-self.since / 120)
        self._deposit(self.food_scent, self.pos[self.carrying & active], strength[self.carrying & active])
        self._deposit(self.home_scent, self.pos[~self.carrying & active],
                      0.25 * strength[~self.carrying & active])
        for fx, fy, fr in self.foods:
            found = ~self.carrying & (np.hypot(self.pos[:, 0] - fx, self.pos[:, 1] - fy) < fr)
            self.carrying |= found
            self.heading = np.where(found, self.heading + math.pi, self.heading)
            self.since = np.where(found, 0, self.since)
        home = self.carrying & (np.hypot(*(self.pos - self.nest).T) < self.nest_radius)
        self.carrying &= ~home
        self.heading = np.where(home, self.heading + math.pi, self.heading)
        self.since = np.where(home, 0, self.since)
        for f in (self.food_scent, self.home_scent):
            f *= self.decay
            near = np.roll(f, 1, 0) + np.roll(f, -1, 0) + np.roll(f, 1, 1) + np.roll(f, -1, 1)
            f[:] = 0.6 * f + 0.1 * near
        self.t += 1

    def snapshot(self):
        """(positions, headings, carrying, food scent): copies, for drawing later."""
        return self.pos.copy(), self.heading.copy(), self.carrying.copy(), self.food_scent.copy()


def colony_frames(frames, substeps=4, **kw):
    """Run an `AntColony(**kw)` for `frames` frames of `substeps` steps each and
    return one snapshot per frame, cached by arguments so any frame can be
    drawn in any order. `kw` values must be hashable (tuples, not lists)."""
    return _colony_frames(frames, substeps, tuple(sorted(kw.items())))


@functools.lru_cache(maxsize=8)
def _colony_frames(frames, substeps, kw):
    colony = AntColony(**dict(kw))
    out = []
    for _ in range(frames):
        for _ in range(substeps):
            colony.step()
        out.append(colony.snapshot())
    return tuple(out)


def draw_pheromone(cv, scent, width, height, color=demo.TEAL, level=4.0, glow=1.2):
    """Draw a scent grid over (0, 0, width, height) as a soft glow in `color`,
    fully opaque where the scent reaches `level`."""
    a = np.clip(scent / level, 0, 1) ** 0.6
    r, g, b, _ = vb.rgba(color)
    rgba = np.zeros(a.shape + (4,), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = round(r * 255), round(g * 255), round(b * 255)
    rgba[..., 3] = (a * 235).astype(np.uint8)
    pil = PILImage.fromarray(rgba, 'RGBA').filter(ImageFilter.GaussianBlur(glow))
    cv.image(vb.Image.from_pil(pil), 0, 0, width, height)


def draw_ants(cv, snapshot, length=6, idle=demo.MUTED, carrying=demo.ACCENT):
    """Draw each ant of a `snapshot` as a short dash along its heading:
    searchers in `idle`, food carriers in `carrying` with a crumb at the front."""
    pos, heading, carry, _ = snapshot
    for (x, y), a, c in zip(pos, heading, carry):
        dx, dy = math.cos(a) * length / 2, math.sin(a) * length / 2
        cv.line(x - dx, y - dy, x + dx, y + dy, carrying if c else idle, width=2, alpha=1.0 if c else 0.7)
        if c:
            demo.dot(cv, x + dx, y + dy, r=2, color=carrying)


NEST = (140.0, 270.0)
FOODS = ((700.0, 105.0, 36.0), (745.0, 270.0, 36.0), (700.0, 435.0, 36.0))


def draw(n, cv):
    snaps = colony_frames(demo.FPS * 3, width=demo.W, height=demo.H, nest=NEST, foods=FOODS)
    snap = snaps[n]
    draw_pheromone(cv, snap[3], demo.W, demo.H)
    for fx, fy, fr in FOODS:
        demo.dot(cv, fx, fy, r=fr * 0.75, color=demo.ACCENT, alpha=0.12)
        for i in range(7):
            a = i * 2 * math.pi / 7 + fx
            demo.dot(cv, fx + 11 * math.cos(a) * (i > 0), fy + 11 * math.sin(a) * (i > 0), r=4.5,
                     color=demo.ACCENT)
        cv.mark('food', fx - fr, fy - fr, 2 * fr, 2 * fr)
    nx, ny = NEST
    demo.dot(cv, nx, ny, r=18, color=demo.LINE)
    cv.arc(nx, ny, 22, 0, 2 * math.pi, demo.INK, width=2, alpha=0.8)
    cv.mark('nest', nx - 22, ny - 22, 44, 44)
    draw_ants(cv, snap)


CAPABILITY = Capability(
    id='ant-colony-pheromone-trails',
    name='Ant colony pheromone trails',
    family='particles',
    group='Swarms & agents',
    aliases=('ant trails', 'stigmergy trails', 'ant colony simulation', 'pheromone trails'),
    definition='Many tiny wandering agents leave a fading scent wherever they carry food home, and the '
               'rest follow the strongest scent, so bright paths emerge between a nest and its food.',
    phrasings=('ants scattering from a nest and slowly forming glowing paths to the food',
               'a swarm simulation where little bugs lay trails that the others follow',
               'show the trails building up between the colony and the food piles'),
    related=('dashed-line-march', 'particle-trail', 'fireflies', 'langton-s-ant', 'cursor-particle-trail',
             'echo-trail-type'),
    api=('videobuilder.capabilities.particles.ant_colony_pheromone_trails.AntColony',
         'videobuilder.capabilities.particles.ant_colony_pheromone_trails.colony_frames',
         'videobuilder.capabilities.particles.ant_colony_pheromone_trails.draw_pheromone',
         'videobuilder.capabilities.particles.ant_colony_pheromone_trails.draw_ants'),
    demo=lambda: demo.film(draw),
)
