"""Cross-hatch shading: a form is shaded only with ruled ink lines. Where it
is lit the paper shows through; as it turns away from the light one set of
lines comes in, then a second set crossing it, then a third, each thickening
-- so the darkness is the density of the hatching. Move the light and the
hatching drifts across the form."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

ANGLES = (math.radians(-38), math.radians(52), math.radians(8))   # each layer's line direction


def hatch(cv, x, y, w, h, darkness, color='#000000', spacing=11, angles=ANGLES, weight=None, step=6,
          alpha=1.0):
    """Shade the box (x, y, w, h) with layered hatching. `darkness(px, py)`
    gives 0 (paper) to 1 (darkest) at a point, or None outside the shape.
    Each of `angles` is one set of parallel lines `spacing` px apart; layer
    k of n starts where darkness passes k/n, and its lines swell from
    nothing to `weight` px (default 0.5 * spacing) across that slice, so
    light areas carry a few fine lines and dark ones a dense crossed mesh.
    Lines are built from `step`-px segments; clip `cv` first for a hard
    outline."""
    weight = spacing * 0.5 if weight is None else weight
    n = len(angles)
    ctx = cv.ctx
    ctx.save()
    ctx.set_source_rgba(*vb.rgba(color, alpha))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    cx, cy = x + w / 2, y + h / 2
    reach = math.hypot(w, h) / 2
    for k, ang in enumerate(angles):
        lo = k / n
        dx, dy = math.cos(ang), math.sin(ang)        # along the lines
        nx, ny = -dy, dx                             # across them
        off = (k * 0.37 % 1) * spacing               # stagger layers so crossings don't line up
        rows = int(reach / spacing) + 1
        for i in range(-rows, rows + 1):
            ox, oy = cx + nx * (i * spacing + off), cy + ny * (i * spacing + off)
            segs = int(2 * reach / step) + 1
            prev = None
            for j in range(segs + 1):
                s = -reach + j * step
                px, py = ox + dx * s, oy + dy * s
                d = darkness(px, py) if x <= px <= x + w and y <= py <= y + h else None
                lw = None if d is None else vb.clamp01((d - lo) * n) * weight
                if prev is not None and lw is not None and prev[2] + lw > 0.3:
                    ctx.set_line_width(max(0.4, (prev[2] + lw) / 2))
                    ctx.move_to(prev[0], prev[1])
                    ctx.line_to(px, py)
                    ctx.stroke()
                prev = None if lw is None else (px, py, lw)
    ctx.restore()


def sphere_darkness(cx, cy, r, light, ambient=0.08, deepest=0.88):
    """A `darkness(px, py)` for a ball centred at (cx, cy), radius `r`, lit
    from direction `light` (x right, y down, z towards the viewer): 1 - the
    Lambert light level, scaled to at most `deepest`, None off the ball."""
    m = math.sqrt(sum(c * c for c in light)) or 1.0
    lx, ly, lz = (c / m for c in light)

    def darkness(px, py):
        u, v = (px - cx) / r, (py - cy) / r
        q = 1 - u * u - v * v
        if q < 0:
            return None
        lit = max(0.0, u * lx + v * ly + math.sqrt(q) * lz)
        return deepest * vb.clamp01(1 - ambient - lit * (1 - ambient))
    return darkness


def hatch_sphere(cv, cx, cy, r, light, paper='#eef1f4', ink='#14181f', spacing=11, outline=True):
    """Draw a cross-hatched ball: a `paper` disc shaded with `ink` hatching
    from `light` (see `sphere_darkness`), clipped to the rim."""
    ctx = cv.ctx
    cv.sector(cx, cy, r, 0, 2 * math.pi, paper)
    ctx.save()
    ctx.new_path()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.clip()
    hatch(cv, cx - r, cy - r, 2 * r, 2 * r, sphere_darkness(cx, cy, r, light), ink, spacing)
    ctx.restore()
    if outline:
        cv.arc(cx, cy, r, 0, 2 * math.pi, ink, width=2.5)
    cv.mark('hatched', cx - r, cy - r, 2 * r, 2 * r)


def draw(n, cv):
    p = demo.phase(n, 0.0, demo.SECONDS)
    a = math.radians(-150) + math.radians(250) * (0.5 - 0.5 * math.cos(math.pi * p))   # light sweeps round
    light = (0.85 * math.cos(a), 0.85 * math.sin(a), 0.7)
    cx, cy, r = demo.W / 2, demo.H / 2 - 30, 200
    floor = cy + r + 26
    # a hatched cast shadow on the ground, thrown away from the light
    sx, ex, ey = cx - light[0] * 150, r * 1.05, r * 0.17

    def shadow(px, py):
        q = ((px - sx) / ex) ** 2 + ((py - floor) / ey) ** 2
        return None if q > 1 else 0.85 * (1 - q) ** 0.5
    hatch(cv, sx - ex, floor - ey, 2 * ex, 2 * ey, shadow, '#5d6675', spacing=9, angles=ANGLES[:2])
    hatch_sphere(cv, cx, cy, r, light, paper=demo.INK, ink=demo.BG)


TECHNIQUE = Technique(
    id='cross-hatch-shading',
    name='Cross-hatch shading',
    family='camera',
    group='Shader looks',
    aliases=('hatching', 'cross-hatching', 'hatch shading', 'line shading', 'engraving hatch'),
    definition='A form is shaded only with crossing sets of fine ink lines, sparse where light falls '
               'and packed into a dense, thick mesh in the shadows, like a pen or engraving drawing.',
    phrasings=('shade it like a pen-and-ink drawing with criss-cross lines',
               'make the shadows out of crossed lines that get denser where it is darker',
               'give the ball an old engraving look with hatched shading'),
    related=('cel-shading-look', 'low-poly-faceting', 'cross-processing', 'line-weave',
             'theme-swap-crossfade', 'rim-light'),
    api=('videobuilder.techniques.camera.cross_hatch_shading.hatch',
         'videobuilder.techniques.camera.cross_hatch_shading.hatch_sphere',
         'videobuilder.techniques.camera.cross_hatch_shading.sphere_darkness'),
    demo=lambda: demo.film(draw),
)
