"""Particle text formation: specks scattered all over the frame fly in, each
on its own clock and slightly curved path, and settle into the letters of a
word. It is the dissolve-to-particles sampling run in reverse, driven by the
particle-swarm-assemble motion."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ..shapes.particle_swarm_assemble import swarm
from ..typography.dissolve_to_particles import text_specks


def draw_formation(cv, lines, font, x, y, p, colors=(demo.INK,), bounds=None, seed=0, step=5, size=None,
                   jitter=1.2, **kw):
    """Draw `lines` (a string or list of lines, top-left at (x, y)) forming
    out of particles at progress `p` (0 -> 1).

    The word's ink is sampled every `step` px (`text_specks`); each sample is
    a square speck that starts at a seeded random spot inside `bounds` (x, y,
    w, h; default the whole canvas) and flies to its place in the letters
    (`swarm`; `kw` such as `stagger`, `curve`, `ease` go there). Specks are
    dim and small in flight and full strength once landed, each in one of
    `colors`; `jitter` px of seeded offset keeps the settled word grainy
    rather than a clean grid. At 1 every speck is home. Returns the Box of the
    text."""
    lines = [lines] if isinstance(lines, str) else list(lines)
    w, h = vb.text.block_size(lines, font)
    rnd = random.Random(f'formation:{seed}')
    targets = [(x + sx + rnd.uniform(-jitter, jitter), y + sy + rnd.uniform(-jitter, jitter))
               for sx, sy in text_specks(lines, font, step)]
    tints = [rnd.choice(colors) for _ in targets]
    size = size or step * 0.7
    for (px, py, q), tint in zip(swarm(targets, vb.clamp01(p), bounds or (0, 0, cv.width, cv.height),
                                       seed=seed, **kw), tints):
        r = size * (0.6 + 0.4 * q)
        cv.rect(px - r / 2, py - r / 2, r, r, tint, alpha=0.5 + 0.5 * q)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(190, 900)
    text = 'GATHER'
    w, h = vb.text.block_size([text], f)
    box = draw_formation(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.2, 2.5),
                         colors=(demo.INK, demo.INK, demo.INK, demo.ACCENT), seed=5, stagger=0.4)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='particle-text-formation',
    name='Particle text formation',
    family='particles',
    group='Particle text & images',
    aliases=('text assembly', 'particles forming words', 'particle assembly into type', 'particles form text',
             'dots assemble word'),
    definition='A cloud of tiny specks spread across the frame streams together until the specks sit '
               'in the shape of a word.',
    phrasings=('have the title build itself out of flying dots',
               'little particles swoop in from everywhere and spell out the word',
               'scattered specks come together to make the text'),
    related=('dissolve-to-particles', 'particle-swarm-assemble', 'metaball-goo-text', 'noise-dissolve',
             'text-on-a-path', 'dither-reveal'),
    api=('videobuilder.capabilities.particles.particle_text_formation.draw_formation',
         'videobuilder.capabilities.typography.dissolve_to_particles.text_specks',
         'videobuilder.capabilities.shapes.particle_swarm_assemble.swarm'),
    demo=lambda: demo.film(draw),
)
