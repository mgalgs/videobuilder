"""Emboss: the picture turns into a flat grey plate whose shapes stand up in
relief, every edge catching light on one side and falling into shade on the
other, as if pressed into metal or paper."""
import math
from contextlib import contextmanager

import cairo
from PIL import Image, ImageChops, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...canvas import rgba
from ...looks import fx


def emboss(im, light=135.0, depth=3.0, strength=2.5, soften=1.2, colour=0.0, u=1.0):
    """`im` (a PIL image) as a relief, the same size, RGB. Each pixel's
    brightness is compared with its neighbour `depth` px towards the light:
    edges facing the light come out bright, edges facing away dark, flat
    areas a mid grey.

    - `light`: where the light comes from, in degrees (0 = right, 90 = top,
      135 = top-left).
    - `depth`: how far apart the compared pixels are -- the bevel's width.
    - `strength`: how hard the relief is pushed from grey.
    - `soften`: a blur (px) taken first, so edges bevel rather than alias.
    - `colour`: 0 gives the plain grey plate; 1 lays the relief over the
      picture's own colours.
    - `u`: device px per 1080-frame px, so the bevel sizes the same at every
      render scale (`embossed` passes it)."""
    im = im.convert('RGB')
    g = im.convert('L')
    if soften > 0:
        g = g.filter(ImageFilter.GaussianBlur(soften * u))
    a = math.radians(light)
    dx, dy = round(math.cos(a) * depth * u), round(-math.sin(a) * depth * u)
    toward = g.copy()                   # toward[p] = g[p + (dx, dy)]; where that falls off, g itself (flat)
    toward.paste(g, (-dx, -dy))
    relief = ImageChops.subtract(g, toward, scale=1 / max(strength, 1e-6), offset=128)
    plate = relief.convert('RGB')
    if colour <= 0:
        return plate
    return Image.blend(plate, ImageChops.overlay(im, plate), min(colour, 1.0))


EMBOSS = fx.Filter('emboss', 'Emboss', 'a grey relief plate lit from one side',
                   lambda im, t, age, u, **kw: emboss(im, u=u, **kw), aliases=('relief',))


@contextmanager
def embossed(cv, box=None, light=135.0, depth=3.0, strength=2.5, soften=1.2, colour=0.0):
    """Everything drawn inside comes out embossed (see `emboss`). `box`
    (x, y, w, h in the canvas's coordinates) limits the treatment to that
    region, the rest of the frame left as drawn -- slide its edge to wipe the
    relief on. Draw copy that must stay readable outside the block.

        with embossed(cv, box=(0, 0, wipe_x, demo.H)):
            draw_scene(cv)
    """
    opts = dict(light=light, depth=depth, strength=strength, soften=soften, colour=colour)
    with fx.apply(cv, EMBOSS, 0.0, box=box, opts=opts):
        yield cv


# ---- the demo ----

PX, PY, PW, PH = 200, 95, 560, 350     # the picture's panel


def _wave(x, base, amp, length, shift):
    return base + amp * math.sin(2 * math.pi * x / length + shift)


def _hill(c, base, amp, length, shift, color):
    c.move_to(PX, PY + PH)
    for i in range(0, PW + 1, 16):
        c.line_to(PX + i, _wave(i, base, amp, length, shift))
    c.line_to(PX + PW, PY + PH)
    c.close_path()
    c.set_source_rgba(*rgba(color))
    c.fill()


def scene(cv):
    """The picture being embossed: a sky, a sun, three rolling hills and a word."""
    c = cv.ctx
    c.save()
    sky = cairo.LinearGradient(0, PY, 0, PY + PH * 0.7)
    sky.add_color_stop_rgb(0, 52 / 255, 60 / 255, 140 / 255)
    sky.add_color_stop_rgb(1, 120 / 255, 132 / 255, 230 / 255)
    c.rectangle(PX, PY, PW, PH)
    c.set_source(sky)
    c.fill()
    c.restore()
    demo.dot(cv, PX + PW * 0.76, PY + 82, r=36, color='#f2b51c')
    c.save()
    _hill(c, PY + 200, 17, 380, 0.3, '#5d6fb8')
    _hill(c, PY + 245, 20, 320, 2.1, '#34407a')
    _hill(c, PY + 295, 13, 450, 4.0, '#1f2540')
    c.restore()
    demo.word(cv, 'RELIEF', PX + PW * 0.32, PY + 84, size=64, color=demo.INK)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.2))
    edge = PX + PW * p
    scene(cv)
    if p > 0:
        with embossed(cv, box=(PX, PY, edge - PX, PH), depth=5):
            scene(cv)
    if 0 < p < 1:
        cv.line(edge, PY, edge, PY + PH, '#e9e6df', width=4)
    cv.outline(PX, PY, PW, PH, demo.LINE, width=2)
    cv.mark('picture', PX, PY, PW, PH)


TECHNIQUE = Technique(
    id='emboss',
    name='Emboss',
    family='vfx',
    group='Blend & composite',
    aliases=('relief filter', 'bevel emboss', 'raised relief'),
    definition='The image becomes a flat grey surface where every outline is raised, lit bright on one side '
               'and shaded on the other, like a stamped metal plate.',
    phrasings=('make the picture look pressed into metal',
               'turn the frame into a grey carved relief',
               'stamp the image so its shapes stand out like an embossed card'),
    related=('fresnel-edge-glow', 'ascii-art-render', 'heat-haze', 'op-art-vibrating-pattern', 'film-edge-frame',
             'refresh-bar'),
    api=('videobuilder.techniques.vfx.emboss.embossed',
         'videobuilder.techniques.vfx.emboss.emboss'),
    demo=lambda: demo.film(draw),
)
