"""Ripple Displacement: rings spread out from a point like a stone dropped in
water, and as each crest passes through the text it pushes the letterforms
outward and pulls them back, so the strokes bulge, thin and wobble."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...canvas import rgba
from ...type import kit as type_kit


def ripple_offset(x, y, cx, cy, t, amplitude=14.0, wavelength=110.0, speed=520.0, decay=1.6, falloff=900.0):
    """How far (dx, dy) the point (x, y) is pushed `t` seconds after a drop
    at (cx, cy). Rings travel out at `speed` px/s, `wavelength` px apart; a
    point stays still until the leading ring reaches it, then swings along
    the radius by up to `amplitude` px. The swell dies away over time
    (`decay` per second) and with distance (`falloff` px)."""
    if t <= 0:
        return 0.0, 0.0
    dx, dy = x - cx, y - cy
    d = math.hypot(dx, dy)
    behind = speed * t - d             # how far the leading ring has passed this point
    if behind <= 0 or d < 1e-6:
        return 0.0, 0.0
    front = min(1.0, behind / wavelength)  # ease in under the first ring, no hard edge
    size = amplitude * front * math.exp(-decay * t) / (1 + d / falloff)
    push = size * math.sin(2 * math.pi * behind / wavelength)
    return dx / d * push, dy / d * push


def _segments(path, step):
    """A flattened cairo path as polylines, every edge cut into pieces no
    longer than `step` px so straight strokes can bend too."""
    out, cur, start = [], [], None
    for kind, pts in path:
        if kind == cairo.PATH_MOVE_TO:
            if cur:
                out.append(cur)
            cur, start = [pts], pts
        elif kind == cairo.PATH_LINE_TO:
            x0, y0 = cur[-1] if cur else pts
            x1, y1 = pts
            n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / step))
            cur.extend((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(1, n + 1))
        elif kind == cairo.PATH_CLOSE_PATH and cur:
            x0, y0 = cur[-1]
            x1, y1 = start
            n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / step))
            cur.extend((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(1, n))
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def text_polylines(text, font, x, y, step=3.0):
    """`text`'s glyph outlines, top-left at (x, y) as `text.draw` would set
    them, as closed polylines in film pixels: the shapes to displace."""
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
    ctx.set_tolerance(0.2)
    ctx.translate(x, y)
    ctx.append_path(type_kit._outline(text, font))
    ctx.identity_matrix()
    return _segments(ctx.copy_path_flat(), step)


def draw_ripple_text(cv, text, font, x, y, color, t, cx=None, cy=None, alpha=1.0, **wave):
    """Draw `text` from its top-left (x, y) with a ripple dropped at
    (cx, cy) (default: the line's centre) `t` seconds ago warping its
    letters; `wave` goes to `ripple_offset`. At `t <= 0` the line is plain.
    Returns the Box of the undisturbed line."""
    w, h = vb.text.block_size([text], font)
    cx = x + w / 2 if cx is None else cx
    cy = y + h / 2 if cy is None else cy
    ctx = cv.ctx
    ctx.save()
    ctx.new_path()
    for poly in text_polylines(text, font, x, y):
        for i, (px, py) in enumerate(poly):
            ox, oy = ripple_offset(px, py, cx, cy, t, **wave)
            (ctx.move_to if i == 0 else ctx.line_to)(px + ox, py + oy)
        ctx.close_path()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    ctx.set_source_rgba(*rgba(color, alpha))
    ctx.fill()
    ctx.restore()
    return vb.Box(x, y, w, h)


DROP = 0.5   # s into the demo the drop lands


def draw(n, cv):
    f = demo.font(210, 900)
    text = 'RIPPLE'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    t = n / demo.FPS - DROP
    # the drop lands just left of centre, so the rings sweep the word unevenly
    box = draw_ripple_text(cv, text, f, x, y, demo.INK, t, cx=demo.W / 2 - w * 0.1, cy=demo.H / 2,
                           amplitude=26, wavelength=130, speed=420, decay=0.7, falloff=1400)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='ripple-displacement',
    name='Ripple displacement',
    family='typography',
    group='Liquid and organic',
    aliases=('water ripple text', 'radial wave warp', 'ripple distortion'),
    definition='Rings of motion spread out from one spot through a word, and each one shoves the '
               'letter outlines back and forth as it passes, so the type swells and wobbles like a '
               'reflection on a pond.',
    phrasings=('make the title wobble like a stone was dropped into water next to it',
               'the letters ripple outward from the middle as if they were liquid',
               'a water-drop wave that warps the text and then calms down'),
    related=('ripple', 'height-field-ripples', 'refraction-ripple', 'wave-deformer',
             'text-reflection-shimmer', 'sine-wave-text'),
    api=('videobuilder.capabilities.typography.ripple_displacement.draw_ripple_text',
         'videobuilder.capabilities.typography.ripple_displacement.ripple_offset',
         'videobuilder.capabilities.typography.ripple_displacement.text_polylines'),
    demo=lambda: demo.film(draw),
)
