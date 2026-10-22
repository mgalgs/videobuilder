"""Pointer Parallax Layers: a framed scene of stacked flat layers that each
slide a different amount as the pointer moves over it, the near ones furthest,
so the flat picture reads as having depth."""
import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Capability


def pointer_shift(pointer, box, depth, reach=40):
    """How far a layer at `depth` slides, as (dx, dy), with the pointer at
    `pointer` (x, y) over `box`. The pointer's distance from the box's centre
    is taken as -1 -> 1 on each axis (clamped at the edges) and scaled by
    `depth * reach` px. Depth 0 stays put, 1 slides the full `reach`; layers
    slide against the pointer, as if seen through a window; a negative
    `reach` makes them follow it instead."""
    x, y, w, h = box
    nx = max(-1.0, min(1.0, (pointer[0] - (x + w / 2)) / (w / 2)))
    ny = max(-1.0, min(1.0, (pointer[1] - (y + h / 2)) / (h / 2)))
    return -nx * depth * reach, -ny * depth * reach


def draw_pointer_parallax(cv, box, layers, pointer, reach=40, radius=0):
    """Draw `layers`, a list of `(depth, draw)` pairs listed far first, inside
    `box` (x, y, w, h) with the pointer at `pointer`. Each `draw(cv)` paints
    its layer at rest in frame px and is slid by `pointer_shift`; everything
    is clipped to the box (rounded by `radius`), so paint each layer `reach`
    px past the box's edges to keep them covered."""
    with cv.clip(*box, radius=radius):
        for depth, draw in layers:
            dx, dy = pointer_shift(pointer, box, depth, reach)
            with cv.layer(dx=dx, dy=dy):
                draw(cv)


def draw_cursor(cv, x, y, size=26, color=demo.INK, outline='#000000'):
    """An arrow mouse pointer with its tip at (x, y), `size` px tall."""
    s = size / 26
    pts = [(0, 0), (0, 22), (6, 17), (10, 26), (14, 24), (10, 16), (17, 16)]
    pts = [(x + px * s, y + py * s) for px, py in pts]
    paths.draw(cv, pts, outline, width=3 * s, closed=True)
    paths.draw(cv, pts, color, fill=True)


BOX = (demo.W / 2 - 330, demo.H / 2 - 200, 660, 400)
PAD = 70  # each layer is painted this far past the box, more than the widest slide


def _band(base, amp, seed, color):
    """A rolling ridge across the box from y `base`, closed down past its bottom."""
    x, y, w, h = BOX
    ridge = vb.parallax.ridge(w + 2 * PAD, amp, seed=seed, bumps=(1, 2), step=12)
    pts = [(x - PAD + px, base + py - amp) for px, py in ridge]
    pts += [(x + w + PAD, y + h + PAD), (x - PAD, y + h + PAD)]
    return lambda cv: paths.draw(cv, pts, color, fill=True)


def _sky(cv):
    x, y, w, h = BOX
    steps = 12
    cv.rect(x - PAD, y - PAD, w + 2 * PAD, h + 2 * PAD, '#1d2340')
    for i in range(steps):  # a stepped dusk glow, brighter toward the horizon
        cv.rect(x - PAD, y - PAD + (h + 2 * PAD) * i / steps, w + 2 * PAD, (h + 2 * PAD) / steps,
                '#4a5590', alpha=0.6 * i / (steps - 1))


def _moon(cv):
    x, y, w, h = BOX
    demo.dot(cv, x + w * 0.74, y + h * 0.26, 42, color='#f2b632')


def _peaks(cv):
    x, y, w, h = BOX
    b = y + h * 0.72
    pts = [(x - PAD, b), (x + w * 0.2, y + h * 0.3), (x + w * 0.42, b - h * 0.12),
           (x + w * 0.62, y + h * 0.4), (x + w + PAD, b + h * 0.05), (x + w + PAD, y + h + PAD),
           (x - PAD, y + h + PAD)]
    paths.draw(cv, pts, '#6670a8', fill=True)


def _trees(cv):
    x, y, w, h = BOX
    _band(y + h * 0.86, 40, 5, '#1b2036')(cv)
    for tx, th in ((0.1, 150), (0.86, 110)):
        cx, base = x + w * tx, y + h * 0.9
        paths.draw(cv, [(cx, base - th), (cx + th * 0.2, base), (cx - th * 0.2, base)], '#141829', fill=True)


LAYERS = (
    (0.0, _sky),
    (0.15, _moon),
    (0.35, _peaks),
    (0.65, _band(BOX[1] + BOX[3] * 0.7, 46, 2, '#3d4675')),
    (1.0, _trees),
)

# Where the pointer wanders, (seconds, x, y): in from the centre, up right, across left, down.
_X, _Y, _W, _H = BOX
ROUTE = ((0.0, _X + _W * 0.5, _Y + _H * 0.55), (0.3, _X + _W * 0.5, _Y + _H * 0.55),
         (1.0, _X + _W * 0.92, _Y + _H * 0.12), (1.9, _X + _W * 0.08, _Y + _H * 0.3),
         (2.6, _X + _W * 0.45, _Y + _H * 0.92), (3.0, _X + _W * 0.5, _Y + _H * 0.6))


def draw(n, cv):
    t = n / demo.FPS
    ts = [k[0] for k in ROUTE]
    px = vb.interpolate(t, ts, [k[1] for k in ROUTE], ease=vb.ease_in_out_quart)
    py = vb.interpolate(t, ts, [k[2] for k in ROUTE], ease=vb.ease_in_out_quart)
    x, y, w, h = BOX
    cv.shadow(x, y, w, h, radius=22, dy=12, blur=36, color=(0, 0, 0, 0.5))
    draw_pointer_parallax(cv, BOX, LAYERS, (px, py), reach=44, radius=22)
    cv.outline(x, y, w, h, demo.LINE, width=2, radius=22)
    cv.mark('scene', *BOX)
    draw_cursor(cv, px, py)
    cv.mark('pointer', px, py, 18, 26)


CAPABILITY = Capability(
    id='pointer-parallax-layers',
    name='Pointer parallax layers',
    family='ui',
    group='Cursor & hover',
    aliases=('mouse parallax', 'depth follow', 'hover parallax', 'cursor parallax'),
    definition='As the mouse pointer moves over a picture built from flat cut-out layers, each layer '
               'slides by a different amount, the nearest the most, so the scene seems to have depth.',
    phrasings=('the layers of the illustration shift with the mouse to give it depth',
               'when the cursor moves, the foreground moves more than the background',
               'a hover effect where the scene tilts in layers as you move the pointer around'),
    related=('parallax-layers', 'parallax-letter-layers', 'parallax-slide', 'scroll-parallax-layers',
             'two-point-five-d-photo-parallax', 'layered-fog-bands'),
    api=('videobuilder.capabilities.ui.pointer_parallax_layers.draw_pointer_parallax',
         'videobuilder.capabilities.ui.pointer_parallax_layers.pointer_shift',
         'videobuilder.capabilities.ui.pointer_parallax_layers.draw_cursor'),
    demo=lambda: demo.film(draw),
)
