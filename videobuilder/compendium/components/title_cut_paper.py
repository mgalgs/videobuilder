"""Title: cut paper. A ransom-note headline assembled on a paper wall: each
word printed on its own torn scrap (cream, ink-black or the accent), mixed
type, slapped down one per half beat in stop-motion -- held on twos, a
seeded jitter while it moves, its lift shadow shrinking as it lands -- then
a red-pencil scribble underlines the last row and an optional subtitle
lands on a strip of masking tape.

The scraps are packed into rows fitted per format, so a tall frame stacks
more, bigger rows instead of shrinking one wide line into the middle.
After `examples/capabilities/paper-collage.py`'s paper, grain and shadows.
"""
import math
import random
from functools import lru_cache

import cairo

import videobuilder as vb
from videobuilder import paths, text

from .. import kit
from ..schema import Component, Slot
from ._title_util import frames_per_beat, grain

WALL = '#c9bdac'
SCRAP = '#f1ece2'
PRINT = '#1b1916'
TAPE = '#e6dcc3'
PAD = 44
SUB_F = kit.font(24, 700)


def step(n):
    """Stop-motion: paper only moves on even frames."""
    return n - n % 2


def boil(key, n, amount):
    r = random.Random(f'{key}:{step(n)}')
    return r.uniform(-1, 1) * amount, r.uniform(-1, 1) * amount, math.radians(r.uniform(-0.6, 0.6) * amount)


def _word_font(i, size):
    """Mixed type, ransom-note style, but one family's worth of it."""
    if i % 3 == 1:
        return kit.mono(round(size * 0.9), 700, tracking=-0.02)
    return kit.font(size, 900 if i % 2 == 0 else 800, tracking=-0.03)


def _look(i, accent):
    """(paper, ink) for word i: cream, the accent, cream, black, repeating."""
    return ((SCRAP, PRINT), (accent, SCRAP), (SCRAP, PRINT), (PRINT, SCRAP))[i % 4]


def _rect_pts(w, h):
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


@lru_cache(maxsize=256)
def _torn(w, h, seed, amount):
    return tuple(paths.torn(_rect_pts(w, h), seed=seed, amount=amount))


def _layout(cv, title, has_sub):
    """Words packed into rows: [(word, font, scrap w, scrap h, cx, cy, tilt)], size, bottom y."""
    s = vb.Box.of(cv).pad(PAD)
    words = title.upper().split()
    tall = cv.height > cv.width * 1.2
    budget = s.h * (0.88 if tall else 0.84) - (text.line_height(SUB_F) + 60 if has_sub else 0)
    rnd = random.Random(title)
    tilts = [rnd.uniform(1.2, 3.6) * (1 if i % 2 else -1) for i in range(len(words))]
    nudges = [rnd.uniform(-1, 1) for _ in range(len(words))]
    for size in range(150, 25, -4):
        padx, pady = size * 0.24, size * 0.12
        fonts = [_word_font(i, size) for i in range(len(words))]
        dims = [(text.measure(w, f) + 2 * padx, text.line_height(f) * 0.92 + 2 * pady) for w, f in zip(words, fonts)]
        hgap, vgap = size * 0.16, size * 0.2
        rows, cur, cur_w = [], [], 0
        for i, (w, h) in enumerate(dims):
            if cur and cur_w + hgap + w > s.w * 0.94:
                rows.append(cur)
                cur, cur_w = [], 0
            cur_w += (hgap if cur else 0) + w
            cur.append(i)
        rows.append(cur)
        row_h = size * 0.92 + 2 * pady + size * 0.2
        under = size * 0.3
        total = len(rows) * row_h + (len(rows) - 1) * vgap + under
        if all(w <= s.w * 0.94 for w, _ in dims) and total <= budget:
            break
    block_top = s.cy - (total + (text.line_height(SUB_F) + 60 if has_sub else 0)) / 2
    placed = []
    for r, row in enumerate(rows):
        row_w = sum(dims[i][0] for i in row) + hgap * (len(row) - 1)
        slack = (s.w - row_w) / 2
        x = s.x + slack + nudges[row[0]] * slack * 0.5
        cy = block_top + r * (row_h + vgap) + row_h / 2
        for i in row:
            w, h = dims[i]
            placed.append((words[i], fonts[i], w, h, x + w / 2, cy + nudges[i] * size * 0.05, tilts[i]))
            x += w + hgap
    bottom = block_top + total
    return s, placed, size, rows, bottom


def _paper(cv, pts, color, seed):
    ctx = cv.ctx
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgba(*vb.rgba(color))
    ctx.fill_preserve()
    ctx.save()
    ctx.clip_preserve()
    ctx.set_source_rgba(*vb.rgba('#fbf8f2', 0.55))
    ctx.set_line_width(2.4)
    ctx.stroke_preserve()
    grain(cv, 0.55, seed=seed)
    ctx.restore()
    ctx.new_path()


def _wall(cv):
    cv.fill(WALL)
    grain(cv, 0.5, seed=3)
    w, h = cv.width, cv.height
    sheets = (([(-30, h * 0.78), (w * 0.34, h + 30), (-30, h + 30)], '#d5cbbd', 11),
              ([(w * 0.62, -30), (w + 30, -30), (w + 30, h * 0.2)], '#bcb09f', 12))
    for pts, color, seed in sheets:
        torn = paths.torn(pts, seed=seed, amount=7)
        cv.shape_shadow(torn, dx=2, dy=3, blur=9, color=(40, 30, 20, 0.3))
        _paper(cv, torn, color, seed)
    # Soft window light: a broad diagonal falloff.
    g = cairo.LinearGradient(0, 0, w, h)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.10)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.14)
    cv.ctx.set_source(g)
    cv.ctx.paint()


def draw(cv, shot):
    data = shot.data
    accent = data['accent']
    fpb = frames_per_beat(shot)
    n = shot.f
    _wall(cv)
    s, placed, size, rows, bottom = _layout(cv, data['title'], bool(data['subtitle']))
    ctx = cv.ctx

    land = 6  # frames from the top of the slap to flat on the wall
    t_first = fpb * 0.25 - land
    for i, (word, f, w, h, cx, cy, tilt) in enumerate(placed):
        a = t_first + i * fpb * 0.5
        if step(n) < a:
            continue
        t = vb.ease_out_back(vb.clamp01((step(n) - a) / land))
        moving = step(n) < a + land + 2
        jx, jy, jr = boil(f'w{i}', n, 1.4) if moving else (0, 0, 0)
        lift = 4 + (1 - t) * 20
        paper, ink = _look(i, accent)
        pts = _torn(round(w), round(h), 20 + i, round(size * 0.05, 1))
        ctx.save()
        ctx.translate(cx + jx - (1 - t) * 30, cy + jy - (1 - t) * 24)
        ctx.rotate(math.radians(tilt) + jr + (1 - t) * math.radians(8 if i % 2 else -8))
        sc = 1 + (1 - t) * 0.28
        ctx.scale(sc, sc)
        cv.shape_shadow(pts, dx=lift * 0.5, dy=lift, blur=round(8 + lift), color=(35, 25, 15, 0.42))
        _paper(cv, pts, paper, 30 + i)
        tw = text.measure(word, f)
        th = text.line_height(f)
        box = text.draw(cv, [word], f, -tw / 2, -th / 2 + size * 0.02, ink)
        cv.mark(f'word-{i}', box.x, box.y + th * 0.12, box.w, box.h * 0.76)
        ctx.restore()
        # A strip of tape on the first and last scrap, once they're down.
        if i in (0, len(placed) - 1) and t >= 1 and step(n) >= a + land + 4:
            corner = (-w / 2 + 6, -h / 2 + 4) if i == 0 else (w / 2 - 6, h / 2 - 4)
            ca, sa = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
            tx, ty = cx + corner[0] * ca - corner[1] * sa, cy + corner[0] * sa + corner[1] * ca
            tape = _torn(round(size * 0.7), round(size * 0.22), 90 + i, 1.5)
            ctx.save()
            ctx.translate(tx, ty)
            ctx.rotate(math.radians(-40 if i == 0 else -35))
            cv.shape_shadow(tape, dx=1, dy=2, blur=4, color=(40, 20, 0, 0.22))
            ctx.new_path()
            ctx.move_to(*tape[0])
            for p in tape[1:]:
                ctx.line_to(*p)
            ctx.close_path()
            ctx.set_source_rgba(*vb.rgba(TAPE, 0.8))
            ctx.fill()
            ctx.restore()

    # ---- a red-pencil scribble under the last row, drawn on ----
    done = t_first + (len(placed) - 1) * fpb * 0.5 + land
    last = [p for p in placed if abs(p[5] - placed[-1][5]) < size * 0.3]
    x0 = min(p[4] - p[2] / 2 for p in last) + size * 0.1
    x1 = max(p[4] + p[2] / 2 for p in last) - size * 0.1
    uy = max(p[5] + p[3] / 2 for p in last) + size * 0.16
    u = vb.ease_in_out_quart(vb.clamp01((n - done - fpb * 0.25) / (fpb * 0.75)))
    if u > 0:
        pts = []
        for k in range(61):
            q = k / 60
            pts.append((x0 + (x1 - x0) * q, uy + math.sin(q * math.pi * 1.0) * size * 0.05 - q * size * 0.04))
        back = [(x1 - (x1 - x0) * 0.85 * q, uy + size * 0.08 + math.sin(q * 3.0) * size * 0.02)
                for q in (k / 40 for k in range(41))]
        stroke = paths.jitter(pts + back, seed=7, amount=1.6, wander=0.4)
        paths.draw(cv, paths.reveal(stroke, u), accent, width=max(4, size * 0.085))

    # ---- the subtitle, on a strip of masking tape ----
    sub = data['subtitle']
    if sub:
        room = s.w * 0.86 - 40
        for sz in range(24, 11, -1):
            sf = kit.font(sz, 700)
            lines = text.wrap(sub, sf, room)
            if len(lines) <= 2 and all(text.measure(ln, sf) <= room for ln in lines):
                break
        sw, sh = text.block_size(lines, sf)
        a = done + fpb * 0.75
        if step(n) >= a:
            t = vb.ease_out_back(vb.clamp01((step(n) - a) / land))
            tw_, th_ = sw + 48, sh + 22
            cx, cy = s.cx, min(s.bottom - th_ / 2 - 8, bottom + 30 + th_ / 2)
            moving = step(n) < a + land + 2
            jx, jy, jr = boil('sub', n, 1.2) if moving else (0, 0, 0)
            pts = _torn(round(tw_), round(th_), 77, 2.5)
            ctx.save()
            ctx.translate(cx + jx, cy + jy + (1 - t) * 30)
            ctx.rotate(math.radians(-1.2) + jr)
            cv.shape_shadow(pts, dx=1, dy=2 + (1 - t) * 8, blur=round(5 + (1 - t) * 10), color=(40, 20, 0, 0.3))
            ctx.new_path()
            ctx.move_to(*pts[0])
            for p in pts[1:]:
                ctx.line_to(*p)
            ctx.close_path()
            ctx.set_source_rgba(*vb.rgba(TAPE, 0.93))
            ctx.fill()
            box = text.draw(cv, lines, sf, -sw / 2, -sh / 2, PRINT, align='center', width=sw)
            cv.mark('subtitle', *box)
            ctx.restore()


COMPONENT = Component(
    id='cut-paper-title',
    kind='title',
    description=('A ransom-note title: each word on its own torn paper scrap in mixed type, slapped onto a paper '
                 'wall one per half beat in stop-motion, underlined in red pencil, with an optional subtitle on '
                 'masking tape.'),
    tags=('title', 'paper', 'collage', 'handmade', 'stop-motion', 'craft', 'playful'),
    formats=('16x9', '9x16', '1x1'),
    beats=(4, 7),
    slots=(
        Slot('title', 'text', True, 'The headline, two to five short words; each word gets its own scrap.',
             max_length=30),
        Slot('subtitle', 'text', False, 'One short line on masking tape under the headline.', max_length=40),
        Slot('accent', 'color', False, 'Colour of every other scrap and the pencil underline; a warm, bold colour.'),
    ),
    sample={'title': 'Small hands, big plans', 'subtitle': 'A workshop for the weekend', 'accent': '#d2553a'},
    draw=draw,
)
