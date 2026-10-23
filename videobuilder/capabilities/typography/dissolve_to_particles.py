"""Dissolve to Particles: a word crumbles into fine specks along a moving
front; the specks drift away on a breeze and fade, until nothing is left."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

_SPECKS = {}  # (lines, repr(font), step) -> [(dx, dy), ...]


def text_specks(lines, font, step=4):
    """The points, one every `step` px, where `lines` (a string or list of
    lines, drawn as `vb.text.draw` would from (0, 0)) has ink. Cached, since
    a film asks for the same word every frame."""
    lines = (lines,) if isinstance(lines, str) else tuple(lines)
    key = (lines, repr(font), step)
    if key not in _SPECKS:
        w, h = vb.text.block_size(lines, font)
        cv = vb.Canvas(math.ceil(w), math.ceil(h))
        vb.text.draw(cv, list(lines), font, 0, 0, '#ffffff')
        data, stride = cv.bgra(), cv.surface.get_stride()
        _SPECKS[key] = [(x + step / 2, y + step / 2)
                        for y in range(0, cv.surface.get_height() - step + 1, step)
                        for x in range(0, cv.surface.get_width() - step + 1, step)
                        if data[(y + step // 2) * stride + (x + step // 2) * 4 + 3] > 120]
    return _SPECKS[key]


def draw_dissolve(cv, lines, font, x, y, p, color, speck=None, seed=0, step=4, life=0.45,
                  drift=(320, -140), spread=60, size=None):
    """Draw `lines` from its top-left (x, y) dissolving at progress `p` (0 -> 1).

    A front sweeps left to right; behind it the letters are gone and each bit
    of ink has become a speck (`speck` colour, default `color`) that rides
    `drift` px (dx, dy) plus up to `spread` px of scatter over `life` of the
    progress, shrinking and fading as it goes. At 0 the text is whole; at 1
    every speck is gone. The same `seed` gives the same specks, frame for
    frame. Returns the Box of the whole text."""
    lines = [lines] if isinstance(lines, str) else list(lines)
    w, h = vb.text.block_size(lines, font)
    p = vb.clamp01(p)
    sweep = 1 - life
    front = x + w * p / sweep if sweep > 0 else x + w * (p > 0) * 2
    if front < x + w:
        with cv.clip(front, y - h, x + w - front + 4, h * 3):
            vb.text.draw(cv, lines, font, x, y, color)
    size = size or step * 0.9
    for i, (sx, sy) in enumerate(text_specks(lines, font, step)):
        rnd = random.Random(seed * 1_000_003 + i)
        release = sweep * sx / w + rnd.uniform(-0.04, 0.04)
        age = (p - max(0.0, release)) / life
        if not 0 < age < 1:
            continue
        ang = rnd.uniform(0, 2 * math.pi)
        k = rnd.uniform(0.55, 1.25)
        e = 1 - (1 - age) ** 3  # scatter bursts out, then the breeze carries it
        dx = drift[0] * k * age + spread * math.cos(ang) * e
        dy = drift[1] * k * age + spread * math.sin(ang) * e + 18 * math.sin(age * 6 + ang)
        r = size * (1 - 0.6 * age)
        cv.rect(x + sx + dx - r / 2, y + sy + dy - r / 2, r, r, speck or color, alpha=(1 - age) ** 1.5)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(150, 900)
    text = 'VANISH'
    w, h = vb.text.block_size([text], f)
    box = draw_dissolve(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 1.6, 2.95),
                        demo.INK, speck=demo.ACCENT, seed=3)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='dissolve-to-particles',
    name='Dissolve to particles',
    family='typography',
    group='Physics and particles',
    aliases=('text disintegrate', 'particle dispersal', 'particle dissolve', 'disintegrate', 'scatter-out'),
    definition='The text crumbles into a cloud of tiny specks along a moving edge, and the specks '
               'blow away and fade until the word is gone.',
    phrasings=('make the title turn to dust and blow away',
               'the word breaks up into little particles that drift off',
               'disintegrate the text like sand in the wind'),
    related=('particle-text-formation', 'dither-reveal', 'pixelation-reveal', 'film-dissolve', 'blur-dissolve',
             'character-drop'),
    api=('videobuilder.capabilities.typography.dissolve_to_particles.draw_dissolve',
         'videobuilder.capabilities.typography.dissolve_to_particles.text_specks'),
    demo=lambda: demo.film(draw),
)
