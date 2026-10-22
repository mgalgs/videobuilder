"""Gate Weave: the whole picture wanders a few pixels side to side and hops
up and down from frame to frame, the way film never sits quite still as it
is pulled through a projector. A slow, smooth lateral drift (the film
snaking in the gate) plus a small per-frame registration jitter (each frame
landing a hair off the last)."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..principles.perlin_noise_drift import noise_drift
from ..schema import Technique


def gate_weave(n, fps=30, amount=6.0, seed=0, drift=0.6, speed=1.4):
    """The (dx, dy) pixel offset of frame `n`: shift the picture by it (e.g.
    `with cv.layer(dx=dx, dy=dy):`) to make it weave like projected film.

    `amount` is the largest offset in pixels. `drift` is the share of the
    sideways movement that is the slow smooth wander (read from noise at
    `speed` cycles a second); the rest, and the vertical, is a fresh random
    jolt every frame, so the picture never holds still from one frame to the
    next. The same `seed` gives the same weave, frame for frame."""
    t = n / fps
    rnd = random.Random(f'gate-weave:{seed}:{n}')
    jx = rnd.uniform(-1, 1) * amount * (1 - drift)
    jy = rnd.uniform(-1, 1) * amount * 0.6
    dx = noise_drift(t, f'gate-weave:{seed}', amount * drift, speed, octaves=2) + jx
    return dx, jy


def draw(n, cv):
    img = demo.photo()
    w, h = 640, 400
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    # The projector's mask stays put: static corner marks show the picture moving against it.
    m, k = 14, 30
    for cx, cy, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        px, py = cx - sx * m, cy - sy * m
        cv.line(px, py, px + sx * k, py, demo.MUTED, width=3)
        cv.line(px, py, px, py + sy * k, demo.MUTED, width=3)
    dx, dy = gate_weave(n, demo.FPS, amount=9.0, seed=4)
    with cv.layer(dx=dx, dy=dy):
        cv.shadow(x, y, w, h, radius=10, dy=8, blur=24, color=(0, 0, 0, 0.5))
        with cv.clip(x, y, w, h, radius=10):
            cv.image(img, *vb.Box(x, y, w, h).cover(img.w, img.h))
    cv.mark('picture', x + dx, y + dy, w, h)


TECHNIQUE = Technique(
    id='gate-weave',
    name='Gate weave',
    family='vfx',
    group='Film & analog',
    aliases=('projector weave', 'film gate jitter', 'film wobble', 'film weave'),
    definition='The whole picture never quite sits still, drifting a little sideways and nudging up and down '
               'every frame as if run off an old film projector.',
    phrasings=('make it wobble like old projected film',
               'add that subtle jitter vintage film has in the projector',
               'give the footage a slight frame-to-frame unsteadiness like a reel of celluloid'),
    related=('line-weave', 'wiggle-path', 'screen-tearing', 'scanline-jitter', 'tape-wobble',
             'gradient-border-spin'),
    api=('videobuilder.techniques.vfx.gate_weave.gate_weave',),
    demo=lambda: demo.film(draw),
)
