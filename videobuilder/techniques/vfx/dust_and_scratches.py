"""Dust and scratches: the damage of a worn film print laid over any shot --
specks of dirt and stray hairs that pop on for a frame or two, and thin
vertical scratches that run the full height of the picture, hold for a few
frames while they wander sideways, and vanish."""
import math
import random

import cairo

from .. import _demo as demo
from ..schema import Technique


def _rng(seed, *key):
    """A generator fixed by `seed` and `key`, so a frame always draws the same damage."""
    h = seed & 0xffffffff
    for k in key:
        h = (h * 1000003 + k + 0x9e3779b9) & 0xffffffff
    return random.Random(h)


def dust_and_scratches(cv, n, amount=1.0, seed=0, dust=26, hairs=3, scratches=4, fps=30):
    """Draw film damage for frame `n` over whatever `cv` already holds.

    `amount` (0 -> 1) scales how much shows: the number of specks and hairs
    and the chance of each scratch being there. `dust` and `hairs` are how
    many appear in a frame at full amount, each for that frame only, mostly
    dark (dirt on the print) with a few light ones (dirt on the negative).
    `scratches` is how many scratch lanes there are; each lane's scratch lives
    for a handful of frames, drifts and flickers slightly as it goes, then
    jumps somewhere else. `seed` varies the pattern; `fps` keeps scratch
    lifetimes in real time. Call it last in a draw, e.g. after `scene(cv)`:
    `dust_and_scratches(cv, f.n, amount=0.8)`."""
    amount = min(1.0, max(0.0, amount))
    if amount <= 0:
        return
    w, h = cv.width, cv.height
    u = h / 1080  # sizes are tuned at 1080 px tall
    c = cv.ctx
    c.save()
    c.set_line_cap(cairo.LINE_CAP_ROUND)

    def ink(r, light):
        return ((0.96, 0.93, 0.84) if light else (0.05, 0.04, 0.03)) + (r.uniform(0.55, 0.9),)

    # Scratches: each lane keeps one scratch for `life` frames, then rerolls.
    life = max(2, round(fps * 0.2))
    for lane in range(scratches):
        epoch, at = divmod(n + lane * 7, life)
        r = _rng(seed, 1, lane, epoch)
        if r.random() > 0.75 * amount:
            continue
        x = r.uniform(0.05, 0.95) * w + r.uniform(-1, 1) * 6 * u * at
        light = r.random() < 0.6
        jitter = _rng(seed, 2, lane, n)
        x += jitter.uniform(-2, 2) * u
        y0 = -10 if r.random() < 0.7 else r.uniform(0, 0.5) * h
        y1 = h + 10 if r.random() < 0.7 else r.uniform(0.5, 1) * h
        c.set_source_rgba(*ink(jitter, light))
        c.set_line_width(r.uniform(1.2, 3.0) * u)
        c.move_to(x, y0)
        steps = 6
        for i in range(1, steps + 1):
            c.line_to(x + math.sin(i * 1.7 + epoch) * r.uniform(0, 2.5) * u, y0 + (y1 - y0) * i / steps)
        c.stroke()

    r = _rng(seed, 3, n)
    # Dust: irregular blobs, most tiny, a few big enough to read as clumps.
    for _ in range(round(dust * amount * r.uniform(0.5, 1.5))):
        cx, cy = r.uniform(0, w), r.uniform(0, h)
        size = (r.random() ** 3 * 14 + 1.5) * u
        c.set_source_rgba(*ink(r, r.random() < 0.3))
        c.move_to(cx + size, cy)
        for i in range(1, 7):
            a = i * math.pi / 3.5
            k = size * r.uniform(0.55, 1.2)
            c.line_to(cx + math.cos(a) * k, cy + math.sin(a) * k)
        c.close_path()
        c.fill()
    # Hairs: thin wandering curls.
    for _ in range(round(hairs * amount * r.uniform(0, 1.6))):
        x, y = r.uniform(0, w), r.uniform(0, h)
        ang, length = r.uniform(0, 2 * math.pi), r.uniform(40, 160) * u
        c.set_source_rgba(*ink(r, r.random() < 0.3))
        c.set_line_width(r.uniform(1.0, 2.2) * u)
        c.move_to(x, y)
        turn = r.uniform(-0.12, 0.12)
        for _ in range(12):
            ang += turn + r.uniform(-0.25, 0.25)
            x += math.cos(ang) * length / 12
            y += math.sin(ang) * length / 12
            c.line_to(x, y)
        c.stroke()
    c.restore()


def _draw(n, cv):
    img = demo.photo()
    cv.image(img, 0, 0, demo.W, demo.H)
    cv.fill('#c79a5a', alpha=0.28)            # a warm, aged cast so it reads as an old print
    c = cv.ctx
    g = cairo.RadialGradient(demo.W / 2, demo.H / 2, demo.H * 0.35, demo.W / 2, demo.H / 2, demo.W * 0.65)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.55)
    c.set_source(g)
    c.paint()
    dust_and_scratches(cv, n, amount=0.15 + 0.85 * demo.phase(n, 0.3, 1.0), seed=4)


TECHNIQUE = Technique(
    id='dust-and-scratches',
    name='Dust and scratches',
    family='vfx',
    group='Film & analog',
    aliases=('film damage', 'film scratches', 'dirt and dust overlay', 'old film look', 'damaged print'),
    definition='Flecks of dirt, stray hairs and thin vertical lines flicker over the picture from frame to '
               'frame, as if it were projected from a worn, much-handled film reel.',
    phrasings=('make the footage look like a scratchy old movie',
               'add some film dirt and scratch lines over the shot',
               'give it that dusty, beat-up projector feel'),
    related=('lens-dirt-overlay', 'screen-tearing', 'light-leak', 'heat-haze', 'dust-motes', 'glitch-transition'),
    api=('videobuilder.techniques.vfx.dust_and_scratches.dust_and_scratches',),
    demo=lambda: demo.film(_draw),
)
