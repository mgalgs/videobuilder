"""Line-draw logo reveal: the same pen tracing round each outline then
filling solid as Stroke draw-on (`../typography/stroke_draw_on.py`, which
keeps the capability) -- its own alias "logo stroke reveal" is this logo
preset's own title: a thin line traces every contour of a logo mark, pen tip
leading, and once the outlines have closed the mark floods with its solid
colour -- holes left open -- and the wordmark traces in beside it. This
module's own code stays (a film may still import it), but it is no longer a
capability of its own."""
import math

import cairo

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..typography.stroke_draw_on import draw_stroke_on

MERGED_INTO = 'stroke-draw-on'


def draw_line_logo(cv, contours, p, color, fill=None, width=4, stagger=0.35, fill_from=0.65, head=True,
                   keep_line=0.0, ease=vb.ease_in_out_quart, alpha=1.0):
    """Draw a logo mark made of the closed point lists `contours` at progress
    `p` (0 -> 1). Until `fill_from` each contour's outline traces on in
    `color` from its own first point, one after another (`stagger` 0 = all
    together, 1 = strictly in turn), with a dot riding the pen tip when
    `head`. From `fill_from` to 1 the whole mark fills in `fill` (default
    `color`) with the even-odd rule, so a contour inside another is a hole;
    as it fills, the line fades to `keep_line` of its strength."""
    p = vb.clamp01(p)
    k = len(contours)
    if not k:
        return
    trace = vb.clamp01(p / fill_from) if fill_from > 0 else 1.0
    fade = vb.clamp01((p - fill_from) / (1 - fill_from)) if fill_from < 1 else float(p >= 1)
    each = 1.0 / (1 + (k - 1) * stagger)
    with cv.layer(opacity=alpha):
        if fade > 0:
            c = cv.ctx
            c.new_path()
            for pts in contours:
                c.move_to(*pts[0])
                for pt in pts[1:]:
                    c.line_to(*pt)
                c.close_path()
            c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            c.set_source_rgba(*vb.rgba(fill or color, vb.ease_out_quint(fade)))
            c.fill()
            c.set_fill_rule(cairo.FILL_RULE_WINDING)
        line_alpha = 1 - (1 - keep_line) * fade * fade
        for i, pts in enumerate(contours):
            q = ease(vb.clamp01((trace - i * each * stagger) / each))
            if q <= 0:
                continue
            seg = paths.reveal(pts, q, closed=True)
            paths.draw(cv, seg, color, width=width, alpha=line_alpha)
            if head and 0 < q < 1 and seg:
                demo.dot(cv, *seg[-1], r=width * 1.6, color=color)


def hexagon(cx, cy, r):
    """A flat-sided hexagon outline centred at (cx, cy), starting at its top-left corner."""
    return [(cx + r * math.cos(a), cy + r * math.sin(a))
            for a in (math.pi * (-2 / 3 + i / 3) for i in range(6))]


def monogram_m(cx, cy, w, h, stroke=0.24, dip=0.55):
    """A block capital M outline centred at (cx, cy), `w` by `h`; `stroke`
    is the leg thickness as a share of `w`, `dip` how far down the V reaches."""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    s = w * stroke
    return [(x0, y1), (x0, y0), (x0 + s, y0), (cx, y0 + h * dip * 0.7), (x1 - s, y0), (x1, y0), (x1, y1),
            (x1 - s, y1), (x1 - s, y0 + h * 0.42), (cx, y0 + h * dip + h * 0.22), (x0 + s, y0 + h * 0.42),
            (x0 + s, y1)]


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H * 0.42, demo.H * 0.24
    mark = [hexagon(cx, cy, r), monogram_m(cx, cy + r * 0.04, r * 0.92, r * 0.78)]
    draw_line_logo(cv, mark, demo.phase(n, 0.2, 2.0), demo.INK, fill=demo.ACCENT, width=4)
    f = demo.font(64, 800)
    name = 'MERIDIAN'
    w, h = vb.text.block_size([name], f)
    box = draw_stroke_on(cv, name, f, (demo.W - w) / 2, cy + r + demo.H * 0.08, demo.phase(n, 1.2, 2.7),
                         demo.INK, width=2, stagger=0.25)
    cv.mark('logo', cx - r, cy - r, 2 * r, 2 * r)
    cv.mark('wordmark', *box)
