"""Cel Shading Look: a round form lit in a few flat tones with hard edges
between them -- no gradients -- so as the light moves, the shadow shapes
slide across it like painted cels."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Technique

CUTS = (0.0, 0.4, 0.93)   # light levels (N.L) where the tone steps up: core shadow, half-tone, base, highlight
STEPS = 96                # points along each band's edge


def _unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def _band_path(ctx, cx, cy, r, light, cut):
    """Put on `ctx` the path of the part of a sphere (centre (cx, cy), radius
    `r`, seen face on) whose light level `normal . light` is at least `cut`.
    `light` points from the sphere to the light, screen axes: x right, y down,
    z towards the viewer. Returns False when that part is out of sight."""
    lx, ly, lz = _unit(light)
    rho = math.hypot(lx, ly)
    if rho < 1e-4:                       # light straight on: nudge it so the axes below exist
        lx, ly, lz = _unit((1e-3, 0.0, lz))
        rho = math.hypot(lx, ly)
    s = math.sqrt(max(0.0, 1 - cut * cut))
    ux, uy = ly / rho, -lx / rho         # u: across the light, in the screen plane
    vx, vy = -lz * uy, lz * ux           # v = light x u; its z part is -rho

    def point(t):  # a point on the band's edge circle, projected
        return (cx + r * (cut * lx + s * (math.cos(t) * ux + math.sin(t) * vx)),
                cy + r * (cut * ly + s * (math.cos(t) * uy + math.sin(t) * vy)))

    def lit(x, y):  # light level of the visible surface point over unit-disc (x, y)
        return x * lx + y * ly + math.sqrt(max(0.0, 1 - x * x - y * y)) * lz

    ctx.new_path()
    k = cut * lz / (s * rho) if s > 1e-6 else math.copysign(2.0, cut * lz)
    if k >= 1:                            # the band's whole edge faces us: an ellipse
        for i in range(STEPS):
            ctx.line_to(*point(2 * math.pi * i / STEPS))
        ctx.close_path()
        if lit(cut * lx, cut * ly) < cut:  # the band is outside the ellipse: the disc minus it
            ctx.new_sub_path()
            ctx.arc_negative(cx, cy, r, 0, -2 * math.pi)
        return True
    if k <= -1:                           # the edge is all round the back: everything or nothing
        if rho > cut:
            ctx.arc(cx, cy, r, 0, 2 * math.pi)
            return True
        return False
    a0 = math.pi - math.asin(k)           # the visible stretch of the edge: sin(t) <= k
    a1 = 2 * math.pi + math.asin(k)
    for i in range(STEPS + 1):
        ctx.line_to(*point(a0 + (a1 - a0) * i / STEPS))
    # Back to the start along the rim, the way that runs through the lit side.
    end, start = point(a1), point(a0)
    e = math.atan2(end[1] - cy, end[0] - cx)
    b = math.atan2(start[1] - cy, start[0] - cx)
    sweep = (b - e) % (2 * math.pi)
    mid = e + sweep / 2
    if math.cos(mid) * lx + math.sin(mid) * ly >= cut:
        ctx.arc(cx, cy, r, e, e + sweep)
    else:
        ctx.arc_negative(cx, cy, r, e, e + sweep - 2 * math.pi)
    ctx.close_path()
    return True


def cel_tones(color, shadow='#000000', light='#ffffff'):
    """Four flat tones for `color`, darkest first: core shadow, half-tone,
    base and highlight -- the palette `cel_sphere` steps through."""
    return (kit.mix(color, shadow, 0.62), kit.mix(color, shadow, 0.34), color,
            kit.mix(color, light, 0.55))


def cel_sphere(cv, cx, cy, r, light, tones, cuts=CUTS, outline=None, width=4):
    """Draw a cel-shaded ball centred at (cx, cy), radius `r`: flat `tones`
    (darkest first, one more than `cuts`) with hard edges where the light
    level `normal . light` crosses each of `cuts`. `light` is the direction
    towards the light, (x right, y down, z towards the viewer); move it over
    time and the shadow shapes slide across the ball. `outline` adds an ink
    line round the rim, `width` px."""
    if len(tones) != len(cuts) + 1:
        raise ValueError(f'cel_sphere: {len(cuts)} cuts need {len(cuts) + 1} tones, got {len(tones)}')
    ctx = cv.ctx
    ctx.save()
    ctx.new_path()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.clip()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    cv.fill(tones[0])
    for cut, tone in zip(cuts, tones[1:]):
        if _band_path(ctx, cx, cy, r, light, cut):
            ctx.set_source_rgba(*vb.rgba(tone))
            ctx.fill()
    ctx.restore()
    if outline:
        cv.arc(cx, cy, r, 0, 2 * math.pi, outline, width=width)
    cv.mark('cel', cx - r, cy - r, 2 * r, 2 * r)


def draw(n, cv):
    p = demo.phase(n, 0.0, demo.SECONDS)
    a = -2.3 + 1.9 * math.pi * p                     # the light swings round...
    lz = 0.3 + 0.62 * math.cos(2 * math.pi * p)      # ...and dips behind the ball midway
    rho = math.sqrt(1 - lz * lz)
    light = (rho * math.cos(a), rho * math.sin(a), lz)
    cx, cy, r = demo.W / 2, demo.H / 2 - 22, 180
    floor = cy + r + 34
    # A hard-edged cast shadow on the ground, thrown away from the light.
    ctx = cv.ctx
    ctx.new_path()
    ctx.save()
    ctx.translate(cx - light[0] * 110, floor)
    ctx.scale(1, 0.16)
    ctx.arc(0, 0, r * 0.95, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(*vb.rgba('#000000', 0.5))
    ctx.fill()
    cel_sphere(cv, cx, cy, r, light, cel_tones(demo.ACCENT, shadow=demo.BG), outline=demo.INK, width=3)


TECHNIQUE = Technique(
    id='cel-shading-look',
    name='Cel shading look',
    family='shapes',
    group='Hand-drawn & traditional',
    aliases=('toon shading', 'cel shading', 'cel-shaded', 'two-tone cel', 'hard-edged shading',
             'flat shading'),
    definition='A form is coloured in a few flat tones with crisp edges between light and shadow, '
               'like a cartoon cel, and those shadow shapes slide across it as the light moves.',
    phrasings=('make it look like a cartoon with flat, hard shadows',
               'anime-style shading where the light and dark areas have sharp edges',
               'shade the ball in solid bands of colour instead of a smooth gradient'),
    related=('gooch-shading', 'low-poly-faceting', 'cross-hatch-shading', 'fresnel-edge-glow',
             'matcap-shading', 'heat-haze'),
    api=('videobuilder.techniques.shapes.cel_shading_look.cel_sphere',
         'videobuilder.techniques.shapes.cel_shading_look.cel_tones'),
    demo=lambda: demo.film(draw),
)
