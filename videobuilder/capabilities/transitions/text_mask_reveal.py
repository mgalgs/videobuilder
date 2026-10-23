"""Text mask reveal: a big word is cut out of the outgoing scene, the
incoming scene shows through its letters, and the word zooms until one
letter swallows the frame."""
import math
from functools import lru_cache

import cairo

import videobuilder as vb
from videobuilder import text

from .. import _demo as demo
from ..schema import Capability


@lru_cache(maxsize=64)
def _word(word, font):
    """`word`'s glyph outlines as a cairo path with its ink's top-left at
    (0, 0), the ink's size, and a pivot deep inside one letter: `(path, w, h,
    (px, py), clearance)`, where every point within `clearance` of the pivot
    is inside the ink."""
    from gi.repository import PangoCairo
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
    ctx.move_to(0, 0)
    PangoCairo.layout_path(ctx, text._layout(ctx, word, font))
    x0, y0, x1, y1 = ctx.path_extents()
    ctx.new_path()
    ctx.translate(-x0, -y0)
    ctx.move_to(0, 0)
    PangoCairo.layout_path(ctx, text._layout(ctx, word, font))
    path = ctx.copy_path()
    ctx.identity_matrix()
    ctx.new_path()
    ctx.append_path(path)
    w, h = x1 - x0, y1 - y0
    # Probe a grid for the point furthest from any edge of the ink: zooming
    # about it, the letter it sits in grows over the whole frame.
    step, dirs = h / 80, [(math.cos(a), math.sin(a)) for a in (i * math.pi / 8 for i in range(16))]

    def clearance(px, py):
        r = step
        while r < h and all(ctx.in_fill(px + dx * r, py + dy * r) for dx, dy in dirs):
            r += step
        return r - step

    cands = [((i + 0.5) * w / 48, (j + 0.5) * h / 16) for i in range(48) for j in range(16)]
    scored = [(clearance(px, py), px, py) for px, py in cands if ctx.in_fill(px, py)]
    best = max(c for c, _, _ in scored)
    c, px, py = min((s for s in scored if s[0] >= 0.85 * best), key=lambda s: abs(s[1] - w / 2))
    return path, w, h, (px, py), max(c, step)


def text_mask_reveal(cv, a, b, p, word='OPEN', font=None, fill=0.8, ease=None):
    """Draw the reveal at progress `p` (0 -> 1): `a(cv)` with `word` cut out
    of it, `b(cv)` seen through the letters, the word zooming about a point
    inside one of its letters until that letter covers the frame at `p` = 1.

    `word` starts as large as fits in `fill` of the frame (`font` only
    picks the typeface and weight). `ease` shapes the zoom on a log scale
    (default: a slow start that rushes at the end). A real film calls it
    inside its own overlap, like any `transition(cv, a, b, p)`."""
    font = font or demo.font(400, 900)
    path, w, h, (px, py), clear = _word(word, font)
    W, H = cv.width, cv.height
    s0 = min(fill * W / w, fill * H / h)
    ox, oy = (W - w * s0) / 2, (H - h * s0) / 2   # the word centred at the start
    fx, fy = ox + px * s0, oy + py * s0            # the pivot on screen stays put
    reach = max(math.hypot(fx - x, fy - y) for x in (0, W) for y in (0, H))
    s1 = reach / clear * 1.05                      # the pivot's letter then covers every corner
    u = (ease or (lambda t: t ** 2.4))(vb.clamp01(p))
    s = s0 * (s1 / s0) ** u
    a(cv)
    c = cv.ctx
    c.save()
    c.translate(fx - px * s, fy - py * s)
    c.scale(s, s)
    c.new_path()
    c.append_path(path)
    c.restore()
    c.save()
    c.clip()
    b(cv)
    c.restore()


def _demo_ease(t, hold=0.8, k=0.04):
    """The demo's zoom: a gentle push (to `k` of the log-scale zoom, about
    1.1x) for the first `hold` of the move, so OPEN stays whole and readable
    with the next scene in its letters, then a rush through one letter. The
    two parts meet at the same speed."""
    if t < hold:
        return k * t / hold
    x = (t - hold) / (1 - hold)
    lead = k * (1 - hold) / (hold * (1 - k))
    return k + (1 - k) * (lead * x + (1 - lead) * x * x)


def _demo_reveal(cv, a, b, p):
    text_mask_reveal(cv, a, b, p, ease=_demo_ease)


def scene_a(cv):
    demo.scene_a(cv)
    cv.fill(demo.BG, alpha=0.35)   # dim the photo a touch so the bright cut-out letters read


CAPABILITY = Capability(
    id='text-mask-reveal',
    name='Text mask reveal',
    family='transitions',
    group='Shape and Mask',
    aliases=('letter mask reveal', 'type mask transition', 'text matte transition'),
    definition='A large word becomes a window cut into the current shot, showing the next one inside '
               'its letters, then zooms in until a single letter fills the screen.',
    phrasings=('the next scene appears inside the letters of a word that grows to take over the screen',
               'punch through a big title into the next shot',
               'zoom into the text and come out the other side in the new scene'),
    related=('text-reveal-through-shape-mask', 'character-rise', 'wipe-reveal', 'pixelation-reveal',
             'video-clipped-inside-letterforms', 'handwriting-reveal'),
    api=('videobuilder.capabilities.transitions.text_mask_reveal.text_mask_reveal',),
    demo=lambda: demo.two_scenes(_demo_reveal, seconds=3.2, start=0.3, length=2.5, a=scene_a),
)
