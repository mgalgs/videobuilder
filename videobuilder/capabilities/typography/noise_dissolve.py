"""Noise Dissolve: text appears or disappears through a cloudy noise
threshold, patch by patch, with a thin glowing edge where it is still
eating through."""
from contextlib import contextmanager
from functools import lru_cache

from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...canvas import _a8, rgba
from ...looks.fx import noise


@lru_cache(maxsize=8)
def noise_field(w, h, grain, seed):
    """A w x h grey noise field (device px) of soft blotches about `grain`
    px across: seeded random cells, smoothly upscaled. Cached per size."""
    small = noise(max(2, round(w / grain)) + 1, max(2, round(h / grain)) + 1, seed)
    return small.resize((w, h), Image.BICUBIC)


def _ramp(level, width, tent=False):
    """A 256-entry lookup: for noise value n, how far past `level` it is,
    over `width`, as 0..255 -- a soft step, or a peak (`tent`) on the edge."""
    width = max(1e-6, width)
    out = []
    for n in range(256):
        d = (level - n) / width
        a = (1 - abs(2 * d - 1)) if tent else d
        out.append(int(255 * vb.clamp01(a)))
    return out


@contextmanager
def noise_dissolve(cv, p, grain=22, soft=0.08, seed=1, edge=None, edge_width=0.07):
    """Everything drawn inside shows only where the noise field is below
    progress `p` (0: none of it, 1: all of it), so it fills in or eats away
    in irregular patches. `grain`: blotch size in frame px; `soft`: how soft
    each patch's border is (a fraction of the noise range); `edge`: a colour
    to light the advancing border in (None: no edge), `edge_width` wide.

    Reveal with `p` rising; dissolve away with `1 - p`:

        with noise_dissolve(cv, demo.phase(n, 0.3, 1.5), edge=ACCENT):
            vb.text.draw(cv, ['HELLO'], font, x, y, INK)
    """
    c = cv.ctx
    p = vb.clamp01(p)
    c.push_group()
    try:
        yield cv
    finally:
        content = c.pop_group()
    if p <= 0:
        return
    if p >= 1:
        c.set_source(content)
        c.paint()
        return
    sw, sh = cv.surface.get_width(), cv.surface.get_height()
    field = noise_field(sw, sh, max(1.0, grain * cv.scale), seed)
    cut = p * (255 + 255 * (soft + edge_width))   # the noise level the reveal has reached
    shown = _a8(field.point(_ramp(cut - 255 * edge_width, 255 * soft)))
    m = c.get_matrix()      # the group's pattern is placed by the matrix in force at set_source
    c.save()
    c.set_source(content)
    c.identity_matrix()     # the masks are in device px
    c.mask_surface(shown, 0, 0)
    if edge:
        rim = _a8(field.point(_ramp(cut, 255 * edge_width, tent=True)))
        c.push_group()
        c.set_matrix(m)
        c.set_source(content)
        c.identity_matrix()
        c.mask_surface(rim, 0, 0)
        lit = c.pop_group()     # the content's own shape, only along the border
        c.set_source_rgba(*rgba(edge))
        c.mask(lit)
    c.restore()


def draw(n, cv):
    f = demo.font(150, 900)
    text = 'DISSOLVE'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    shown = demo.phase(n, 0.2, 1.3) - demo.phase(n, 1.8, 2.8)   # in, hold, back out
    with noise_dissolve(cv, shown, edge=demo.ACCENT, seed=4):
        box = vb.text.draw(cv, [text], f, x, y, demo.INK)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='noise-dissolve',
    name='Noise dissolve',
    family='typography',
    group='Physics and particles',
    aliases=('noise reveal', 'threshold dissolve', 'burn-away text', 'erode transition'),
    definition='Text fills in or eats away in irregular cloudy patches, as if a noise pattern were '
               'being thresholded over it, often with a lit edge along the moving border.',
    phrasings=('the title appears in random blotches until it is solid',
               'make the words break up and vanish in patchy noise',
               'burn the text away with a glowing edge'),
    related=('blur-dissolve', 'dither-reveal', 'smoke-dissolve', 'pixelation-reveal', 'noise-field-warp',
             'film-dissolve'),
    api=('videobuilder.techniques.typography.noise_dissolve.noise_dissolve',
         'videobuilder.techniques.typography.noise_dissolve.noise_field'),
    demo=lambda: demo.film(draw),
)
