"""Glitter Pour: a thin, glinting stream of flakes falls from a spout, lands
on the floor and slides down into a growing heap."""
import math
import random

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability

GLITTER = ('#f6d36b', '#e8b23a', '#fff1b8', '#d9a441', '#f4f4f2')
GRAVITY = 2600.0  # px/s^2: fast enough that the stream reads as falling, not floating


def _flake(i, seed, spread):
    """The fixed random traits of flake `i`: launch drift, size, colour, spin
    and where on the heap it comes to rest (a triangular spread about the tip)."""
    r = random.Random(f'{seed}:{i}')
    return (r.gauss(0, spread), r.uniform(0, 60), r.uniform(2.2, 4.6), r.randrange(len(GLITTER)),
            r.uniform(0, 2 * math.pi), r.uniform(6, 16), r.random() - r.random(), r.uniform(0, 1))


def heap_height(count, flake_area=10.0, slope=0.28):
    """Height of a cone-shaped heap of `count` landed flakes, each covering
    `flake_area` px^2 of its cross-section, with sides rising `slope` px per px."""
    return math.sqrt(max(0, count) * flake_area * slope)


def glitter_pour(cv, x, y, ground, t, rate=420, stop=None, spread=18.0, seed=0, colors=GLITTER,
                 flake_area=10.0, slope=0.28, pile_color=None):
    """Draw a pour of glitter `t` seconds after it began, from a spout at
    (x, y) onto the floor at `ground`. Flakes leave at `rate` per second
    (until `stop` seconds, if given), fall under gravity drifting sideways by
    about `spread` px/s, glint as they spin, and on landing slide down the
    heap's sides to rest; the heap is a cone that grows with what has landed
    (`flake_area`, `slope` as in `heap_height`), filled behind the flakes in
    `pile_color` (default: the darkest of `colors`, dimmed). Purely a function
    of `t`: the same `seed` gives the same pour, frame for frame. Returns the
    Box around the stream and the heap."""
    ctx = cv.ctx
    emitted = int(max(0.0, min(t, stop if stop is not None else t)) * rate)
    drop = ground - y
    fall = math.sqrt(2 * drop / GRAVITY)  # time from spout to floor, ignoring the heap
    landed = max(0, min(emitted, int((t - fall) * rate) + 1)) if t > fall else 0
    peak = heap_height(landed, flake_area, slope)
    half = peak / slope if peak else 0
    if peak > 0:
        ctx.new_path()
        ctx.move_to(x - half, ground)
        ctx.curve_to(x - half * 0.45, ground, x - half * 0.2, ground - peak, x, ground - peak)
        ctx.curve_to(x + half * 0.2, ground - peak, x + half * 0.45, ground, x + half, ground)
        ctx.close_path()
        ctx.set_source_rgba(*rgba(pile_color or colors[-2 if len(colors) > 1 else 0], 0.55))
        ctx.fill()

    for i in range(emitted):
        born = i / rate
        age = t - born
        vx, vy, size, ci, spin, glint, u, depth = _flake(i, seed, spread)
        h = heap_height(min(i, landed), flake_area, slope)  # flakes arrive in order: i landed before this one
        land_y = ground - h
        # solve y + vy*a + g/2*a^2 = land_y for the arrival time a
        arrive = (-vy + math.sqrt(vy * vy + 2 * GRAVITY * (land_y - y))) / GRAVITY
        if age < arrive:
            px, py = x + vx * age, y + vy * age + 0.5 * GRAVITY * age * age
        else:
            # slide from the tip to a resting spot on the heap's surface, with a little hop
            s = vb.clamp01((age - arrive) / 0.35)
            e = 1 - (1 - s) ** 3
            hw = h / slope
            rx = x + vx * arrive + u * hw
            ry = ground - h * (1 - abs(u)) * (1 - 0.15 * depth) - 1.5
            tx, ty = x + vx * arrive, land_y
            px = tx + (rx - tx) * e
            py = ty + (ry - ty) * e - math.sin(math.pi * s) * 10 * (1 - depth)
        # a flat flake catches the light only when it turns face-on
        face = abs(math.cos(spin + age * glint))
        if age >= arrive + 0.35:
            face = 0.35 + 0.65 * abs(math.cos(spin + t * 1.3))  # resting flakes still twinkle, slower
        bright = 0.3 + 0.7 * face ** 6
        ctx.save()
        ctx.translate(px, py)
        ctx.rotate(spin + age * glint)
        ctx.scale(1, 0.25 + 0.75 * face)
        ctx.rectangle(-size / 2, -size / 2, size, size)
        ctx.set_source_rgba(*rgba(colors[ci % len(colors)], bright))
        ctx.fill()
        ctx.restore()
        if face > 0.995 and age < arrive + 0.35 or face > 0.99995:
            g = size * 2.2  # a brief star glint on the flakes facing the light
            ctx.set_source_rgba(1, 1, 1, 0.85)
            ctx.set_line_width(1.2)
            ctx.move_to(px - g, py)
            ctx.line_to(px + g, py)
            ctx.move_to(px, py - g)
            ctx.line_to(px, py + g)
            ctx.stroke()
    w = max(half, 3 * spread * fall + 20)
    return vb.Box(x - w, y, 2 * w, ground - y)


def draw(n, cv):
    sx, sy, ground = demo.W / 2, 150, demo.H - 150
    demo.floor(cv, ground, color=demo.LINE)
    cv.rect(sx - 26, sy - 46, 52, 30, demo.MUTED, radius=6)  # a small spout the glitter leaves from
    cv.rect(sx - 10, sy - 20, 20, 20, demo.MUTED, radius=3)
    box = glitter_pour(cv, sx, sy, ground, n / demo.FPS - 0.15, seed=3)
    cv.mark('glitter', *box)


CAPABILITY = Capability(
    id='glitter-pour',
    name='Glitter pour',
    family='particles',
    group='Emitters',
    aliases=('glitter spill', 'sparkle stream'),
    definition='A steady trickle of tiny shiny flakes falls from one spot, flashing as they tumble, '
               'and builds into a glittering mound on the floor.',
    phrasings=('glitter streaming down and piling up at the bottom',
               'pour sparkly flakes from the top like sand from a jar',
               'a sparkle stream that falls and heaps on the ground'),
    related=('sph-fluid', 'ink-splash-spread', 'curl-noise-flow', 'drip-wipe', 'comment-pop-up-stack',
             'sheen-sweep'),
    api=('videobuilder.capabilities.particles.glitter_pour.glitter_pour',
         'videobuilder.capabilities.particles.glitter_pour.heap_height'),
    demo=lambda: demo.film(draw),
)
