"""Pencil sketch: a picture redrawn in graphite on pale paper -- its dark
areas filled with fine diagonal hatching (cross-hatched where they are
darkest), its edges traced in a soft grey line. The hatching boils a few
times a second, so a held sketch still looks hand-made."""
from functools import lru_cache

from PIL import Image, ImageChops, ImageFilter, ImageOps

import videobuilder as vb
from videobuilder.looks.fx import Filter, apply, boil, edges, grow, luma, noise, shrink, work_factor

from .. import _demo as demo
from ..schema import Technique

PAPER = (238, 237, 232)
GRAPHITE = (78, 80, 86)
DRAWINGS = 3    # hatch textures the sketch boils between


@lru_cache(maxsize=24)
def _strokes(w, h, angle, seed):
    """A w x h grey texture of long thin streaks at `angle` degrees, its
    values spread evenly over 0..255, so thresholding it at a tone covers
    that share of the paper with strokes."""
    side = int((w * w + h * h) ** 0.5) + 2
    streaks = noise(side, side, seed, stretch=36)
    turned = streaks.rotate(angle, resample=Image.BILINEAR)
    x0, y0 = (side - w) // 2, (side - h) // 2
    return ImageOps.equalize(turned.crop((x0, y0, x0 + w, y0 + h)))


@lru_cache(maxsize=8)
def _paper(w, h):
    grain = noise(w, h, 7, blur=0.6).point(lambda v: 128 + (v - 128) // 10)
    return ImageChops.soft_light(Image.new('RGB', (w, h), PAPER), Image.merge('RGB', (grain, grain, grain)))


def _hatch(tone, texture, lift=0, gain=1.0):
    """How hard the pencil presses where `tone` (L: 255 darkest) beats the
    stroke `texture`: 0 on bare paper, up to 255 on a stroke."""
    shaded = tone.point(lambda v: max(0, min(255, int((v - lift) * gain))))
    return ImageChops.subtract(shaded, texture).point(lambda v: min(255, v * 5))


def pencil(im, t=0.0, u=1.0, strength=1.0, outline=1.0, boil_rate=8):
    """`im` (a PIL RGB image) redrawn as a pencil sketch, the same size:
    diagonal hatching as dense as the picture is dark, a second cross-hatch
    in the darkest areas, and the strong edges traced. `u` is the frame's
    short side over 1080 (stroke size); `strength` scales how much graphite
    goes down; `outline` how dark the traced edges are (0: none). The
    hatching redraws `boil_rate` times a second of `t` (0: never)."""
    k = work_factor(u)
    small = shrink(im, k)
    gray = luma(small).filter(ImageFilter.GaussianBlur(1.0))
    w, h = gray.size
    tone = ImageOps.invert(gray)
    take = boil(t, boil_rate) % DRAWINGS if boil_rate else 0
    first = _hatch(tone, _strokes(w, h, 32, 10 + take), lift=40, gain=0.8 * strength)
    cross = _hatch(tone, _strokes(w, h, -48, 20 + take), lift=170, gain=1.2 * strength)
    lead = ImageChops.lighter(first, cross)
    if outline:
        line = edges(gray, level=8, blur=0.8, thick=1).filter(ImageFilter.GaussianBlur(0.5))
        lead = ImageChops.lighter(lead, line.point(lambda v: int(v * 0.9 * outline)))
    lead = grow(lead.point(lambda v: int(v * 0.7)), im.size, Image.BILINEAR)
    return Image.composite(Image.new('RGB', im.size, GRAPHITE), _paper(*im.size), lead)


FILTER = Filter('pencil-sketch', 'Pencil sketch', 'graphite hatching and traced edges on pale paper',
                lambda im, t, age, u, **opts: pencil(im, t, u, **opts), aliases=('graphite sketch',))


def sketch(cv, t, box=None, **opts):
    """A context manager: everything already on `cv`, and everything drawn
    inside the block, is redrawn as a pencil sketch when the block ends --
    the whole frame, or only `box` (x, y, w, h in frame px). `opts` go to
    `pencil` (`strength=`, `outline=`, `boil_rate=`)."""
    return apply(cv, FILTER, t, None, box, opts)


def draw(n, cv):
    img = demo.photo()
    pw, ph = 640, 420
    x, y = (demo.W - pw) / 2, (demo.H - ph) / 2
    cv.image(img, x, y, pw, ph)
    reveal = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.0))
    edge = x + pw * reveal
    if reveal > 0:
        with sketch(cv, n / demo.FPS, box=(x, y, edge - x, ph)):
            pass
    if 0 < reveal < 1:
        cv.line(edge, y, edge, y + ph, demo.INK, width=2, alpha=0.8)
    cv.mark('photo', x, y, pw, ph)


TECHNIQUE = Technique(
    id='pencil-sketch',
    name='Pencil sketch',
    family='vfx',
    group='Painterly & sketch',
    aliases=('graphite sketch', 'pencil drawing filter', 'line drawing'),
    definition='A picture is turned into a grey pencil drawing on paper, its shadows built from fine '
               'hatched strokes and its edges traced in soft lines.',
    phrasings=('make the photo look like it was drawn in pencil',
               'turn the footage into a graphite sketch',
               'a hand-drawn sketch version of the picture with hatching'),
    related=('whiteboard-marker-drawing', 'ink-outline', 'line-chart-draw-on', 'stroke-draw-on', 'line-boil',
             'parallel-coordinates-draw'),
    api=('videobuilder.techniques.vfx.pencil_sketch.pencil',
         'videobuilder.techniques.vfx.pencil_sketch.sketch'),
    demo=lambda: demo.film(draw),
)
