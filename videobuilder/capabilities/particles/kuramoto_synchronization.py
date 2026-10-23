"""Kuramoto Synchronization: a crowd of oscillators, each ticking at its own
slightly different rate, pull on one another's timing until they fall into
step and flash as one."""
import functools
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

GLOW = '#f2d16b'


@functools.lru_cache(maxsize=16)
def _trajectory(count, seconds, coupling, seed, rate, spread, dt):
    rng = random.Random(seed)
    omega = [2 * math.pi * rng.gauss(rate, spread) for _ in range(count)]
    theta = [rng.uniform(0, 2 * math.pi) for _ in range(count)]
    out = [tuple(theta)]
    for step in range(round(seconds / dt)):
        k = coupling(step * dt) if callable(coupling) else coupling
        r, psi = order(theta)
        theta = [t + dt * (w + k * r * math.sin(psi - t)) for t, w in zip(theta, omega)]
        out.append(tuple(theta))
    return tuple(out)


def kuramoto(t, count=48, coupling=4.0, seed=0, rate=1.4, spread=0.18, seconds=4.0, dt=1 / 240):
    """The phases (radians, unwrapped) of `count` coupled oscillators at time
    `t` seconds. Each starts at a random phase with its own natural rate drawn
    around `rate` Hz (std `spread` Hz) and is nudged toward the group's mean
    phase with strength `coupling` -- a number, or a function of time so the
    pull can switch on partway. Integrated from 0 to `seconds` once and
    cached, so frames can be drawn in any order; the same `seed` gives the
    same crowd."""
    traj = _trajectory(count, seconds, coupling, seed, rate, spread, dt)
    i = min(len(traj) - 1, max(0, round(t / dt)))
    return traj[i]


def order(phases):
    """How in step `phases` are: `(r, psi)`, `r` from 0 (scattered) to 1
    (all together) and `psi` the mean phase."""
    x = sum(math.cos(p) for p in phases) / len(phases)
    y = sum(math.sin(p) for p in phases) / len(phases)
    return math.hypot(x, y), math.atan2(y, x)


def flash(phase, sharpness=6):
    """A firefly-like blink for one oscillator: 1 at the top of each cycle,
    falling quickly to 0 between."""
    return ((1 + math.cos(phase)) / 2) ** sharpness


COLS, ROWS = 10, 5


def _coupling(t):
    return 7.0 * vb.clamp01((t - 0.5) / 0.6)


def _phases(t):
    return kuramoto(t, count=COLS * ROWS, coupling=_coupling, seed=11, seconds=demo.SECONDS + 0.1)


# the gallery's poster is the frame at 70%; turn every clock by the same amount so
# the locked crowd's flash lands exactly there
POSTER_T = 0.7 * demo.SECONDS


def draw(n, cv):
    shift = -order(_phases(POSTER_T))[1]
    phases = [p + shift for p in _phases(n / demo.FPS)]
    # the swarm: a field of dots, each blinking on its own clock
    x0, y0, gap = 90, 130, 56
    for i, p in enumerate(phases):
        rng = random.Random(i)
        cx = x0 + (i % COLS) * gap + rng.uniform(-14, 14)
        cy = y0 + (i // COLS) * gap * 1.25 + rng.uniform(-14, 14)
        b = flash(p)
        demo.dot(cv, cx, cy, r=7, color=demo.LINE)
        if b > 0.02:
            demo.dot(cv, cx, cy, r=10 + 16 * b, color=GLOW, alpha=0.25 * b)
            demo.dot(cv, cx, cy, r=7, color=GLOW, alpha=b)
    cv.mark('swarm', x0 - 30, y0 - 30, (COLS - 1) * gap + 60, (ROWS - 1) * gap * 1.25 + 60)
    # the same oscillators as beads on a phase circle, bunching up as they lock
    cx, cy, rad = 770, 270, 130
    cv.arc(cx, cy, rad, 0, 2 * math.pi, demo.LINE, width=3)
    for p in phases:
        demo.dot(cv, cx + rad * math.cos(p - math.pi / 2), cy + rad * math.sin(p - math.pi / 2),
                 r=7, color=GLOW, alpha=0.4 + 0.6 * flash(p))
    r, psi = order(phases)
    cv.line(cx, cy, cx + rad * r * math.cos(psi - math.pi / 2), cy + rad * r * math.sin(psi - math.pi / 2),
            demo.TEAL, width=4)
    demo.dot(cv, cx, cy, r=5, color=demo.TEAL)
    cv.mark('phases', cx - rad, cy - rad, 2 * rad, 2 * rad)
    f = demo.font(22, 700)
    w, _ = vb.text.block_size(['IN STEP'], f)
    vb.text.draw(cv, ['IN STEP'], f, cx - w / 2, cy + rad + 30, demo.MUTED)
    cv.rect(cx - 100, cy + rad + 66, 200, 8, demo.LINE, radius=4)
    cv.rect(cx - 100, cy + rad + 66, 200 * r, 8, demo.TEAL, radius=4)


CAPABILITY = Capability(
    id='kuramoto-synchronization',
    name='Kuramoto synchronization',
    family='particles',
    group='Swarms & agents',
    aliases=('Kuramoto model', 'coupled oscillators', 'firefly sync', 'spontaneous synchronization'),
    definition='A crowd of blinking dots, each on its own slightly different rhythm, gradually nudges '
               'itself into time until they all pulse together.',
    phrasings=('fireflies that start blinking randomly and end up flashing in unison',
               'lots of dots pulsing out of step that slowly lock into the same beat',
               'show a swarm falling into sync on its own'),
    related=('fireflies', 'scanline-jitter', 'lorenz-attractor', 'turbulence-displacement', 'electric-arc',
             'location-ripple-pulse'),
    api=('videobuilder.capabilities.particles.kuramoto_synchronization.kuramoto',
         'videobuilder.capabilities.particles.kuramoto_synchronization.order',
         'videobuilder.capabilities.particles.kuramoto_synchronization.flash'),
    demo=lambda: demo.film(draw),
)
