"""Dock magnification: a row of icons swells under the pointer as it glides
along, the icon beneath growing most and its neighbours less with distance,
the whole row widening so nothing overlaps."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

ICON_COLORS = ('#ef5b4c', '#f2a541', '#4fc3b0', '#5b8def', '#a77bea', '#e46aa8', '#7cc56b')


def magnification(distance, reach, peak=1.8):
    """Scale of one icon `distance` from the pointer: `peak` right under it,
    falling smoothly (a raised cosine) to 1 at `reach` and beyond."""
    d = abs(distance) / reach
    return 1.0 if d >= 1 else 1 + (peak - 1) * (0.5 + 0.5 * math.cos(math.pi * d))


def dock_layout(count, cx, baseline, pointer_x, size=96, gap=20, reach=260, peak=1.8, strength=1.0):
    """The `count` icons of a dock centred on `cx`, sitting on `baseline`, as
    one `vb.Box` each. Each icon scales by its rest centre's distance to
    `pointer_x` (`None`: the pointer is away); `strength` 0 -> 1 eases the
    whole effect in and out. Icons stay bottom-aligned and side by side, so
    the row widens about its centre as icons grow."""
    pitch = size + gap
    rest = [cx + (i - (count - 1) / 2) * pitch for i in range(count)]
    sizes = []
    for x in rest:
        s = 1.0 if pointer_x is None else magnification(x - pointer_x, reach, peak)
        sizes.append(size * (1 + (s - 1) * vb.clamp01(strength)))
    total = sum(sizes) + gap * (count - 1)
    x = cx - total / 2
    boxes = []
    for s in sizes:
        boxes.append(vb.Box(x, baseline - s, s, s))
        x += s + gap
    return boxes


def draw_dock(cv, boxes, colors=ICON_COLORS, shelf='#2a2c33', pad=10):
    """Draw a dock shelf behind `boxes` (from `dock_layout`) and a rounded,
    shaded tile for each icon, cycling through `colors`."""
    x0, x1 = boxes[0].x - pad, boxes[-1].x + boxes[-1].w + pad
    base = max(b.y + b.h for b in boxes)
    shelf_h = min(b.h for b in boxes) * 0.55 + 2 * pad
    cv.shadow(x0, base - shelf_h + pad, x1 - x0, shelf_h, radius=18, dy=8, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(x0, base - shelf_h + pad, x1 - x0, shelf_h, shelf, radius=18, alpha=0.9)
    for i, b in enumerate(boxes):
        r = b.w * 0.24
        cv.shadow(b.x, b.y, b.w, b.h, radius=r, dy=b.w * 0.06, blur=b.w * 0.18, color=(0, 0, 0, 0.45))
        cv.rect(b.x, b.y, b.w, b.h, colors[i % len(colors)], radius=r)
        cv.rect(b.x + b.w * 0.22, b.y + b.h * 0.22, b.w * 0.56, b.h * 0.56, demo.INK, radius=r * 0.6, alpha=0.3)


ARROW = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def _pointer(cv, x, y, s=1.1):
    pts = [(x + px * s, y + py * s) for px, py in ARROW]
    cv.shape_shadow(pts, dy=3, blur=6, color=(0, 0, 0, 0.5))
    ctx = cv.ctx
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgba(*vb.canvas.rgba('#ffffff'))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.canvas.rgba('#000000'))
    ctx.set_line_width(2)
    ctx.stroke()


def draw(n, cv):
    count, size, gap = 7, 60, 14
    baseline = demo.H - 120
    span = (count - 1) * (size + gap) / 2
    p = demo.phase(n, 0.3, 2.7)
    px = demo.W / 2 - span - 40 + (2 * span + 80) * vb.ease.bezier(0.45, 0, 0.55, 1)(p)
    strength = min(demo.phase(n, 0.2, 0.6), 1 - demo.phase(n, 2.5, 2.9))
    boxes = dock_layout(count, demo.W / 2, baseline, px, size=size, gap=gap, reach=170,
                        strength=strength)
    draw_dock(cv, boxes)
    _pointer(cv, px, baseline - size * 0.4)
    for i, b in enumerate(boxes):
        cv.mark(f'icon{i}', *b)


TECHNIQUE = Technique(
    id='dock-magnification',
    name='Dock magnification',
    family='ui',
    group='Cursor & hover',
    aliases=('dock zoom', 'fisheye dock', 'magnifying dock', 'hover magnify'),
    definition='As a pointer slides along a row of icons, the one beneath it grows largest and its '
               'neighbours swell less the farther away they sit, pushing the row wider as it passes.',
    phrasings=('icons get bigger as the mouse moves over them, like the Mac dock',
               'a bar of app icons that bulges up around the cursor',
               'the toolbar buttons zoom in a wave following the pointer'),
    related=('zoom-to-detail-magnifier', 'cursor-follow-auto-zoom', 'ui-walkthrough-camera-zoom',
             'scale-zoom-through', 'icon-hover-bounce', 'proximity-stagger'),
    api=('videobuilder.techniques.ui.dock_magnification.dock_layout',
         'videobuilder.techniques.ui.dock_magnification.magnification',
         'videobuilder.techniques.ui.dock_magnification.draw_dock'),
    demo=lambda: demo.film(draw),
)
