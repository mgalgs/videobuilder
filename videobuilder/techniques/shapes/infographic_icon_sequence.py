"""Infographic icon sequence: a row of icon badges pops in one after another,
each with its label, while a connecting line runs on from badge to badge, so
the eye reads them as ordered steps."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique


# ---- icon glyphs: each draws in a unit box centred on (0, 0), radius ~1, stroked in the current colour ----

def _person(c):
    c.new_sub_path()
    c.arc(0, -0.42, 0.26, 0, 2 * math.pi)
    c.move_to(-0.5, 0.55)
    c.curve_to(-0.5, 0.0, 0.5, 0.0, 0.5, 0.55)


def _gear(c):
    teeth = 8
    for i in range(teeth):
        a = 2 * math.pi * i / teeth
        c.move_to(0.38 * math.cos(a), 0.38 * math.sin(a))
        c.line_to(0.6 * math.cos(a), 0.6 * math.sin(a))
    c.new_sub_path()
    c.arc(0, 0, 0.38, 0, 2 * math.pi)
    c.new_sub_path()
    c.arc(0, 0, 0.14, 0, 2 * math.pi)


def _chart(c):
    c.move_to(-0.55, 0.55)
    c.line_to(0.55, 0.55)
    for x, top in ((-0.3, 0.15), (0.0, -0.15), (0.3, -0.5)):
        c.move_to(x, 0.4)
        c.line_to(x, top)


def _check(c):
    c.move_to(-0.45, 0.02)
    c.line_to(-0.12, 0.35)
    c.line_to(0.48, -0.3)


ICONS = {'person': _person, 'gear': _gear, 'chart': _chart, 'check': _check}


def draw_icon(cv, icon, cx, cy, size, color, width=None, alpha=1.0):
    """Stroke `icon` (a name from `ICONS`, or any `f(ctx)` that builds a path
    in a unit box about the origin) centred at (cx, cy), `size` px across."""
    glyph = ICONS.get(icon, icon) if isinstance(icon, str) else icon
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.scale(size / 2, size / 2)
    c.new_path()
    glyph(c)
    c.restore()
    c.set_source_rgba(*rgba(color, alpha))
    c.set_line_width(width or size * 0.075)
    c.set_line_cap(1)   # round
    c.set_line_join(1)  # round
    c.stroke()


def stagger(p, i, count, overlap=0.4):
    """Item `i` of `count`'s own progress 0 -> 1 while the whole sequence runs
    `p` 0 -> 1. Each item takes the same time; `overlap` (0..1) is how much of
    one item's span the next one starts inside."""
    span = 1 / (count - (count - 1) * overlap) if count > 1 else 1
    return vb.clamp01((p - i * span * (1 - overlap)) / span)


def icon_sequence(cv, items, cx, cy, p, gap=220, radius=52, color=demo.ACCENT, ink=demo.INK,
                  line=demo.MUTED, label_font=None, overlap=0.35):
    """Draw `items` -- `(icon, label)` pairs, `icon` as in `draw_icon` -- as a
    centred row of round badges at progress `p` (0 -> 1). Badge `i` pops in
    with an overshoot, its glyph fades up and its label rises in beneath; the
    connector from the previous badge runs on just before it arrives. `gap` is centre
    to centre. Returns each badge's Box (badges not yet in still have one)."""
    count = len(items)
    f = label_font or demo.font(24, 700)
    x0 = cx - gap * (count - 1) / 2
    boxes = []
    for i, (icon, label) in enumerate(items):
        q = stagger(p, i, count, overlap)
        x = x0 + i * gap
        if i > 0:  # the line from the previous badge runs on, then this one pops
            run = vb.ease_out_quint(vb.clamp01(q / 0.3))
            a, b = x - gap + radius + 10, x - radius - 10
            if run > 0:
                cv.line(a, cy, a + (b - a) * run, cy, line, width=5)
        pop = vb.ease_out_back(vb.clamp01((q - 0.2) / 0.4)) if q > 0.2 else 0
        if pop > 0:
            cv.shadow(x - radius * pop, cy - radius * pop, 2 * radius * pop, 2 * radius * pop,
                      radius=radius * pop, dy=7, blur=18, color=(0, 0, 0, 0.4))
            demo.dot(cv, x, cy, radius * pop, color=color)
            glyph = vb.clamp01((q - 0.4) / 0.3)
            draw_icon(cv, icon, x, cy, radius * 1.15 * max(pop, 0.01), ink, alpha=glyph)
        rise = vb.ease_out_quint(vb.clamp01((q - 0.5) / 0.5))
        if rise > 0:
            demo.word(cv, label, x, cy + radius + 36 + 16 * (1 - rise), font=f, color=ink, alpha=rise)
        boxes.append(vb.Box(x - radius, cy - radius, 2 * radius, 2 * radius))
    return boxes


STEPS = (('person', 'Sign up'), ('gear', 'Set up'), ('chart', 'Track'), ('check', 'Done'))


def draw(n, cv):
    boxes = icon_sequence(cv, STEPS, demo.W / 2, demo.H / 2 - 24, demo.phase(n, 0.3, 2.5))
    for i, box in enumerate(boxes):
        cv.mark(f'icon{i}', *box)


TECHNIQUE = Technique(
    id='infographic-icon-sequence',
    name='Infographic icon sequence',
    family='shapes',
    group='Explainer & infographic',
    aliases=('icon reveal sequence', 'staggered icon reveal', 'process icons', 'icon steps'),
    definition='A row of simple icons in badges appears one at a time, each popping in with its label '
               'while a line links it to the one before, so they read as ordered steps.',
    phrasings=('show the four steps as icons that pop in one after another',
               'icons appear in a row with labels underneath, joined by a line',
               'an explainer graphic where each stage gets its own little icon'),
    related=('pictogram-counting', 'flowchart-build', 'step-by-step-process-reveal', 'logo-build-on-reveal',
             'slopegraph-reveal', 'line-draw-logo-reveal'),
    api=('videobuilder.techniques.shapes.infographic_icon_sequence.icon_sequence',
         'videobuilder.techniques.shapes.infographic_icon_sequence.draw_icon',
         'videobuilder.techniques.shapes.infographic_icon_sequence.stagger'),
    demo=lambda: demo.film(draw),
)
