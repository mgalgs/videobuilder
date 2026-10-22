"""Film grain: a fine, fresh speckle over the whole picture every frame,
strongest in the mid-tones and fading out in the deep shadows and highlights,
like the crystals of a film stock.

`vb.paper_grain` is a still paper texture (fibres and mottle), so this
module builds its own: plates of soft noise, a new one each film frame,
blended overlay so the picture's own brightness shapes how much shows.
"""
import math
import random
from functools import lru_cache

import cairo
from PIL import Image, ImageChops, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

PLATES = 8  # distinct noise plates, cycled with random offsets so no repeat shows


@lru_cache(maxsize=2 * PLATES)
def _plate(w, h, size, chroma, seed):
    """A w x h RGB noise plate centred on mid-grey: grains about `size` px
    across, `chroma` (0..1) of the way from grey to coloured specks."""
    rnd = random.Random(seed)
    gw, gh = max(1, round(w / size)), max(1, round(h / size))

    def channel():
        # Two uniforms averaged: a bell-ish spread, so most grains are subtle.
        a = Image.frombytes('L', (gw, gh), rnd.randbytes(gw * gh))
        b = Image.frombytes('L', (gw, gh), rnd.randbytes(gw * gh))
        im = ImageChops.add(a, b, scale=2.0)
        if (gw, gh) != (w, h):
            im = im.resize((w, h), Image.BICUBIC)
        return im.filter(ImageFilter.GaussianBlur(0.35 * max(1.0, size)))
    luma = channel()
    if chroma > 0:
        rgb = [Image.blend(luma, channel(), chroma) for _ in range(3)]
    else:
        rgb = [luma] * 3
    # Averaging narrows the spread; stretch it back out about mid-grey.
    rgb = [c.point(lambda v: max(0, min(255, round(128 + (v - 128) * 2.2)))) for c in rgb]
    im = Image.merge('RGB', rgb)
    surf = cairo.ImageSurface.create_for_data(bytearray(im.tobytes('raw', 'BGRX')), cairo.FORMAT_RGB24, w, h, w * 4)
    pat = cairo.SurfacePattern(surf)
    pat.set_extend(cairo.EXTEND_REPEAT)
    pat.set_filter(cairo.FILTER_NEAREST)
    return pat


def film_grain(cv, t, amount=0.5, size=1.5, chroma=0.0, seed=0, fps=24):
    """Lay film grain over everything drawn on `cv` so far, at film time `t`
    seconds. `amount` (0..1) is how strong it shows; `size` is a grain's size
    in film px (1: fine 35 mm, 3: coarse 16 mm); `chroma` (0..1) tints the
    specks red/green/blue instead of grey; the grain changes `fps` times a
    second (24: once per film frame). Overlay blending keeps it strongest
    in the mid-tones and gentle in near-black and near-white.

    Call it last in a frame's draw, e.g. `film_grain(cv, n / fps, amount=0.35)`;
    inside `cv.clip(...)` it grains just that region."""
    if amount <= 0:
        return
    s = cv.scale
    w, h = max(1, round(cv.width * s)), max(1, round(cv.height * s))
    k = math.floor(t * fps + 1e-9)
    rnd = random.Random(seed * 1_000_003 + k)
    pat = _plate(w, h, max(0.5, size * s), round(chroma, 2), seed * PLATES + k % PLATES)
    ctx = cv.ctx
    # User space -> device px (whatever layers are open), then a random shift into the plate.
    pat.set_matrix(ctx.get_matrix().multiply(cairo.Matrix(x0=rnd.randrange(w), y0=rnd.randrange(h))))
    ctx.save()
    ctx.set_source(pat)
    ctx.set_operator(cairo.OPERATOR_OVERLAY)
    ctx.paint_with_alpha(min(1.0, amount))
    ctx.restore()


def _scene(cv):
    """A dusk landscape: a sky going from deep to pale, a sun, three ridges --
    smooth gradients, where grain shows best."""
    ctx = cv.ctx
    sky = cairo.LinearGradient(0, 0, 0, demo.H)
    sky.add_color_stop_rgb(0, *vb.rgba('#2b2f5e')[:3])
    sky.add_color_stop_rgb(0.6, *vb.rgba('#a3a0c8')[:3])
    sky.add_color_stop_rgb(1, *vb.rgba('#e8c9b0')[:3])
    ctx.set_source(sky)
    ctx.paint()
    demo.dot(cv, demo.W * 0.68, demo.H * 0.3, r=110, color='#f2b705')
    for base, amp, phase, color in ((0.55, 70, 0.0, '#7c86e6'), (0.68, 55, 1.7, '#48507e'),
                                    (0.8, 45, 3.1, '#1f2233')):
        ctx.move_to(0, demo.H)
        for x in range(0, demo.W + 40, 40):
            ctx.line_to(x, demo.H * base - amp * math.sin(x / demo.W * 2 * math.pi * 1.3 + phase))
        ctx.line_to(demo.W, demo.H)
        ctx.close_path()
        ctx.set_source_rgb(*vb.rgba(color)[:3])
        ctx.fill()


def draw(n, cv):
    t = n / demo.FPS
    # A divider sweeps right to left: clean picture ahead of it, grain behind.
    edge = demo.W * (1 - vb.ease_in_out_quart(demo.phase(n, 0.4, 1.6)))
    _scene(cv)
    with cv.clip(edge, 0, demo.W - edge, demo.H):
        film_grain(cv, t, amount=0.42, size=1.6, chroma=0.15, seed=3)
    if 0 < edge < demo.W:
        cv.line(edge, 0, edge, demo.H, demo.INK, width=3, alpha=0.8)
    f = demo.font(30, 800)
    if edge > 140:
        vb.text.draw(cv, ['clean'], f, 40, 32, demo.INK)
    if edge < demo.W - 160:
        vb.text.draw(cv, ['grain'], f, demo.W - 40 - vb.text.block_size(['grain'], f)[0], 32, demo.INK)


TECHNIQUE = Technique(
    id='film-grain',
    name='Film grain',
    family='vfx',
    group='Film & analog',
    aliases=('film noise', 'emulsion grain', 'photochemical grain', 'grain overlay'),
    definition='A fine speckle that shimmers over the whole picture and changes every frame, '
               'showing most in the mid-tones, so clean digital images look shot on film.',
    phrasings=('make it look like it was shot on old film stock',
               'put a bit of moving grain over everything',
               'give the footage that noisy analog film texture'),
    related=('domain-warping', 'gaussian-blur', 'lens-dirt-overlay', 'dust-motes', 'thin-film-iridescence',
             'floyd-steinberg-dithering'),
    api=('videobuilder.techniques.vfx.film_grain.film_grain',),
    demo=lambda: demo.film(draw),
)
