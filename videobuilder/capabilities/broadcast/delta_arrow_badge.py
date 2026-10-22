"""Delta Arrow Badge: beside a stat, a small pill pops in holding an arrow
(up or down) and the signed change from the previous value, tinted by
direction, so the number reads as "up 19" or "down 6" at a glance."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

UP = demo.TEAL
DOWN = demo.ACCENT


def delta_text(delta, decimals=0, suffix=''):
    """The badge's label for a change of `delta`: signed, with a real minus
    sign, e.g. `+19`, `−6`, `+2.5%`."""
    sign = '+' if delta > 0 else '−' if delta < 0 else '±'
    return f'{sign}{abs(delta):.{decimals}f}{suffix}'


def _arrow(cv, cx, cy, s, up, color, alpha):
    """A filled arrow `s` px tall centred on (cx, cy), pointing up or down."""
    c = cv.ctx
    d = -1 if up else 1                     # tip direction in y
    head, shaft = s * 0.55, s * 0.2
    tip, neck, tail = cy + d * s / 2, cy + d * (s / 2 - head), cy - d * s / 2
    c.new_path()
    c.move_to(cx, tip)
    c.line_to(cx + s * 0.42, neck)
    c.line_to(cx + shaft / 2, neck)
    c.line_to(cx + shaft / 2, tail)
    c.line_to(cx - shaft / 2, tail)
    c.line_to(cx - shaft / 2, neck)
    c.line_to(cx - s * 0.42, neck)
    c.close_path()
    r, g, b, a = vb.canvas.rgba(color)
    c.set_source_rgba(r, g, b, a * alpha)
    c.fill()


def draw_delta_badge(cv, delta, x, cy, progress, size=40, decimals=0, suffix='', up_color=UP,
                     down_color=DOWN):
    """Draw a delta badge whose left edge is at `x`, centred vertically on
    `cy`, `size` px tall, for a change of `delta` (`delta_text` formats it).
    `progress` 0 -> 1 runs its entrance: the pill pops in from small with a
    slight overshoot, then the arrow slides in the direction it points and
    the value fades up. Positive is `up_color`, negative or zero
    `down_color`. Returns the badge's Box."""
    if progress <= 0:
        return vb.Box(x, cy - size / 2, 0, size)
    up = delta > 0
    color = up_color if up else down_color
    label = delta_text(delta, decimals, suffix)
    f = demo.font(round(size * 0.55), 800)
    tw = vb.text.measure(label, f)
    pad, arrow = size * 0.32, size * 0.5
    w = pad + arrow + size * 0.22 + tw + pad
    pop = vb.ease_out_back(vb.clamp01(progress / 0.6))
    inner = vb.ease_out_quint(vb.clamp01((progress - 0.3) / 0.7))
    with cv.layer(dx=x + w / 2, dy=cy, scale=max(pop, 0.0)):
        cv.rect(-w / 2, -size / 2, w, size, color, radius=size * 0.28, alpha=0.18)
        cv.rect(-w / 2, -size / 2, w, size, color, radius=size * 0.28, alpha=0.18 * (1 - inner))
        slide = (1 - inner) * size * 0.45 * (1 if up else -1)
        with cv.clip(-w / 2, -size / 2, w, size, radius=size * 0.28):
            _arrow(cv, -w / 2 + pad + arrow / 2, slide, arrow, up, color, inner)
        th = vb.text.line_height(f)
        vb.text.draw(cv, [label], f, -w / 2 + pad + arrow + size * 0.22, -th / 2, color, alpha=inner)
    box = vb.Box(x, cy - size / 2, w, size)
    cv.mark('delta', *box)
    return box


ROWS = (('Visitors', 42, 61), ('Signups', 68, 74), ('Churn', 55, 49), ('Refunds', 87, 80))
TOP, ROW_H = 120, 92


def draw(n, cv):
    tick = vb.ease_in_out_quart(demo.phase(n, 0.3, 1.2))
    lf, vf = demo.font(30, 700), demo.mono(48, 700)
    head = demo.font(18, 700)
    vb.text.draw(cv, ['PREVIOUS'], head, 360, TOP - 48, demo.MUTED)
    vb.text.draw(cv, ['NOW'], head, 520, TOP - 48, demo.MUTED)
    for i, (name, before, after) in enumerate(ROWS):
        cy = TOP + ROW_H * i + ROW_H / 2
        vb.text.draw(cv, [name], lf, 120, cy - vb.text.line_height(lf) / 2, demo.MUTED)
        vh = vb.text.line_height(vf)
        vb.text.draw(cv, [str(before)], vf, 360, cy - vh / 2, demo.MUTED, alpha=0.7)
        now = round(before + (after - before) * tick)
        vb.text.draw(cv, [str(now)], vf, 520, cy - vh / 2, demo.INK)
        cv.line(120, cy + ROW_H / 2, demo.W - 120, cy + ROW_H / 2, demo.LINE, width=2)
        draw_delta_badge(cv, after - before, 640, cy, demo.phase(n, 1.25 + 0.2 * i, 1.85 + 0.2 * i), size=46)


TECHNIQUE = Technique(
    id='delta-arrow-badge',
    name='Delta arrow badge',
    family='broadcast',
    group='Stats',
    aliases=('change indicator', 'up-down badge', 'delta chip', 'trend badge'),
    definition='A little coloured tag with an up or down arrow and the signed difference pops in next to a '
               'number, showing at once how far it rose or fell since last time.',
    phrasings=('put a green up arrow with +19 next to the number',
               'show how much each stat went up or down beside it',
               'add a little change pill to each value, red when it dropped'),
    related=('badge-count-bump', 'arrow-slide', 'live-indicator-pulse', 'badge-stamp-impact',
             'gradient-shift-button', 'striped-progress-bar'),
    api=('videobuilder.techniques.broadcast.delta_arrow_badge.draw_delta_badge',
         'videobuilder.techniques.broadcast.delta_arrow_badge.delta_text'),
    demo=lambda: demo.film(draw),
)
