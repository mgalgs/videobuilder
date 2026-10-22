"""Image to particles: a picture is sampled on a grid, one particle per sample
in that pixel's colour; the particles fly in from a loose cloud and settle
into place, so the image assembles out of them."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ..shapes.particle_swarm_assemble import swarm


def sample_particles(img, x, y, w, h, step=8):
    """One particle per `step` display px of the image `img` (a `vb.Image` or
    a PIL image) laid into the box (x, y, w, h): `(px, py, color)` triples,
    `color` an `(r, g, b)` tuple read from the pixel under each grid cell's
    centre."""
    pil = getattr(img, '_pil', img).convert('RGB')
    cols, rows = max(1, round(w / step)), max(1, round(h / step))
    small = pil.resize((cols, rows))  # each cell averages its block of the source
    sx, sy = w / cols, h / rows
    return [(x + (c + 0.5) * sx, y + (r + 0.5) * sy, small.getpixel((c, r)))
            for r in range(rows) for c in range(cols)]


def draw_image_particles(cv, particles, p, bounds, size=6.0, seed=0, **kw):
    """Draw `particles` (from `sample_particles`) at progress `p` (0 -> 1):
    each starts at a random spot inside `bounds` (x, y, w, h), small and faint,
    and flies to its home grid cell, growing to a `size` px square as it lands.
    `kw` goes to `particle_swarm_assemble.swarm` (`stagger`, `curve`, `ease`).
    Returns the Box around the settled image."""
    targets = [(px, py) for px, py, _ in particles]
    for (x, y, q), (_, _, color) in zip(swarm(targets, p, bounds, seed=seed, **kw), particles):
        s = size * (0.45 + 0.55 * q)
        cv.rect(x - s / 2, y - s / 2, s, s, color, alpha=0.35 + 0.65 * q)
    xs, ys = [x for x, _ in targets], [y for _, y in targets]
    return vb.Box(min(xs) - size / 2, min(ys) - size / 2, max(xs) - min(xs) + size, max(ys) - min(ys) + size)


STEP = 9
_PARTICLES = None


def _particles():
    global _PARTICLES
    if _PARTICLES is None:
        img = demo.photo()
        w = 900
        h = w * img.h / img.w
        _PARTICLES = sample_particles(img, (demo.W - w) / 2, (demo.H - h) / 2, w, h, step=STEP)
    return _PARTICLES


def draw(n, cv):
    box = draw_image_particles(cv, _particles(), demo.phase(n, 0.2, 2.5), (0, 0, demo.W, demo.H),
                               size=STEP - 1, seed=5, stagger=0.5, curve=0.25)
    cv.mark('image', *box)


TECHNIQUE = Technique(
    id='image-to-particles',
    name='Image to particles',
    family='particles',
    group='Particle text & images',
    aliases=('pixel particle portrait', 'particle image reconstruction', 'particle picture'),
    definition='A picture is broken into a grid of small particles, each tinted with the colour of the pixel '
               'it stands for, which fly in from a scattered cloud and lock into place to rebuild the image.',
    phrasings=('make the photo assemble itself out of thousands of coloured dots',
               'particles swirl in and settle into the picture',
               'turn the image into specks that fly together to form it'),
    related=('pixelation', 'pixel-build', 'pixel-sorting', 'pixelate-transition', 'particle-swarm-assemble',
             'spin-blur'),
    api=('videobuilder.techniques.particles.image_to_particles.draw_image_particles',
         'videobuilder.techniques.particles.image_to_particles.sample_particles',
         'videobuilder.techniques.shapes.particle_swarm_assemble.swarm'),
    demo=lambda: demo.film(draw),
)
