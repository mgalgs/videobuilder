"""Podium rise: ranked blocks grow up out of a baseline one at a time, lowest
rank first, so the winner's tallest block is the last to arrive."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

GOLD, SILVER, BRONZE = '#f2b632', '#8e9bff', '#5a6299'


def podium_order(count):
    """Left-to-right slot of each rank (0 = first place): the winner in the
    middle, then alternating outwards -- 2nd left, 3rd right, 4th further left..."""
    mid = (count - 1) // 2
    slots = [0] * count
    for rank in range(count):
        step = (rank + 1) // 2
        slots[rank] = mid - step if rank % 2 else mid + step
    return slots


def podium_rise(cv, names, p, x, baseline, width, height, colors=(GOLD, SILVER, BRONZE),
                gap=28, overlap=0.35, ease=vb.ease_out_back):
    """Draw a podium of `names` (in rank order, winner first) at progress `p`
    (0 -> 1). Blocks stand on `baseline` across `width` from `x`; the
    winner's block is `height` tall and each lower rank shorter. They rise in
    reverse rank order, each overlapping the previous by `overlap` of its own
    time, and each block's name fades in above it once it is up.

    In a film, call it with `p` from the shot's own clock, e.g. `podium_rise(cv,
    ['Ana', 'Ben', 'Cy'], shot.f / (2 * fps), 200, 450, 560, 280)`."""
    count = len(names)
    slots = podium_order(count)
    col = (width - gap * (count - 1)) / count
    span = 1 + (count - 1) * (1 - overlap)  # total time in block-durations
    num_f, name_f = demo.font(col * 0.32, 800), demo.font(max(14, col * 0.12), 700)
    with cv.clip(x - gap, 0, width + 2 * gap, baseline):  # blocks come up out of the floor
        for order, rank in enumerate(reversed(range(count))):
            t0 = order * (1 - overlap) / span
            q = vb.clamp01((p - t0) * span)
            if q <= 0:
                continue
            h = height * (1 - 0.22 * rank) * max(0.0, ease(q))
            bx = x + slots[rank] * (col + gap)
            top = baseline - h
            color = colors[rank] if rank < len(colors) else colors[-1]
            cv.rect(bx, top, col, h + 12, color, radius=10)
            ink = demo.BG if rank == 0 else demo.INK
            demo.word(cv, str(rank + 1), bx + col / 2, top + col * 0.32, font=num_f, color=ink)
            cv.mark(f'block-{rank + 1}', bx, top, col, h)
    for rank in range(count):
        order = count - 1 - rank
        t_up = (order * (1 - overlap) + 0.7) / span
        a = vb.clamp01((p - t_up) * span / 0.3)
        if a > 0:
            h = height * (1 - 0.22 * rank)
            bx = x + slots[rank] * (col + gap)
            demo.word(cv, names[rank], bx + col / 2, baseline - h - name_f.size * 1.1 - 10 * (1 - a),
                      font=name_f, color=demo.INK, alpha=a)
    cv.line(x - gap, baseline, x + width + gap, baseline, demo.MUTED, width=3)


def draw(n, cv):
    width = 600
    podium_rise(cv, ['Ada', 'Ben', 'Cleo'], demo.phase(n, 0.2, 1.8),
                (demo.W - width) / 2, demo.H - 90, width, 300, gap=20)


CAPABILITY = Capability(
    id='podium-rise',
    name='Podium rise',
    family='broadcast',
    group='Stats',
    aliases=('ranking podium reveal', 'winners podium'),
    definition='Ranked blocks grow up from a shared floor one after another, starting with the lowest place, '
               'so the tallest first-place block lands last.',
    phrasings=('reveal the top three on a podium, winner last',
               'show the rankings as podium steps rising up one by one',
               'build up a medal stand from third place to first'),
    related=('leaderboard-row-swap', 'character-rise', 'bar-chart-race', 'title-card-reveal', 'pedestal',
             'staggered-cascade-reveal'),
    api=('videobuilder.capabilities.broadcast.podium_rise.podium_rise',
         'videobuilder.capabilities.broadcast.podium_rise.podium_order'),
    demo=lambda: demo.film(draw),
)
