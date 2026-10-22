"""Headline rotator: one fixed headline slot on a banner steps through a list
of headlines, the current one sliding out of the slot as the next slides in."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

DIRECTIONS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}


def rotation(t, count, hold=1.6, swap=0.4):
    """Where a rotator of `count` headlines is at `t` seconds: `(current,
    following, p)`. Each headline holds for `hold` seconds, then the swap to
    the next runs over `swap` seconds with `p` going 0 -> 1 (eased); outside a
    swap `p` is 0. The list loops."""
    cycle = hold + swap
    k, into = divmod(max(t, 0.0), cycle)
    k = int(k)
    p = vb.ease_in_out_quart(vb.clamp01((into - hold) / swap)) if into > hold else 0.0
    return k % count, (k + 1) % count, p


def draw_headline_rotator(cv, headlines, font, x, y, w, h, t, color=demo.INK, hold=1.6, swap=0.4,
                          direction='up', fade=True):
    """Draw the slot (x, y, w, h) of a headline rotator at `t` seconds:
    `headlines` cycle in turn, each left-aligned and vertically centred in the
    slot, the outgoing one pushed out towards `direction` ('up', 'down',
    'left', 'right') as the incoming one follows it in from the other side.
    Drawing is clipped to the slot. Returns the index showing (the incoming
    one once the swap is past half way)."""
    cur, nxt, p = rotation(t, len(headlines), hold, swap)
    dx, dy = DIRECTIONS[direction]
    span_x, span_y = w * dx, h * dy

    def line(text, offset, alpha):
        tw, th = vb.text.block_size([text], font)
        vb.text.draw(cv, [text], font, x + offset * span_x, y + (h - th) / 2 + offset * span_y, color,
                     alpha=alpha)

    with cv.clip(x, y, w, h):
        line(headlines[cur], p, 1 - p if fade else 1.0)
        if p > 0:
            line(headlines[nxt], p - 1, p if fade else 1.0)
    return nxt if p >= 0.5 else cur


HEADLINES = ('MARKETS OPEN HIGHER', 'STORM FRONT MOVES EAST', 'CITY VOTES ON NEW PARK')
HOLD, SWAP = 0.75, 0.4


def draw(n, cv):
    t = n / demo.FPS
    bx, by, bw, bh = 150, 200, 660, 140
    cv.shadow(bx, by, bw, bh, radius=10, dy=8, blur=24, color=(0, 0, 0, 0.45))
    cv.rect(bx, by, bw, bh, '#1d1f26', radius=10)
    cv.rect(bx, by, 8, bh, demo.ACCENT, radius=3)
    vb.text.draw(cv, ['LATEST'], demo.font(20, 800), bx + 40, by + 24, demo.TEAL)
    slot = (bx + 40, by + 52, bw - 80, 58)
    showing = draw_headline_rotator(cv, HEADLINES, demo.font(40, 800), *slot, t, hold=HOLD, swap=SWAP)
    cv.mark('slot', *slot)
    for i in range(len(HEADLINES)):  # which headline of the set is up
        cv.rect(bx + 40 + i * 34, by + bh - 22, 26, 4, demo.ACCENT if i == showing else demo.LINE, radius=2)


TECHNIQUE = Technique(
    id='headline-rotator',
    name='Headline rotator',
    family='broadcast',
    group='Tickers & banners',
    aliases=('chyron rotation', 'headline cycle', 'rotating headlines'),
    definition='A banner keeps one headline slot and swaps its text in turn, each headline sliding '
               'out of the slot while the next slides in behind it.',
    phrasings=('a news banner that flips between a few headlines',
               'cycle the top stories through one lower-third line',
               'make the breaking news bar rotate through several headlines'),
    related=('word-carousel-rotate', 'typed-word-rotator', 'turntable-rotation', 'character-rotate-in',
             'word-flip-in', 'spin'),
    api=('videobuilder.techniques.broadcast.headline_rotator.draw_headline_rotator',
         'videobuilder.techniques.broadcast.headline_rotator.rotation'),
    demo=lambda: demo.film(draw),
)
