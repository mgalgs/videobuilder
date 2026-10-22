"""Versus card: two panels slide in from opposite sides to face each other, a
VS badge pops in the gap between them, then each side's stat bars fill and
their numbers count up, row by row."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _ramp(p, a, b):
    return vb.clamp01((p - a) / (b - a))


def _panel(cv, x, y, w, h, name, stats, color, fill, side):
    """One side's card at its top-left (x, y): `name` up top, then one row per
    stat with its label, value counted to `fill` of the way, and a bar that
    grows from the card's outer edge toward the badge (`side` -1 left, 1 right)."""
    cv.shadow(x, y, w, h, radius=18, dy=10, blur=28, color=(0, 0, 0, 0.45))
    cv.rect(x, y, w, h, '#1c1e25', radius=18)
    cv.outline(x, y, w, h, demo.LINE, width=2, radius=18)
    cv.rect(x + 24, y + 22, 40, 5, color, radius=2.5)
    demo.word(cv, name, x + w / 2, y + 74, size=40, weight=800)
    lab, num = demo.mono(15, 600), demo.font(24, 800)
    top, row = y + 128, (h - 150) / max(1, len(stats))
    pad = 24
    for i, ((label, value, most), f) in enumerate(zip(stats, fill)):
        ry = top + i * row
        shown = str(round(value * f))
        vw = vb.text.measure(shown, num)
        if side < 0:
            vb.text.draw(cv, [label], lab, x + pad, ry + 6, demo.MUTED)
            vb.text.draw(cv, [shown], num, x + w - pad - vw, ry, demo.INK)
        else:
            vb.text.draw(cv, [shown], num, x + pad, ry, demo.INK)
            lw = vb.text.measure(label, lab)
            vb.text.draw(cv, [label], lab, x + w - pad - lw, ry + 6, demo.MUTED)
        track = w - 2 * pad
        by = ry + 38
        cv.rect(x + pad, by, track, 6, demo.LINE, radius=3)
        bw = track * f * value / most
        if bw > 0.5:
            bx = x + pad if side < 0 else x + w - pad - bw
            cv.rect(bx, by, bw, 6, color, radius=3)


def draw_versus_card(cv, cx, cy, left, right, stats, p, colors=(demo.ACCENT, demo.TEAL),
                     w=300, h=380, gap=120, slide=None):
    """Draw a head-to-head card centred at (cx, cy) at progress `p` (0 -> 1).

    `left` and `right` are the two names; `stats` is a list of
    `(left_label, left_value, right_label, right_value, most)` rows, `most`
    being the value a full bar stands for. Across `p`: the two panels slide in
    from opposite edges (0 -> 0.35, `slide` px, default the frame's width
    away), the VS badge pops (0.3 -> 0.45), then the rows fill and count up
    one after another (0.45 -> 1). Returns the badge's centre."""
    slide = cv.width if slide is None else slide
    s = vb.ease_out_expo(_ramp(p, 0.0, 0.35))
    off = (1 - s) * slide
    lx, rx = cx - gap / 2 - w, cx + gap / 2
    y = cy - h / 2
    n = len(stats)
    fills = [vb.ease_out_quint(_ramp(p, 0.45 + 0.35 * i / max(1, n), 0.45 + 0.35 * i / max(1, n) + 0.3))
             for i in range(n)]
    _panel(cv, lx - off, y, w, h, left, [(a, b, m) for a, b, _, _, m in stats], colors[0], fills, -1)
    _panel(cv, rx + off, y, w, h, right, [(c, d, m) for _, _, c, d, m in stats], colors[1], fills, 1)
    cv.mark('left', lx - off, y, w, h)
    cv.mark('right', rx + off, y, w, h)
    b = _ramp(p, 0.3, 0.45)
    if b > 0:
        r = 40 * vb.ease_out_back(b)
        demo.dot(cv, cx, cy, r + 4, color=demo.LINE)
        demo.dot(cv, cx, cy, r, color='#0e0f13')
        with cv.layer(opacity=b):
            demo.word(cv, 'VS', cx, cy, size=max(1, 30 * r / 40), weight=900)
        cv.mark('badge', cx - r, cy - r, 2 * r, 2 * r)
    return cx, cy


STATS = [('SPEED', 82, 'SPEED', 64, 100), ('POWER', 55, 'POWER', 91, 100),
         ('RANGE', 70, 'RANGE', 48, 100), ('CONTROL', 38, 'CONTROL', 77, 100)]


def draw(n, cv):
    draw_versus_card(cv, demo.W / 2, demo.H / 2, 'ALPHA', 'BETA', STATS, demo.phase(n, 0.15, 2.7))


CAPABILITY = Capability(
    id='versus-card',
    name='Versus card',
    family='broadcast',
    group='Comparisons',
    aliases=('VS card', 'head-to-head card', 'tale of the tape'),
    definition='Two rivals slide in on panels facing each other across a VS badge, '
               'then matching stat bars and numbers fill in on both sides for a side-by-side comparison.',
    phrasings=('put the two players head to head with their stats',
               'a VS screen comparing two teams number by number',
               'show both options side by side with a versus in the middle'),
    related=('card-deck-fan', 'stacked-card-reveal', 'graphic-match', 'sticky-card-stack-on-scroll', 'flip',
             'player-stat-card'),
    api=('videobuilder.capabilities.broadcast.versus_card.draw_versus_card',),
    demo=lambda: demo.film(draw),
)
