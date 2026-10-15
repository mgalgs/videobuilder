"""Transition: block wipe. Staggered bands of solid colour sweep across on
the beat -- the first covers the outgoing card, the last uncovers the
incoming one -- with the bands' edges cut on a slant. The sweep follows the
frame: left to right on 16:9, bottom to top up the tall 9:16, corner to
corner on 1:1. Each card is an editorial type layout: a mono kicker up top,
a heavy title anchored low, its lines rising out of a mask as it lands.

Built on the timeline's own `Segment(overlap=...)`, like `overlap_slide`.
"""
import math

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot
from . import _transition_util as u

MOVE = 1.0            # beats the sweep takes
STAGGER = 0.1         # of the move, between one band edge and the next (less for many bands)
LINE_STAGGER = 3      # frames between title lines rising
RISE = 12             # frames a title line takes to rise

EASE = vb.bezier(0.75, 0.0, 0.2, 1.0)


def _layout(cv):
    """Per format: the safe box, the title's width, sizes and line limit, the
    numeral's size and where it sits ('right' of the title, or 'top'), and
    the sweep's direction and slant."""
    s = kit.safe(cv, 56)
    name = cv.format.name if cv.format else '16x9'
    if name == '9x16':
        return dict(s=s, title_w=s.w, sizes=(112, 100, 88, 76, 64, 56, 48, 40), lines=4, num=400, num_at='top',
                    dir=(0.0, -1.0), tilt=0.2)
    if name == '1x1':
        return dict(s=s, title_w=s.w, sizes=(84, 76, 68, 60, 52, 46, 40), lines=2, num=190, num_at='right',
                    dir=(1 / math.sqrt(2), 1 / math.sqrt(2)), tilt=0.0)
    return dict(s=s, title_w=s.w * 0.58, sizes=(96, 88, 80, 72, 64, 56, 50, 42), lines=2, num=290, num_at='right',
                dir=(1.0, 0.0), tilt=0.22)


def _rise(enter_f, delay):
    return vb.ease_out_quint(vb.clamp01((enter_f - delay) / RISE))


def _card(cv, d, side, page, accent, enter_f, shift=(0.0, 0.0)):
    """One full-frame card: `page` behind, the kicker top left, a big outline
    numeral, the title anchored bottom left. `enter_f`: frames since the
    card's parts started rising (large = at rest)."""
    L = _layout(cv)
    s = L['s']
    kicker, title, number = d[f'{side}_kicker'], d[f'{side}_title'], d[f'{side}_number']
    ink = u.ink_on(page)
    cv.fill(page)
    dx, dy = shift
    title_f, lines = u.fit(title, L['title_w'], L['sizes'], weight=800, max_lines=L['lines'],
                           tracking=-0.035, line_height=0.98)
    lh = text.line_height(title_f)
    with cv.layer(dx=dx, dy=dy):
        if kicker:
            kf = kit.mono(20, 600, tracking=0.14)
            a = _rise(enter_f, 0)
            cv.rect(s.x, s.y + 11, 28 * a, 4, accent)
            kb = text.draw(cv, [kicker.upper()], kf, s.x + 42, s.y, ink, alpha=a)
            cv.mark(f'kicker-{side}', *kb)
        if number is not None:
            p = _rise(enter_f, 1)
            nf = kit.font(L['num'], 800, tracking=-0.04)
            label = f'{abs(round(number)):02d}'
            line_c = kit.mix(page, ink, 0.4)
            if L['num_at'] == 'top':
                nb = u.outline_text(cv, label, nf, s.x - 4, s.y + 72 + (1 - p) * 60, line_c,
                                    width=3, alpha=p)
            else:
                nb = u.outline_text(cv, label, nf, s.right + (1 - p) * 60, s.y + 44, line_c, width=3,
                                    alpha=p, align='right')
            cv.mark(f'number-{side}', *nb)
        top = s.bottom - lh * len(lines)
        for i, line in enumerate(lines):
            p = _rise(enter_f, (i + 1) * LINE_STAGGER)
            if p <= 0:
                continue
            y = top + i * lh
            w = text.measure(line, title_f)
            with cv.clip(s.x - 8, y - lh * 0.2, w + 24, lh * 1.45):
                box = text.draw(cv, [line], title_f, s.x, y + (1 - p) * lh * 1.25, ink)
            if p >= 1:
                cv.mark(f'title-{side}-{i}', *box)
        # A short rule in the accent, opening the title.
        cv.rect(s.x, top - 22, 64 * _rise(enter_f, 2), 6, accent)


def _band(ctx, n, t, s0, s1, reach):
    """The strip between s0 <= n.p <= s1, as a quad well past the frame."""
    tx, ty = t
    nx, ny = n
    pts = [(nx * s0 + tx * reach, ny * s0 + ty * reach), (nx * s1 + tx * reach, ny * s1 + ty * reach),
           (nx * s1 - tx * reach, ny * s1 - ty * reach), (nx * s0 - tx * reach, ny * s0 - ty * reach)]
    u.poly(ctx, pts)


def draw(cv, shots):
    data = shots[-1].data
    bands = tuple(data['bands']) or (kit.ACCENT, kit.TEAL)
    page = data['page']
    L = _layout(cv)
    (dx, dy), tilt = L['dir'], L['tilt']
    on, p, after, fpb = u.phase(shots, MOVE)
    if not on:
        _card(cv, data, 'from', kit.BG, bands[0], u.hold_f(shots))
        return

    # The sweep's direction, and the edges' normal: the direction turned a little, for the slant.
    nx, ny = dx * math.cos(tilt) - dy * math.sin(tilt), dx * math.sin(tilt) + dy * math.cos(tilt)
    tx, ty = -ny, nx
    corners = [(0, 0), (cv.width, 0), (0, cv.height), (cv.width, cv.height)]
    proj = [nx * x + ny * y for x, y in corners]
    lo, hi = min(proj) - 2, max(proj) + 2
    reach = cv.width + cv.height
    k = len(bands)
    stagger = min(STAGGER, 0.5 / k)
    span = 1 - stagger * k
    edges = [lo + (hi - lo) * EASE(vb.clamp01((p - i * stagger) / span)) for i in range(k + 1)]

    ctx = cv.ctx
    lead = edges[0]
    push = (lead - lo) / (hi - lo)
    if push < 0.999:   # some of the outgoing card is still uncovered
        ctx.save()
        _band(ctx, (nx, ny), (tx, ty), lead, hi + reach, reach)
        ctx.clip()
        _card(cv, data, 'from', kit.BG, bands[0], 10_000,
              shift=(dx * 40 * push, dy * 40 * push))
        ctx.restore()
    for i, color in enumerate(bands):
        if edges[i] - edges[i + 1] > 0.3:
            _band(ctx, (nx, ny), (tx, ty), edges[i + 1], edges[i], reach)
            ctx.set_source_rgba(*vb.rgba(color))
            ctx.fill()
    trail = edges[-1]
    rest = 1 - (trail - lo) / (hi - lo)
    if rest < 0.999:
        enter = after + round(0.5 * fpb)   # its parts start rising as the last band clears
        ctx.save()
        _band(ctx, (nx, ny), (tx, ty), lo - reach, trail, reach)
        ctx.clip()
        _card(cv, data, 'to', page, bands[-1], enter,
              shift=(-dx * 60 * rest, -dy * 60 * rest))
        ctx.restore()


COMPONENT = Component(
    id='block-wipe',
    kind='transition',
    description='Staggered slanted bands of solid colour sweep across on the beat, covering a dark title card '
                'and uncovering a light one whose title lines rise into place. Follows the frame: across 16:9, '
                'up 9:16, corner to corner on 1:1.',
    tags=('transition', 'wipe', 'colour', 'bands', 'editorial', 'type'),
    formats=('16x9', '9x16', '1x1'),
    beats=(2, 4),
    slots=(
        Slot('from_title', 'text', True, 'Title on the outgoing (dark) card, a few words.', max_length=28),
        Slot('to_title', 'text', True, 'Title on the incoming (light) card, a few words.', max_length=28),
        Slot('from_kicker', 'text', False, 'Tiny label above the outgoing title, e.g. a section name.',
             max_length=20),
        Slot('to_kicker', 'text', False, 'Tiny label above the incoming title, e.g. the next section name.',
             max_length=20),
        Slot('from_number', 'number', False, 'Chapter number shown huge in outline on the outgoing card, e.g. 1.'),
        Slot('to_number', 'number', False, 'Chapter number shown huge in outline on the incoming card, e.g. 2.'),
        Slot('bands', 'palette', False, 'Two to four colours for the bands, first to last across the frame.'),
        Slot('page', 'color', False, 'Background of the incoming card; light or dark both work.'),
    ),
    sample={
        'from_title': 'Where we started',
        'to_title': 'Where it goes next',
        'from_kicker': 'Part one',
        'to_kicker': 'Part two',
        'from_number': 1,
        'to_number': 2,
        'bands': (kit.ACCENT, '#f2b84b', kit.TEAL),
        'page': kit.INK,
    },
    draw=draw,
)
