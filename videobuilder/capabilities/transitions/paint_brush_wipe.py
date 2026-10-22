"""Paint Brush Wipe: a broad brush sweeps back and forth across the frame in
rows, and wherever it has passed the incoming scene shows through, its
leading edge ragged like bristle tips."""
import math

from .. import _demo as demo
from ..schema import Capability


def _jitter(i, seed):
    """A repeatable pseudo-random number in [0, 1) for index `i`."""
    v = math.sin(i * 12.9898 + seed * 78.233) * 43758.5453
    return v - math.floor(v)


def _stroke(ctx, x0, x1, y0, y1, head, rightward, bristle, wobble, seed):
    """Add one painted band to the path: x from `x0` to `x1`, y from `y0` to
    `y1`, with wavy top and bottom edges and a ragged edge at `head` (the
    brush's leading side). Always wound the same way, so overlapping bands
    union under cairo's default winding rule."""
    step = 48.0
    top, bottom = [], []
    n = max(1, math.ceil((x1 - x0) / step))
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        top.append((x, y0 + wobble * math.sin(x / 90 + seed)))
        bottom.append((x, y1 + wobble * math.sin(x / 110 + seed * 2.3)))
    teeth = 18
    edge = []
    for k in range(teeth + 1):
        y = y0 + (y1 - y0) * k / teeth
        tip = bristle * (0.25 + 0.75 * _jitter(k, seed)) if 0 < k < teeth else bristle
        edge.append((head - tip if rightward else head + tip, y))
    if rightward:   # top left->right, ragged right side down, bottom right->left
        pts = top + edge + bottom[::-1]
    else:           # top left->right, straight right side, bottom right->left, ragged left side up
        pts = top + bottom[::-1] + edge[::-1]
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def paint_brush_wipe(cv, a, b, p, rows=4, bristle=70, wobble=10, overlap=0.12, seed=1):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)`, then `b(cv)` showing
    through the strokes painted so far. The brush crosses the frame `rows`
    times, alternating direction, top row first; `overlap` is how much of a
    row's time it shares with the next, `bristle` the depth of the ragged
    leading edge, `wobble` the waviness of the stroke's sides.

    In a film, call it inside a two-shot overlap, e.g.
    `paint_brush_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    a(cv)
    if p <= 0:
        return
    w, h = cv.width, cv.height
    band = h / rows
    pad = band * 0.18            # rows overlap so their wavy sides leave no gaps
    span = w + 2 * bristle       # the head travels from just off one side to just off the other
    slot = 1 / (rows - (rows - 1) * overlap)
    ctx = cv.ctx
    ctx.save()
    ctx.new_path()
    any_paint = False
    for i in range(rows):
        q = min(1.0, max(0.0, (p - i * slot * (1 - overlap)) / slot))
        if q <= 0:
            continue
        q = 1 - (1 - q) ** 1.6   # each stroke slows a little as it lands
        rightward = i % 2 == 0
        y0 = -pad if i == 0 else i * band - pad
        y1 = h + pad if i == rows - 1 else (i + 1) * band + pad
        travel = q * span
        if rightward:
            x0, x1 = -bristle - 20, -bristle + travel
            head = x1
        else:
            x0, x1 = w + bristle - travel, w + bristle + 20
            head = x0
        _stroke(ctx, x0, x1, y0, y1, head, rightward, bristle, wobble, seed + i * 7.1)
        any_paint = True
    if any_paint:
        ctx.clip()
        b(cv)
    ctx.restore()


CAPABILITY = Capability(
    id='paint-brush-wipe',
    name='Paint brush wipe',
    family='transitions',
    group='Organic and Fluid',
    aliases=('brush stroke wipe', 'paint reveal', 'brush reveal'),
    definition='A wide brush drags across the picture in rows, and each rough-edged stroke it leaves '
               'is a window onto the next scene until the whole frame is painted over.',
    phrasings=('paint the next shot on with big brush strokes',
               'brush the new scene across the old one, row by row',
               'a wipe that looks like someone painting over the screen'),
    related=('brush-stroke-paint-reveal', 'spiral-wipe', 'diagonal-wipe', 'corner-wipe', 'drip-wipe',
             'box-wipe'),
    api=('videobuilder.capabilities.transitions.paint_brush_wipe.paint_brush_wipe',),
    demo=lambda: demo.two_scenes(paint_brush_wipe, start=0.6, length=1.8),
)
