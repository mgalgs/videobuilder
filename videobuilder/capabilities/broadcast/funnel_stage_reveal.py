"""Funnel stage reveal: a conversion funnel builds one band at a time from the
top down, each band narrower than the last, its count written inside and the
loss from the band above called out beside it."""
import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def _trapezoid(cv, cx, y0, y1, w0, w1, color, alpha=1.0):
    c = cv.ctx
    c.new_path()
    c.move_to(cx - w0 / 2, y0)
    c.line_to(cx + w0 / 2, y0)
    c.line_to(cx + w1 / 2, y1)
    c.line_to(cx - w1 / 2, y1)
    c.close_path()
    c.set_source_rgba(*rgba(color, alpha))
    c.fill()


def stage_progress(p, i, count, each=0.35):
    """Progress 0 -> 1 of stage `i` of `count` at overall progress `p`: each
    stage takes `each` of the run, starting evenly staggered so the last ends at 1."""
    step = (1 - each) / max(1, count - 1)
    return vb.clamp01((p - i * step) / each)


def drop_label(prev, value):
    """The loss from `prev` to `value` as a percentage, e.g. '-53%'."""
    return f'−{round(100 * (1 - value / prev))}%' if prev else ''


def draw_funnel(cv, stages, box, p, colors=(demo.ACCENT,), ink=demo.INK, muted=demo.MUTED,
                drop_color=demo.TEAL, neck=0.3, gap=8, label_w=150, each=0.35):
    """Draw `stages` -- `(name, value)` pairs, widest first -- as a funnel in
    `box` (a `vb.Box`) at reveal progress `p` (0 -> 1). Bands run from the full
    funnel width at the top down to `neck` of it at the bottom; each one drops
    open from its top edge in turn, then its value, its name (in a `label_w`
    column on the left) and its drop from the band above (on the right) fade
    in. `colors` cycle down the bands. Returns the stage bands' Boxes."""
    n = len(stages)
    fw = box.w - 2 * label_w
    cx = box.x + box.w / 2
    band = (box.h - gap * (n - 1)) / n
    width_at = lambda y: fw * (1 - (1 - neck) * (y - box.y) / box.h)  # noqa: E731
    value_f = demo.font(max(18, band * 0.42), 800)
    name_f = demo.font(max(14, band * 0.3), 700)
    drop_f = demo.mono(max(14, band * 0.3), 700)
    boxes = []
    for i, (name, value) in enumerate(stages):
        q = stage_progress(p, i, n, each)
        y0 = box.y + i * (band + gap)
        y1 = y0 + band
        boxes.append(vb.Box(cx - width_at(y0) / 2, y0, width_at(y0), band))
        if q <= 0:
            continue
        grow = vb.ease_out_quint(vb.clamp01(q / 0.6))
        yb = y0 + band * grow
        color = colors[i % len(colors)]
        _trapezoid(cv, cx, y0, yb, width_at(y0), width_at(yb), color, alpha=0.35 + 0.65 * grow)
        cv.line(cx - width_at(y0) / 2, y0 + 1, cx + width_at(y0) / 2, y0 + 1, ink, width=2, alpha=0.25 * grow)
        t = vb.ease_out_quint(vb.clamp01((q - 0.35) / 0.65))
        if t <= 0:
            continue
        mid = y0 + band / 2
        lh = vb.text.line_height(value_f)
        vb.text.draw(cv, [f'{value:,}'], value_f, cx - fw / 2, mid - lh / 2 + 12 * (1 - t), ink,
                     align='center', width=fw, alpha=t)
        lh = vb.text.line_height(name_f)
        vb.text.draw(cv, [name], name_f, box.x, mid - lh / 2, muted, align='right',
                     width=label_w - 24 - 20 * (1 - t), alpha=t)
        if i:
            vb.text.draw(cv, [drop_label(stages[i - 1][1], value)], drop_f,
                         box.right - label_w + 24 + 20 * (1 - t), mid - vb.text.line_height(drop_f) / 2,
                         drop_color, alpha=t)
    return boxes


STAGES = (('Visits', 48200), ('Sign-ups', 21700), ('Trials', 9400), ('Paid', 3800), ('Renewed', 2600))
SHADES = ('#ef5b4c', '#e5694f', '#d97753', '#cc8556', '#bf935a')


def draw(n, cv):
    box = vb.Box(demo.W * 0.1, demo.H * 0.14, demo.W * 0.8, demo.H * 0.72)
    for b in draw_funnel(cv, STAGES, box, demo.phase(n, 0.2, 2.5), colors=SHADES):
        cv.mark('stage', *b)


CAPABILITY = Capability(
    id='funnel-stage-reveal',
    name='Funnel stage reveal',
    family='broadcast',
    group='Charts',
    aliases=('funnel chart fill', 'conversion funnel', 'funnel chart build'),
    definition='A funnel chart builds band by band from the top, each band narrower than the one above, '
               'with its count inside and the percentage lost since the previous step beside it.',
    phrasings=('animate a conversion funnel where each step drops in under the last',
               'show the sales pipeline narrowing stage by stage with the drop-off at each step',
               'build up a funnel chart from visits down to paying customers'),
    related=('staggered-cascade-reveal', 'step-by-step-process-reveal', 'zoom-out-reveal', 'wireframe-reveal',
             'org-chart-grow', 'flowchart-build'),
    api=('videobuilder.capabilities.broadcast.funnel_stage_reveal.draw_funnel',
         'videobuilder.capabilities.broadcast.funnel_stage_reveal.stage_progress',
         'videobuilder.capabilities.broadcast.funnel_stage_reveal.drop_label'),
    demo=lambda: demo.film(draw),
)
