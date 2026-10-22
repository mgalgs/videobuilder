"""Leaderboard row swap: a ranked table whose order changes, each row sliding
up or down to its new place while the rank column stays put."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def row_slots(before, after, p, ease=vb.ease_in_out_quart):
    """Each key's slot (0 = top) at progress `p` of a reorder from the list
    `before` to the list `after` (the same keys, in a new order), as a dict of
    floats: a row moves from its old index to its new one along `ease`. Draw
    the rows at `top + slot * pitch`."""
    k = ease(vb.clamp01(p))
    old = {key: i for i, key in enumerate(before)}
    return {key: old[key] + (i - old[key]) * k for i, key in enumerate(after)}


def draw_order(before, after):
    """The keys in the order to draw them so rows climbing the table pass
    over the rows they overtake: still rows first, then fallers, then risers,
    biggest climb last."""
    old = {key: i for i, key in enumerate(before)}
    return sorted(after, key=lambda key: old[key] - after.index(key))


BEFORE = [('Okafor', 87), ('Lindqvist', 80), ('Moreau', 74), ('Tanaka', 70), ('Reyes', 61),
          ('Kowalski', 55), ('Haddad', 49)]
CLIMBER, GAIN = 'Reyes', 18


def draw(n, cv):
    count = demo.phase(n, 0.5, 1.0)         # the climber's points tick up first
    slide = demo.phase(n, 0.95, 1.95)       # then the table re-sorts
    lift = math.sin(math.pi * slide)        # the climber rises off the table while it moves
    points = dict(BEFORE)
    points[CLIMBER] += round(GAIN * vb.ease_out_expo(count))
    before = [name for name, _ in BEFORE]
    after = sorted(before, key=lambda name: -(dict(BEFORE)[name] + (GAIN if name == CLIMBER else 0)))
    slots = row_slots(before, after, slide)

    x, w, top, pitch, h = 230, demo.W - 430, 118, 56, 46
    label, small = demo.font(22, 800), demo.mono(14, 600)
    vb.text.draw(cv, ['STANDINGS'], small, x, top - 34, demo.MUTED)
    vb.text.draw(cv, ['PTS'], small, x + w - vb.text.measure('PTS', small), top - 34, demo.MUTED)
    for i in range(len(BEFORE)):            # rank numerals belong to the slot, not the row
        vb.text.draw(cv, [f'{i + 1:02d}'], demo.mono(18, 700), x - 44, top + i * pitch + h / 2 - 11, demo.MUTED)

    best = max(points.values())
    for name in draw_order(before, after):
        hot = name == CLIMBER
        y = top + slots[name] * pitch
        dx = -8 * lift if hot else 0
        s = 1 + 0.03 * lift if hot else 1.0     # grow about the row's centre
        with cv.layer(dx=(x + w / 2) * (1 - s), dy=(y + h / 2) * (1 - s), scale=s):
            if hot and lift > 0:
                cv.shadow(x + dx, y, w, h, radius=8, dy=7 * lift, blur=16, color=(0, 0, 0, 0.55 * lift))
            cv.rect(x + dx, y, w, h, '#2a2d36' if hot and count > 0 else '#1d1f26', radius=8)
            if hot and count > 0:
                cv.rect(x + dx, y, 4, h, demo.ACCENT, radius=2)
            vb.text.draw(cv, [name], label, x + dx + 20, y + h / 2 - 14, demo.INK)
            bx, bw = x + dx + 160, w - 250
            cv.rect(bx, y + h / 2 - 3, bw, 6, demo.LINE, radius=3)
            cv.rect(bx, y + h / 2 - 3, bw * points[name] / best, 6, demo.ACCENT if hot else demo.TEAL, radius=3)
            pts = str(points[name])
            vb.text.draw(cv, [pts], label, x + dx + w - 20 - vb.text.measure(pts, label), y + h / 2 - 14,
                         demo.ACCENT if hot else demo.INK)
        if hot:
            cv.mark('climber', x + dx, y, w, h)


CAPABILITY = Capability(
    id='leaderboard-row-swap',
    name='Leaderboard row swap',
    family='broadcast',
    group='Sports graphics',
    aliases=('standings reorder', 'rank swap animation', 'rank change'),
    definition='When a score changes in a ranked table, the affected rows glide up or down past each other '
               'into their new order while the place numbers stay fixed.',
    phrasings=('the team overtakes the others and its row slides up the standings',
               'animate the table re-sorting when the points change',
               'rows swap places on the leaderboard'),
    related=('sorted-bar-reorder', 'bar-chart-race', 'reorder-list-shuffle', 'axis-rescale',
             'layout-animation-flip', 'grid-reflow-shuffle'),
    api=('videobuilder.capabilities.broadcast.leaderboard_row_swap.row_slots',
         'videobuilder.capabilities.broadcast.leaderboard_row_swap.draw_order'),
    demo=lambda: demo.film(draw),
)
