"""Meteor shower: thin streaks of light cut across a dark sky on a slant, each
a bright head trailing a tail that fades out behind it, arriving at uneven
moments."""
import math
import random

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def meteors(t, width, height, seed=0, rate=2.5, life=0.8, angle=32, speed=0.8, tail=0.17, start=-1.0):
    """The meteors alive at time `t` seconds, as dicts with the head `x`, `y`,
    the unit direction `dx`, `dy`, the current `tail` length in px and an
    `alpha` (0 -> 1 -> 0 over the meteor's life).

    Meteors arrive at irregular moments, on average `rate` a second, from
    `start` seconds on (negative: the sky is already busy at 0). Each flies
    for about `life` seconds at about `speed` frame widths a second, its
    tail up to about `tail` frame widths long, heading `angle` degrees below
    the horizontal, left to right (a negative angle flies right to left).
    Start points are spread so every path crosses the `width` x
    `height` frame. The same `seed` gives the same shower, frame for frame."""
    rng = random.Random(f'meteors:{seed}')
    out = []
    born = start
    while born <= t:
        gap = rng.expovariate(rate)
        m_life = life * rng.uniform(0.7, 1.3)
        m_speed = speed * width * rng.uniform(0.75, 1.25)
        m_tail = tail * width * rng.uniform(0.6, 1.3)
        a = math.radians(angle + rng.uniform(-3, 3))
        fx, fy = rng.uniform(-0.15, 0.85), rng.uniform(-0.1, 0.45)
        age = t - born
        if age < m_life:
            dx, dy = math.cos(a), math.sin(a)
            x0 = (fx if dx >= 0 else 1 - fx) * width
            travelled = m_speed * age
            p = age / m_life
            out.append({'x': x0 + dx * travelled, 'y': fy * height + dy * travelled, 'dx': dx, 'dy': dy,
                        'tail': min(m_tail, travelled + 1),
                        'alpha': vb.clamp01(p / 0.12) * vb.clamp01((1 - p) / 0.35)})
        born += gap
    return out


def draw_meteor(cv, m, color='#ffffff', head=3.5, width=3.0):
    """Draw one meteor `m` (a dict from `meteors`): a tail that fades from
    `color` at the head to nothing, `width` px thick at the head, and a head
    `head` px across with a soft glow."""
    c, a = cv.ctx, m['alpha']
    if a <= 0:
        return
    hx, hy = m['x'], m['y']
    tx, ty = hx - m['dx'] * m['tail'], hy - m['dy'] * m['tail']
    # The tail: a thin wedge, widest at the head, shaded along its length.
    nx, ny = -m['dy'] * width / 2, m['dx'] * width / 2
    c.new_path()
    c.move_to(tx, ty)
    c.line_to(hx + nx, hy + ny)
    c.line_to(hx - nx, hy - ny)
    c.close_path()
    grad = cairo.LinearGradient(tx, ty, hx, hy)
    r, g, b, _ = rgba(color)
    grad.add_color_stop_rgba(0, r, g, b, 0)
    grad.add_color_stop_rgba(0.7, r, g, b, 0.35 * a)
    grad.add_color_stop_rgba(1, r, g, b, 0.95 * a)
    c.set_source(grad)
    c.fill()
    # The head: a bright core inside a soft halo.
    glow = cairo.RadialGradient(hx, hy, 0, hx, hy, head * 4)
    glow.add_color_stop_rgba(0, r, g, b, 0.55 * a)
    glow.add_color_stop_rgba(1, r, g, b, 0)
    c.set_source(glow)
    c.arc(hx, hy, head * 4, 0, 2 * math.pi)
    c.fill()
    cv.sector(hx, hy, head, 0, 2 * math.pi, color, alpha=a)


def draw_meteor_shower(cv, t, box=None, color='#ffffff', seed=0, **kw):
    """Draw the shower at time `t` seconds inside `box` (default: the whole
    canvas), clipped to it. `kw` goes to `meteors` (`rate`, `life`, `angle`,
    `speed`, `tail`, `start`). Returns the meteors drawn."""
    box = vb.Box(*box) if box is not None else vb.Box(0, 0, cv.width, cv.height)
    ms = meteors(t, box.w, box.h, seed=seed, **kw)
    with cv.clip(*box):
        for m in ms:
            draw_meteor(cv, dict(m, x=m['x'] + box.x, y=m['y'] + box.y), color=color)
    return ms


def _sky(cv, n):
    """A deep night gradient with faint, slowly twinkling stars."""
    sky = cairo.LinearGradient(0, 0, 0, demo.H)
    sky.add_color_stop_rgba(0, *rgba('#070a14'))
    sky.add_color_stop_rgba(1, *rgba('#141a2c'))
    cv.ctx.set_source(sky)
    cv.ctx.paint()
    rng = random.Random('stars')
    for i in range(140):
        x, y, r = rng.uniform(0, demo.W), rng.uniform(0, demo.H), rng.uniform(0.8, 1.8)
        twinkle = 0.5 + 0.5 * math.sin(n / demo.FPS * rng.uniform(1, 4) + i)
        demo.dot(cv, x, y, r, color=demo.INK, alpha=0.15 + 0.3 * twinkle)


def draw(n, cv):
    _sky(cv, n)
    for m in draw_meteor_shower(cv, n / demo.FPS, seed=5, rate=3.2):
        cv.mark('meteor', m['x'] - 4, m['y'] - 4, 8, 8)


CAPABILITY = Capability(
    id='meteor-shower',
    name='Meteor shower',
    family='particles',
    group='Emitters',
    aliases=('shooting stars', 'falling streaks', 'meteors'),
    definition='Slanted streaks of light shoot across a night sky one after another at uneven moments, '
               'each a bright point dragging a tail that fades away behind it.',
    phrasings=('shooting stars flying across the background',
               'a few meteors zipping diagonally over a dark sky',
               'streaks of light falling across the screen like a meteor shower'),
    related=('confetti-burst', 'falling-letter-rain', 'lens-flare', 'diffraction-spikes', 'ripple', 'shape-burst'),
    api=('videobuilder.capabilities.particles.meteor_shower.draw_meteor_shower',
         'videobuilder.capabilities.particles.meteor_shower.meteors',
         'videobuilder.capabilities.particles.meteor_shower.draw_meteor'),
    demo=lambda: demo.film(draw),
)
