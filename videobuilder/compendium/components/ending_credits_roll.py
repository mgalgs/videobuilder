"""Ending: credits roll. Roles and names scroll up over a tinted background
-- a wash of colour and a halftone screen that fade down the frame -- fading
in at the foot of the frame and out at the head, then ease to a stop with
the closing line resting in the middle. Two columns either side of a gutter
in 16:9; stacked role-over-name where the frame is narrow.

Built from `examples/capabilities/comic-halftone.py` (the dot screen) and
`eased-entrances.py` (the roll's ease to rest).
"""
import cairo

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot
from . import _ending_util as u

MAX_CREDITS = 10
ROLL = 0.66  # share of the shot the roll takes; the closing line holds for the rest
EASE = vb.bezier(0.12, 0.0, 0.35, 1.0)

LAYOUT = {
    '16x9': dict(cols=True, role=18, name=(34, 30, 26), row=26, title=20, close=(68, 60, 52, 44), fade=70),
    '9x16': dict(cols=False, role=19, name=(40, 36, 32, 28), row=44, title=22, close=(80, 72, 64, 56), fade=120),
    '1x1': dict(cols=False, role=15, name=(30, 27, 24, 22), row=22, title=16, close=(52, 46, 40, 34), fade=70),
}


def parse(credits):
    """'Role: Name' lines -> (role, name) pairs; a line with no colon is a name alone."""
    out = []
    for line in credits.replace(';', '\n').split('\n'):
        line = line.strip()
        if not line:
            continue
        role, sep, name = line.partition(':')
        out.append((role.strip(), name.strip()) if sep else ('', role.strip()))
    return out[:MAX_CREDITS]


def _background(cv, tint):
    W, H = cv.width, cv.height
    ctx = cv.ctx
    grad = cairo.LinearGradient(0, 0, 0, H)
    for stop, amt in ((0, 0.62), (0.55, 0.88), (1, 1.0)):
        r, g, b = kit.mix(tint, kit.BG, amt)
        grad.add_color_stop_rgb(stop, r / 255, g / 255, b / 255)
    ctx.set_source(grad)
    ctx.paint()
    fade = cairo.LinearGradient(0, 0, 0, H * 0.7)
    fade.add_color_stop_rgba(0, 0, 0, 0, 0.5)
    fade.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(vb.halftone_pattern(9, 2.3, angle=0.35, color=tint))
    ctx.mask(fade)


def _rows(items, L, width, gutter):
    """Each credit laid out at y=0: (height, [(kind, lines, font, x, dy, w)])."""
    role_f = kit.mono(L['role'], 600, tracking=0.14)
    out = []
    for role, name in items:
        role = role.upper()
        if L['cols']:
            name_w = width / 2 - gutter
            name_f, lines, nw, nh = u.fit(name, L['name'], 650, name_w, 1)
            rh = text.line_height(role_f)
            parts = []
            if role:
                rl = text.wrap(role, role_f, width / 2 - gutter)
                rw, rh = text.block_size(rl, role_f)
                parts.append(('role', rl, role_f, -gutter - rw, (text.line_height(name_f) - text.line_height(role_f)) / 2, rw))
            parts.append(('name', lines, name_f, gutter, 0, nw))
            out.append((max(nh, rh), parts))
        else:
            name_f, lines, nw, nh = u.fit(name, L['name'], 650, width, 2)
            parts, y = [], 0
            if role:
                rl = text.wrap(role, role_f, width)
                rw, rh = text.block_size(rl, role_f)
                parts.append(('role', rl, role_f, -rw / 2, 0, rw))
                y = rh + 4
            parts.append(('name', lines, name_f, -nw / 2, y, nw))
            out.append((y + nh, parts))
    return out


def draw(cv, shot):
    data, f, n = shot.data, shot.f, shot.length
    name = cv.format.name if cv.format is not None and cv.format.name in LAYOUT else '16x9'
    L = LAYOUT[name]
    tint = data['tint']
    W, H = cv.width, cv.height
    s = vb.Box.of(cv).pad(48)
    _background(cv, tint)
    cx = s.cx
    gutter = 16

    rows = _rows(parse(data['credits']), L, s.w, gutter)
    title = data['title'].upper()
    title_f = kit.mono(L['title'], 700, tracking=0.2)
    close_f, close_lines, cw, ch = u.fit(data['closing'], L['close'], 800, s.w, 3, tracking=-0.02)

    # The column, top to bottom, at y=0.
    items = []  # (name, y, h, draw)
    y = 0.0
    if title:
        th = text.line_height(title_f)
        items.append(('title', y, th, ('title',)))
        y += th + L['row'] * 2.2
    for i, (h, parts) in enumerate(rows):
        items.append((f'credit-{i + 1}', y, h, ('row', parts)))
        y += h + L['row']
    y += max(L['row'] * 3, H / 2 - ch / 2 + 4)  # the last credit is just off the top when the closing rests
    close_y = y
    items.append(('closing', y, ch, ('closing',)))

    # Roll from "everything below the frame" to "closing line centred".
    start = s.bottom + 8
    end = H / 2 - ch / 2 - close_y
    p = EASE(vb.clamp01(f / max(1, n * ROLL)))
    off = start + (end - start) * p

    # Draw the column into a group, then fade its head and foot with a mask.
    ctx = cv.ctx
    ctx.push_group()
    for mark, iy, ih, what in items:
        top = off + iy
        if top > H or top + ih < 0:
            continue
        if what[0] == 'title':
            tw = text.measure(title, title_f)
            text.draw(cv, [title], title_f, cx - tw / 2, top, tint)
            box = (cx - tw / 2, top, tw, ih)
        elif what[0] == 'row':
            x0, x1 = W, 0
            for kind, lines, fnt, dx, dy, w in what[1]:
                color = kit.mix(kit.MUTED, tint, 0.35) if kind == 'role' else kit.INK
                text.draw(cv, lines, fnt, cx + dx, top + dy, color, align='right' if kind == 'role' else
                          ('left' if L['cols'] else 'center'), width=w)
                x0, x1 = min(x0, cx + dx), max(x1, cx + dx + w)
            box = (x0, top, x1 - x0, ih)
        else:
            text.draw(cv, close_lines, close_f, cx - cw / 2, top, kit.INK, align='center', width=cw)
            box = (cx - cw / 2, top, cw, ih)
        # Marked only once wholly inside the frame's clear band.
        if s.y <= box[1] and box[1] + box[3] <= s.bottom:
            cv.mark(mark, *box)
    ctx.pop_group_to_source()
    fd = L['fade']
    mask = cairo.LinearGradient(0, 0, 0, H)
    mask.add_color_stop_rgba(0, 0, 0, 0, 0)
    mask.add_color_stop_rgba(fd / H, 0, 0, 0, 1)
    mask.add_color_stop_rgba(1 - fd / H, 0, 0, 0, 1)
    mask.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.mask(mask)

    # Once the roll rests, a tinted rule grows under the closing line.
    if f > n * ROLL * 0.9:
        g = u.smoother((f - n * ROLL * 0.9) / 18)
        ry = H / 2 + ch / 2 + 22
        cv.line(cx - 40 * g, ry, cx + 40 * g, ry, tint, width=4)


COMPONENT = Component(
    id='credits-roll',
    kind='ending',
    description=('A credits roll: roles and names scroll up over a tinted, halftone-screened background, fading at '
                 'the top and bottom of the frame, and ease to rest on a closing line in the middle.'),
    tags=('ending', 'credits', 'roll', 'names', 'thanks', 'outro', 'halftone'),
    formats=('16x9', '9x16', '1x1'),
    beats=(10, 24),
    slots=(
        Slot('credits', 'text', True, f'One credit per line, written "Role: Name" (a line without a colon is a name '
             f'alone); up to {MAX_CREDITS} lines, each name under 28 characters.',
             max_length=320),
        Slot('closing', 'text', True, 'The line the roll stops on, e.g. "Thanks for watching".', max_length=36),
        Slot('title', 'text', False, 'A small heading at the top of the roll, shown in capitals, e.g. "Made by".',
             max_length=24),
        Slot('tint', 'color', False, 'Colour of the background wash, the dot screen, the heading and the rule.'),
    ),
    sample={'credits': ('Director: Ada Fennimore\nWriter: Joss Okafor\nMotion: Priya Lindqvist\n'
                        'Music: The Low Tide Trio\nColour: Mateo Arkwright\nProducer: Wren Halloway'),
           'closing': 'Thanks for watching', 'title': 'Made by', 'tint': kit.TEAL},
    draw=draw,
)
