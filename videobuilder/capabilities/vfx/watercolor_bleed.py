"""Watercolor bleed: a flat painting goes wet. Every coloured area creeps
past its edge into its neighbours with a soft, ragged front, the colours mix
where they meet, and pigment pools darker along the borders, the way paint
runs on damp paper."""
import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ...looks.fx import image_surface, surface_image
from ..schema import Technique


@lru_cache(maxsize=8)
def _damp(w, h, seed):
    """Static blotchy noise (L, 0-255) for a w x h image: where the paper is
    wetter the paint runs further."""
    rnd = random.Random(f'damp:{seed}')
    out = Image.new('L', (w, h), 128)
    for cells, weight in ((6, 0.6), (18, 0.4)):
        cw, ch = cells, max(2, round(cells * h / max(1, w)))
        n = Image.new('L', (cw, ch))
        n.putdata([rnd.randrange(256) for _ in range(cw * ch)])
        n = n.resize((w, h), Image.BICUBIC)
        out = Image.blend(out, n, weight)
    lo, hi = out.getextrema()
    return out.point([round(255 * (v - lo) / max(1, hi - lo)) for v in range(256)])


@lru_cache(maxsize=8)
def _offsets(cols, rows, seed):
    """Per-vertex (angle, size, drift) for the mesh that pushes the edges about."""
    rnd = random.Random(f'mesh:{seed}')
    return tuple(tuple((rnd.uniform(0, 2 * math.pi), rnd.uniform(0.3, 1.0), rnd.uniform(-1.5, 1.5))
                       for _ in range(cols + 1)) for _ in range(rows + 1))


def _warp(im, amount, cell, p, seed):
    """`im` with its contents pushed around by up to `amount` px on a jittered
    mesh of `cell`-px squares, so straight edges go ragged and wander."""
    w, h = im.size
    if amount < 0.5:
        return im
    cols, rows = max(1, round(w / cell)), max(1, round(h / cell))
    offs = _offsets(cols, rows, seed)

    def at(i, j):
        ang, size, drift = offs[j][i]
        x, y = w * i / cols, h * j / rows
        if 0 < i < cols:
            x += math.cos(ang + drift * p) * size * amount
        if 0 < j < rows:
            y += math.sin(ang + drift * p) * size * amount
        return x, y

    mesh = []
    for j in range(rows):
        for i in range(cols):
            box = (round(w * i / cols), round(h * j / rows), round(w * (i + 1) / cols), round(h * (j + 1) / rows))
            quad = (*at(i, j), *at(i, j + 1), *at(i + 1, j + 1), *at(i + 1, j))
            mesh.append((box, quad))
    return im.transform((w, h), Image.MESH, mesh, Image.BILINEAR)


def bleed_image(im, p, reach=36.0, pool=0.55, seed=0):
    """`im` (a PIL RGB image) with its colours bled at progress `p` (0 -> 1).
    Edges spread by up to about `reach` px (in `im`'s pixels), fastest at
    first like paint soaking into paper; wetter patches of the paper run
    further than drier ones; `pool` is how much darker pigment collects along
    the fronts where colours meet. The same `seed` gives the same wet paper,
    frame for frame. Returns a new image the same size."""
    p = vb.clamp01(p)
    if p <= 0:
        return im.copy()
    w, h = im.size
    soak = p ** 0.7  # like paint soaking into paper: quicker at first, slowing as it goes
    r = reach * soak
    # Ragged fronts: the picture is pushed about at two scales before it softens.
    out = _warp(im, r * 0.45, max(4.0, reach * 1.6), p, seed)
    out = _warp(out, r * 0.18, max(3.0, reach * 0.45), p, seed + 1)
    # Soft spread, further where the paper is wetter.
    near = out.filter(ImageFilter.GaussianBlur(r * 0.25))
    far = out.filter(ImageFilter.GaussianBlur(r * 0.65))
    out = Image.composite(far, near, _damp(w, h, seed))
    # Pigment pools at the fronts: where the picture differs from a wide blur
    # of itself, its colour deepens (multiplied by itself, so bare paper stays pale).
    if pool > 0:
        wide = out.filter(ImageFilter.GaussianBlur(r * 1.2 + 1))
        edge = ImageChops.difference(out, wide).convert('L')
        k = pool * min(1.0, p * 3)
        out = Image.composite(ImageChops.multiply(out, out), out,
                              edge.point([min(255, round(v * 4 * k)) for v in range(256)]))
    return out


def watercolor_bleed(cv, body, p, box=None, reach=36.0, pool=0.55, seed=0):
    """Draw `body(cv)` with its colours bleeding at progress `p` (0 -> 1),
    inside `box` (a `vb.Box` or (x, y, w, h) in frame px; the whole frame
    by default). Leave a margin of paper around the painting inside `box` so
    the paint has somewhere to run. `reach` is how far edges spread, in frame
    px; `pool` and `seed` are as in `bleed_image`. At `p` 0 it is just `body`.

    In a film: `watercolor_bleed(cv, lambda c: paint_the_scene(c), demo.phase(n, 0.5, 2.5), box=frame)`."""
    if p <= 0:
        return body(cv)
    sub = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    body(sub)
    s = cv.scale
    x, y, w, h = vb.Box(*box) if box is not None else (0, 0, cv.width, cv.height)
    dx, dy = max(0, round(x * s)), max(0, round(y * s))
    dw = min(sub.surface.get_width() - dx, max(1, round(w * s)))
    dh = min(sub.surface.get_height() - dy, max(1, round(h * s)))
    im = surface_image(sub.surface, dx, dy, dw, dh)
    # Work at half size when there are pixels to spare; the bleed is soft anyway.
    half = dw >= 200
    work = im.resize((dw // 2, dh // 2), Image.BILINEAR) if half else im
    out = bleed_image(work, p, reach=reach * s * (0.5 if half else 1.0), pool=pool, seed=seed)
    if half:
        out = out.resize((dw, dh), Image.BICUBIC)
    surf = image_surface(out)
    ctx = cv.ctx
    ctx.save()
    ctx.identity_matrix()
    ctx.set_source_surface(surf, dx, dy)
    ctx.rectangle(dx, dy, dw, dh)
    ctx.fill()
    ctx.restore()


# ---- demo: a little landscape painted in flat washes on a sheet of paper ----

PAPER = '#f1efe8'
SHEET = vb.Box(demo.W / 2 - 300, demo.H / 2 - 200, 600, 400)
ART = vb.Box(SHEET.x + 40, SHEET.y + 36, SHEET.w - 80, SHEET.h - 72)


def _hill(ctx, a, peaks, color):
    """A filled hill band across ART: `peaks` are (x fraction, y fraction) along its top."""
    ctx.move_to(a.x, a.y + a.h)
    pts = [(a.x + fx * a.w, a.y + fy * a.h) for fx, fy in peaks]
    ctx.line_to(*pts[0])
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        mx = (x0 + x1) / 2
        ctx.curve_to(mx, y0, mx, y1, x1, y1)
    ctx.line_to(a.x + a.w, a.y + a.h)
    ctx.close_path()
    ctx.set_source_rgba(*vb.canvas.rgba(color))
    ctx.fill()


def _painting(cv):
    cv.rect(*SHEET, PAPER)
    a = ART
    cv.rect(*a, '#a9b8ec')                                       # sky
    cv.rect(a.x, a.y, a.w, a.h * 0.35, '#8ea2e6', alpha=0.6)     # deeper sky up top
    demo.dot(cv, a.x + a.w * 0.74, a.y + a.h * 0.28, r=34, color='#f2a516')
    ctx = cv.ctx
    _hill(ctx, a, ((0, 0.62), (0.3, 0.38), (0.55, 0.6), (1, 0.48)), '#6f84d6')
    _hill(ctx, a, ((0, 0.72), (0.22, 0.66), (0.5, 0.8), (0.8, 0.62), (1, 0.7)), '#d8574a')
    _hill(ctx, a, ((0, 0.92), (0.4, 0.74), (0.7, 0.86), (1, 0.82)), '#2f6e5e')


def draw(n, cv):
    cv.shadow(*SHEET, dy=10, blur=30, color=(0, 0, 0, 0.5))
    watercolor_bleed(cv, _painting, demo.phase(n, 0.4, 2.7), box=SHEET, reach=30, seed=3)
    cv.mark('painting', *SHEET)


TECHNIQUE = Technique(
    id='watercolor-bleed',
    name='Watercolor bleed',
    family='vfx',
    group='Painterly & sketch',
    aliases=('watercolor wash', 'wet paint bleed', 'pigment bleed', 'wet-in-wet'),
    definition='Crisp areas of colour turn wet and run into each other, their borders softening into '
               'ragged, blotchy fringes with darker pigment gathering where they meet.',
    phrasings=('make the painting look like the paint is still wet and running',
               'let the colours bleed into each other like watercolour on damp paper',
               'soften the shapes into a runny watercolour wash'),
    related=('ink-bleed', 'chroma-bleed', 'ink-in-water', 'ink-spread-reveal', 'drip-wipe', 'ink-splash-spread'),
    api=('videobuilder.techniques.vfx.watercolor_bleed.watercolor_bleed',
         'videobuilder.techniques.vfx.watercolor_bleed.bleed_image'),
    demo=lambda: demo.film(draw),
)
