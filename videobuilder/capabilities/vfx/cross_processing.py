"""Cross-processing: a colour grade that imitates film developed in the
other film type's chemistry -- harsh contrast, highlights pushed to
yellow-green, shadows lifted to blue, colours oversaturated."""
from PIL import Image, ImageEnhance

import videobuilder as vb

from ... import canvas
from ...looks.fx import image_surface, surface_image
from .. import _demo as demo
from ..schema import Capability


def _curve(points):
    """A 256-entry lookup table through `points` ((in, out) pairs in 0..1, in
    rising order), straight between them."""
    out = []
    for v in range(256):
        x = v / 255
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            if x <= x1:
                y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
                break
        out.append(max(0, min(255, round(y * 255))))
    return out


# Red: a steep S, so skin and warm tones go hot and contrasty. Green: a
# softer S lifted through the mids, the source of the yellow-green cast.
# Blue: squashed into a narrow band with its blacks raised and whites
# pulled down, so shadows turn blue and highlights turn yellow.
RED = _curve(((0, 0), (0.25, 0.14), (0.5, 0.52), (0.75, 0.9), (1, 1)))
GREEN = _curve(((0, 0.02), (0.25, 0.2), (0.5, 0.58), (0.75, 0.88), (1, 1)))
BLUE = _curve(((0, 0.24), (0.5, 0.46), (1, 0.7)))


def cross_process_image(im, amount=1.0, saturation=1.35):
    """`im` (a PIL RGB image) cross-processed: the three channel curves above,
    then `saturation` boosted, the result mixed over the original by `amount`
    (0 untouched, 1 the full grade)."""
    if amount <= 0:
        return im
    r, g, b = im.split()
    graded = Image.merge('RGB', (r.point(RED), g.point(GREEN), b.point(BLUE)))
    graded = ImageEnhance.Color(graded).enhance(saturation)
    return graded if amount >= 1 else Image.blend(im, graded, amount)


def cross_process(cv, draw, amount=1.0, saturation=1.35):
    """Draw `draw(c)` onto `cv` with the cross-processed grade laid over it at
    `amount` (0 -> 1; ramp it to grade a shot in, hold it at 1 for the look).

    In a film, wrap the shot: `cross_process(cv, lambda c: shot(c, n), 1.0)`;
    copy that must stay neutral is drawn after, outside it."""
    sub = canvas.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    draw(sub)
    im = cross_process_image(surface_image(sub.surface), amount, saturation)
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(image_surface(im), 0, 0)
    c.paint()
    c.restore()


def _shot(cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))


def draw(n, cv):
    p = demo.phase(n, 0.6, 1.8)
    cross_process(cv, _shot, p * p * (3 - 2 * p))
    f = demo.font(28, 800)
    label = 'Cross-processed' if p >= 1 else 'Normal' if p <= 0 else ''
    if label:
        vb.text.draw(cv, [label], f, 40, 32, demo.INK)


CAPABILITY = Capability(
    id='cross-processing',
    name='Cross-processing',
    family='vfx',
    group='Color & grading',
    aliases=('cross process', 'cross-process color shift', 'x-pro'),
    definition='A grade that makes a shot look like film run through the wrong developer: '
               'contrast cranked up, bright areas gone yellow-green, shadows tinted blue and colours oversaturated.',
    phrasings=('give the footage that harsh yellow-green toy-camera film look',
               'make the colours go weird and punchy like badly developed film',
               'grade it with blue shadows and acid yellow highlights'),
    related=('palette-shift-transition', 'theme-swap-crossfade', 'cross-dissolve', 'color-cycling',
             'rgb-split', 'cross-zoom'),
    api=('videobuilder.capabilities.vfx.cross_processing.cross_process',
         'videobuilder.capabilities.vfx.cross_processing.cross_process_image'),
    demo=lambda: demo.film(draw),
)
