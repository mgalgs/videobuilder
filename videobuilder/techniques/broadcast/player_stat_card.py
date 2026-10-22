"""Player stat card: a sports-broadcast card with the player's number, name
and role in a header, then a column of statistics that drop in one row at a
time, each figure counting up as its row lands."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ..typography.number_count_up import count_up

HEADER = '#2b3350'
BODY = '#1d2029'
ROW = '#252935'
GOLD = '#f2b632'
KIT = '#7f8cff'


def card_timing(p, rows, header=0.3, stagger=0.55):
    """Split card progress `p` (0 -> 1) into the header's progress and each
    of `rows` rows' progress. The header takes the first `header` of the run;
    each row runs for its own slot, and consecutive rows overlap by
    `stagger` of a slot (0: strictly one after another)."""
    p = vb.clamp01(p)
    head = vb.clamp01(p / header) if header > 0 else 1.0
    if not rows:
        return head, []
    span = 1 - header
    slot = span / (rows - (rows - 1) * stagger) if rows > 1 else span
    out = []
    for i in range(rows):
        t0 = header + i * slot * (1 - stagger)
        out.append(vb.clamp01((p - t0) / slot))
    return head, out


def _avatar(cv, x, y, w, h, number, alpha):
    """A plain silhouette in a jersey with `number`, standing on the header's
    bottom edge, inside the box (x, y, w, h)."""
    cx = x + w / 2
    r = w * 0.17
    demo.dot(cv, cx, y + h * 0.3, r=r, color='#8b94d9', alpha=alpha)
    bw, bh = w * 0.82, h * 0.42
    cv.rect(cx - bw / 2, y + h - bh, bw, bh + 20, KIT, radius=bw * 0.32, alpha=alpha)
    f = demo.font(round(h * 0.2), 800)
    tw, th = vb.text.block_size([number], f)
    vb.text.draw(cv, [number], f, cx - tw / 2, y + h - bh * 0.55 - th / 2, BODY, alpha=alpha)


def draw_player_card(cv, x, y, w, name, number, role, stats, p, row_h=46, header_h=128,
                     accent=GOLD, header=0.3, stagger=0.55):
    """Draw a player stat card with its top-left at (x, y), `w` wide, at
    progress `p` (0 -> 1). The header (`number`, `name`, `role` and a jersey
    silhouette) slides up into place first; then each `(label, value)` in
    `stats` drops in as its own row, sliding from the left while its value
    counts up from zero (`count_up`; a value may be a number or a
    `(number, suffix)` pair). See `card_timing` for `header` and `stagger`.
    Returns the card's Box."""
    head, rows = card_timing(p, len(stats), header, stagger)
    h = header_h + 20 + len(stats) * (row_h + 10) + 10
    e = vb.ease_out_expo(head)
    cy = y + 40 * (1 - e)
    with cv.layer(opacity=e):
        cv.shadow(x, cy, w, h, radius=16, dy=12, blur=30, color=(0, 0, 0, 0.5))
        cv.rect(x, cy, w, h, BODY, radius=16)
        with cv.clip(x, cy, w, h, radius=16):
            cv.rect(x, cy, w, header_h, HEADER)
            with cv.clip(x, cy, w, header_h - 3):
                _avatar(cv, x + w - 170, cy + 14, 140, header_h - 17, number, 1.0)
            cv.rect(x, cy + header_h - 3, w, 3, accent)
        tx = x + 28
        slide = 30 * (1 - vb.ease_out_expo(vb.clamp01(head * 1.4 - 0.2)))
        vb.text.draw(cv, [number], demo.font(24, 800), tx + slide, cy + 18, accent)
        vb.text.draw(cv, [name], demo.font(42, 800), tx + slide, cy + 44, demo.INK)
        vb.text.draw(cv, [role.upper()], demo.font(14, 600), tx + slide, cy + 96, demo.MUTED)
    ry = cy + header_h + 20
    f_label, f_value = demo.font(16, 700), demo.font(28, 800)
    for (label, value), rp in zip(stats, rows):
        if rp > 0:
            num, suffix = value if isinstance(value, tuple) else (value, '')
            re_ = vb.ease_out_expo(rp)
            rx, rw = x + 18 - 60 * (1 - re_), w - 36
            with cv.layer(opacity=vb.clamp01(rp * 3)):
                cv.rect(rx, ry, rw, row_h, ROW, radius=6)
                cv.rect(rx, ry, 4, row_h, accent, radius=2)
                _, lh = vb.text.block_size([label.upper()], f_label)
                vb.text.draw(cv, [label.upper()], f_label, rx + 20, ry + (row_h - lh) / 2, demo.MUTED)
                text = count_up(num, vb.clamp01(rp * 1.3), suffix=suffix)
                vw, vh = vb.text.block_size([text], f_value)
                vb.text.draw(cv, [text], f_value, rx + rw - 20 - vw, ry + (row_h - vh) / 2, demo.INK)
            cv.mark(f'row-{label}', rx, ry, rw, row_h)
        ry += row_h + 10
    cv.mark('card', x, cy, w, h)
    return vb.Box(x, cy, w, h)


STATS = (('Points', 28.4), ('Rebounds', 9.1), ('Assists', 6.7), ('FG', (51.3, '%')))


def draw(n, cv):
    w = 520
    h = 128 + 20 + len(STATS) * 56 + 10
    draw_player_card(cv, (demo.W - w) / 2, (demo.H - h) / 2, w, 'R. OKAFOR', '23', 'Forward  /  Season averages',
                     STATS, demo.phase(n, 0.1, 2.6))


TECHNIQUE = Technique(
    id='player-stat-card',
    name='Player stat card',
    family='broadcast',
    group='Sports graphics',
    aliases=('player card', 'athlete profile card', 'stat card', 'player lower-third stats'),
    definition="A card with a player's name and shirt number builds on screen, then their key numbers "
               'drop in underneath one row at a time, each figure ticking up as it arrives.',
    phrasings=('show the striker with their season stats coming in line by line',
               'a sports-TV style player card with points, rebounds and assists',
               'pop up a profile card for the athlete and reveal their numbers one after another'),
    related=('odometer-roll', 'versus-card', 'number-count-up', 'end-card-with-subscribe-slot',
             'sticky-card-stack-on-scroll', 'broadcast-title-card-stinger'),
    api=('videobuilder.techniques.broadcast.player_stat_card.draw_player_card',
         'videobuilder.techniques.broadcast.player_stat_card.card_timing',
         'videobuilder.techniques.typography.number_count_up.count_up'),
    demo=lambda: demo.film(draw),
)
