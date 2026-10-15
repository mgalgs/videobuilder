"""The Motion block: eased entrances, springs, a stagger, a beat pop, a
character hop, an overlap transition, a drawn-on diagram and a shape morph,
each showing a piece of Lumen."""
import math

import videobuilder as vb
from videobuilder import Box, fr, paths, text

from . import kit
from .kit import ACCENT, BG, CARD, CARD_HI, FPB, FPS, INK, LINE, MUTED, TEAL, pick

HEAD = {True: kit.font(46, 800, tracking=-0.02), False: kit.font(52, 800, tracking=-0.02, line_height=1.08)}
LABEL = kit.font(28, 600)
SMALL = kit.font(22, 600)
MONO = kit.mono(24, 500)


def headline(cv, st, copy, x, y, width, f=0, align='left', name='headline'):
    """A shot's headline, already up on the cut."""
    p = kit.spring(f, -4)
    lines, (w, h) = kit.lines_of(copy, HEAD[st.wide], width)
    with cv.layer(opacity=min(1, p), dy=(1 - min(1, p)) * 16):
        box = text.draw(cv, lines, HEAD[st.wide], x, y, INK, align=align, width=width if align != 'left' else None)
    cv.mark(name, *box)
    return box


# ---- eased entrances: one chip per motion token ----
EASES = (('out-expo', vb.ease_out_expo, 'Today'), ('out-quint', vb.ease_out_quint, 'Focus'),
         ('in-out-quart', vb.ease_in_out_quart, 'Calendar'), ('out-back', vb.ease_out_back, 'Habits'),
         ('in-expo', vb.ease_in_expo, 'Notes'))


def eased_entrances(cv, s, st):
    cv.fill(BG)
    c = st.content
    head = headline(cv, st, 'Five ways to arrive.', c.x, c.y + pick(st, 0, 20), c.w, s.f)
    top = head.bottom + pick(st, 34, 60)
    row_h = (c.bottom - top) / len(EASES)
    chip_w, chip_h = pick(st, 260, 240), pick(st, 66, 72)
    for i, (name, ease, word) in enumerate(EASES):
        y = top + i * row_h
        if st.wide:
            lx, track = c.x, Box(c.x + 230, y, c.w - 230, chip_h)
            ly = y + (chip_h - text.line_height(MONO)) / 2
        else:
            lx, ly = c.x, y
            track = Box(c.x, y + 40, c.w, chip_h)
        text.draw(cv, name, MONO, lx, ly, MUTED)
        cv.mark(f'ease-{i}', lx, ly, text.measure(name, MONO), text.line_height(MONO))
        cv.rect(track.x, track.cy - 1, track.w, 2, LINE)
        t = ease(vb.clamp01((s.f - 1) / 26))
        x = kit.lerp(track.x, track.right - chip_w - 70, t)  # room for out-back's overshoot
        cv.rect(x, track.y, chip_w, chip_h, CARD_HI, radius=chip_h / 2)
        col = ACCENT if i % 2 == 0 else TEAL
        cv.rect(x + 18, track.cy - 9, 18, 18, col, radius=9)
        text.draw(cv, word, LABEL, x + 50, track.cy - text.line_height(LABEL) / 2, INK)
        cv.mark(f'chip-{i}', x, track.y, chip_w, chip_h)


# ---- springs with character: three icons, three damping ratios ----
DAMPINGS = ((1.0, 'firm'), (0.6, 'restrained'), (0.3, 'playful'))


def app_icon(cv, x, y, d, name=None):
    """Lumen's app icon: the logo on a dark rounded square."""
    cv.shadow(x, y, d, d, radius=d * 0.24, dy=d * 0.08, blur=d * 0.25, color=(0, 0, 0, 0.45))
    cv.rect(x, y, d, d, CARD_HI, radius=d * 0.24)
    kit.logo(cv, x + d / 2, y + d / 2, d * 0.32, -0.6, name=None)
    if name:
        cv.mark(name, x, y, d, d)


def springs(cv, s, st):
    cv.fill(BG)
    c = st.content
    headline(cv, st, 'Pick the bounce.', c.x, c.y + pick(st, 0, 20), c.w, s.f, align='center')
    d = pick(st, 190, 176)
    shelf = c.y + pick(st, 0.72, 0.66) * c.h
    span = pick(st, 1000, c.w)
    x0 = c.cx - span / 2
    cv.rect(x0, shelf, span, 3, LINE)
    for i, (ratio, word) in enumerate(DAMPINGS):
        cx = x0 + span * (i + 0.5) / 3
        p = vb.spring_at(s.f + 3, FPS, **vb.damped(ratio, hz=2.0))
        y = shelf - d - abs(1 - p) * pick(st, 520, 700)  # an overshoot bounces off the shelf
        app_icon(cv, cx - d / 2, y, d, f'icon-{i}')
        lab = f'{word} · {ratio:.1f}'
        lw = text.measure(lab, LABEL)
        text.draw(cv, lab, LABEL, cx - lw / 2, shelf + 28, INK if i == 2 else MUTED)
        cv.mark(f'ratio-{i}', cx - lw / 2, shelf + 28, lw, text.line_height(LABEL))


# ---- staggered reveals: today's list cascades in ----
TASKS = (('9:30', 'Stand-up', TEAL), ('10:00', 'Draft launch notes', ACCENT), ('11:30', 'Review the beta', TEAL),
         ('12:30', 'Lunch with Sam', MUTED), ('14:00', 'Deep work: pricing', ACCENT))


def task_card(cv, box, f, stagger=4, first=1, name='list'):
    cv.shadow(*box, radius=24, dy=16, blur=40, color=(0, 0, 0, 0.4))
    cv.rect(*box, CARD, radius=24)
    inner = box.pad(28, 30)
    title_f = kit.font(30, 750)
    text.draw(cv, 'Today', title_f, inner.x, inner.y, INK)
    text.draw(cv, 'Friday', SMALL, inner.right - text.measure('Friday', SMALL), inner.y + 6, MUTED)
    top = inner.y + 64
    row = (inner.bottom - top) / len(TASKS)
    for i, (time, task, col) in enumerate(TASKS):
        p = kit.spring(f, first + stagger * i, kit.BOUNCY)
        y = top + i * row
        with cv.layer(opacity=vb.clamp01(p), dx=(1 - p) * 70):
            cv.rect(inner.x, y + 4, inner.w, row - 8, CARD_HI, radius=14)
            cv.outline(inner.x + 18, y + row / 2 - 11, 22, 22, col, width=3, radius=11)
            text.draw(cv, task, LABEL, inner.x + 56, y + row / 2 - text.line_height(LABEL) / 2, INK)
            text.draw(cv, time, MONO, inner.right - 18 - text.measure(time, MONO),
                      y + row / 2 - text.line_height(MONO) / 2, MUTED)
    cv.mark(name, *box)


def staggered(cv, s, st):
    cv.fill(BG)
    c = st.content
    if st.wide:
        left, right = c.row(0.85 * fr, fr, gap=60)
        f = kit.font(64, 800, tracking=-0.025, line_height=1.05)
        lines, (w, h) = kit.lines_of('Your whole day, at a glance.', f, left.w)
        p = min(1, kit.spring(s.f, -4))
        with cv.layer(opacity=p):
            box = text.draw(cv, lines, f, left.x, left.cy - h / 2, INK)
        cv.mark('headline', *box)
        card = right.pad(10, 0)
    else:
        head = headline(cv, st, 'Your whole day, at a glance.', c.x, c.y + 20, c.w, s.f)
        card = Box(c.x, head.bottom + 50, c.w, min(760, c.bottom - head.bottom - 60))
    task_card(cv, card, s.f)


# ---- pop on the beat: the icon punches on every beat of launch week ----
DAYS = ('Mon', 'Tue', 'Wed', 'Thu')


def pop(cv, s, st):
    cv.fill(BG)
    c = st.content
    d = pick(st, 210, 240)
    cx, cy = c.cx, c.y + pick(st, 0.42, 0.42) * c.h
    beat = s.f // FPB
    since = s.f - beat * FPB
    punch = 1 + 0.2 * (1 - vb.spring_at(since + 1, FPS, **vb.damped(0.3, hz=3.2)))
    for k in range(beat + 1):  # a ripple off each beat so far
        age = s.f - k * FPB
        if 0 <= age < 24:
            r = d * 0.6 + age * 9
            cv.arc(cx, cy, r, 0, 2 * math.pi, ACCENT, width=4, alpha=0.6 * (1 - age / 24))
    with kit.scaled(cv, cx, cy, punch):
        app_icon(cv, cx - d / 2, cy - d / 2, d, 'icon')
    gap = pick(st, 120, 130)
    y = cy + d / 2 + pick(st, 70, 110)
    for i, day in enumerate(DAYS):
        x = cx + (i - 1.5) * gap
        lit = i <= beat
        r = 14 * (1 + 0.4 * (1 - vb.spring_at(since + 1, FPS, **vb.damped(0.4, hz=3))) * (i == beat))
        cv.rect(x - r, y - r, 2 * r, 2 * r, ACCENT if lit else LINE, radius=r)
        w = text.measure(day, LABEL)
        text.draw(cv, day, LABEL, x - w / 2, y + 30, INK if lit else MUTED)
    cv.mark('days', cx - 1.5 * gap - 30, y - 20, 3 * gap + 60, 30 + 20 + text.line_height(LABEL))
    head_f = kit.font(pick(st, 34, 40), 700)
    word = 'Launch week'
    w = text.measure(word, head_f)
    hy = cy - d / 2 - pick(st, 86, 140)
    text.draw(cv, word, head_f, cx - w / 2, hy, MUTED)
    cv.mark('headline', cx - w / 2, hy, w, text.line_height(head_f))


# ---- character motion: Lumi the mascot hops up onto "Done" ----
REST, CROUCH, STRETCH, SQUASH = (1.0, 1.0), (1.22, 0.74), (0.84, 1.3), (1.28, 0.7)
ANTIC, HOLD, LAUNCH, LAND = 7, 10, 13, 30


def _squash(f):
    def go(a, b, t, ease=vb.ease_in_out_quart):
        return kit.lerp(a[0], b[0], ease(t)), kit.lerp(a[1], b[1], ease(t))
    if f < ANTIC:
        return go(REST, CROUCH, f / ANTIC)
    if f < HOLD:
        return CROUCH
    if f < LAUNCH:
        return go(CROUCH, STRETCH, (f - HOLD) / (LAUNCH - HOLD))
    if f < LAND:
        p = (f - LAUNCH) / (LAND - LAUNCH)
        if p < 0.35:
            return go(STRETCH, REST, p / 0.35, vb.ease_out_quint)
        if p < 0.8:
            return REST
        return go(REST, SQUASH, (p - 0.8) / 0.2)
    k = vb.spring_at(f - LAND, FPS, **vb.damped(0.22, hz=2.4))
    return kit.lerp(SQUASH[0], 1, k), kit.lerp(SQUASH[1], 1, k)


def character(cv, s, st):
    cv.fill(BG)
    c = st.content
    f = s.f
    base = pick(st, 150, 160)
    hop_x, hop_y = pick(st, (380, 120), (300, 200))
    start = (c.cx - hop_x / 2 - pick(st, 40, 0), c.y + c.h * pick(st, 0.72, 0.62))
    end = (start[0] + hop_x, start[1] - hop_y)
    # The two ledges: a plain one, and the one marked Done.
    for (x, y), word in ((start, None), (end, 'Done')):
        w = pick(st, 250, 230)
        cv.rect(x - w / 2, y, w, 18, CARD_HI, radius=9)
        if word:
            lw = text.measure(word, LABEL)
            text.draw(cv, word, LABEL, x - lw / 2, y + 34, TEAL)
            cv.mark('done', x - w / 2, y, w, 34 + text.line_height(LABEL))
        else:
            cv.mark('ledge', x - w / 2, y, w, 18)
    if f < LAUNCH:
        cx, foot = start
    elif f < LAND:
        p = (f - LAUNCH) / (LAND - LAUNCH)
        cx = kit.lerp(start[0], end[0], p)
        foot = kit.lerp(start[1], end[1], p) - pick(st, 190, 230) * 4 * p * (1 - p)
    else:
        cx, foot = end
    sx, sy = _squash(f)
    w, h = base * sx, base * sy
    ground = start[1] if f < (LAUNCH + LAND) / 2 else end[1]
    lift = vb.clamp01((ground - foot) / 260)
    sw = w * (1 - 0.5 * lift)
    cv.rect(cx - sw / 2, ground - 7, sw, 14, (0, 0, 0, 0.45 * (1 - lift)), radius=7)
    x, y = cx - w / 2, foot - h
    cv.rect(x, y, w, h, ACCENT, radius=min(w, h) / 2)
    look = 0.12 * w if LAUNCH - 4 <= f < LAND else 0.04 * w
    for ex in (-0.17, 0.17):
        er = 0.075 * base
        ehx, ehy = cx + ex * w + look, y + h * 0.4
        cv.rect(ehx - er, ehy - er * 1.3, 2 * er, 2.6 * er, INK, radius=er)
    cv.mark('lumi', x, y, w, h)


# ---- overlap transitions: the week view slides in over the hop ----
WEEK = ((0, 0.10, 0.22, TEAL), (0, 0.45, 0.30, ACCENT), (1, 0.18, 0.40, ACCENT), (2, 0.05, 0.18, TEAL),
        (2, 0.55, 0.25, TEAL), (3, 0.30, 0.45, ACCENT), (4, 0.12, 0.20, TEAL), (4, 0.50, 0.32, ACCENT),
        (5, 0.62, 0.20, TEAL), (6, 0.25, 0.30, MUTED))


def week(cv, s, st):
    c = st.content
    frame = st.frame
    p = kit.prog(s.f, 0, FPB, vb.ease_out_quint)
    if p < 1:
        cv.rect(*frame, (8, 9, 12, 0.55 * p))  # the outgoing shot dims as it's covered
    dx, dy = pick(st, ((1 - p) * frame.w, 0), (0, (1 - p) * frame.h))
    with cv.layer(dx=dx, dy=dy):
        if p < 1:
            cv.shadow(*frame, radius=28, dx=-20 if st.wide else 0, dy=0 if st.wide else -20, blur=50,
                      color=(0, 0, 0, 0.6))
        cv.rect(*frame, BG, radius=28 * (1 - p))
        head = headline(cv, st, 'This week', c.x, c.y + pick(st, 0, 20), c.w, s.f)
        grid = Box(c.x, head.bottom + 36, c.w, c.bottom - head.bottom - 36)
        cols = grid.row(*([fr] * 7), gap=pick(st, 14, 8))
        for i, (col, day) in enumerate(zip(cols, 'MTWTFSS')):
            w = text.measure(day, LABEL)
            text.draw(cv, day, LABEL, col.cx - w / 2, col.y, INK if i < 5 else MUTED)
            body = Box(col.x, col.y + 44, col.w, col.h - 44)
            cv.rect(*body, CARD, radius=12)
        for day, at, length, colour in WEEK:
            col = cols[day]
            body = Box(col.x, col.y + 44, col.w, col.h - 44)
            g = kit.spring(s.f, FPB - 2 + 2 * day, kit.BOUNCY)
            h = body.h * length * max(0.0, min(1.15, g))
            if h > 1:
                cv.rect(body.x + 6, body.y + body.h * at, body.w - 12, h, colour, radius=8, alpha=0.9)
        cv.mark('week', *grid)


# ---- drawn-on diagram: a whiteboard flow, the camera on the pen ----
STEPS = ('Capture', 'Plan', 'Focus', 'Done')
STEP_F = kit.font(40, 650)


def _board(wide):
    """The board's strokes, in order, and its labels: four boxes joined by arrows,
    left to right for 16:9 and top to bottom for 9:16. Board units are px at zoom 1."""
    bw, bh, gap = (260, 130, 150) if wide else (300, 130, 120)
    strokes, labels = [], []
    for i, word in enumerate(STEPS):
        x, y = ((i * (bw + gap), 0) if wide else (0, i * (bh + gap)))
        box = paths.resample(kit.rect_points(x, y, bw, bh) + [(x, y)], 48)
        strokes.append((paths.jitter(box, seed=10 + i, amount=2.4, wander=0.35), INK, 5))
        labels.append((word, x + bw / 2, y + bh / 2, len(strokes) - 1))
        if i < len(STEPS) - 1:
            if wide:
                a, b = (x + bw + 18, y + bh / 2), (x + bw + gap - 18, y + bh / 2)
                head = [(b[0] - 22, b[1] - 16), b, (b[0] - 22, b[1] + 16)]
            else:
                a, b = (x + bw / 2, y + bh + 16), (x + bw / 2, y + bh + gap - 16)
                head = [(b[0] - 16, b[1] - 22), b, (b[0] + 16, b[1] - 22)]
            line = paths.jitter(paths.resample([a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - (14 if wide else 0)), b], 20),
                                seed=30 + i, amount=1.6)
            strokes.append((line + paths.jitter(head, seed=40 + i, amount=1.2), TEAL, 5))
    x, y = labels[-1][1], labels[-1][2]
    tick = [(x + bw / 2 - 8, y - bh / 2 - 6), (x + bw / 2 + 14, y - bh / 2 + 18), (x + bw / 2 + 56, y - bh / 2 - 36)]
    strokes.append((paths.jitter(paths.resample(tick, 16), seed=55, amount=1.2), ACCENT, 8))
    xs = [p[0] for st, _, _ in strokes for p in st]
    ys = [p[1] for st, _, _ in strokes for p in st]
    return strokes, labels, Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


BOARDS = {True: _board(True), False: _board(False)}
DRAW_END, PULL = 48, (48, 64)
LEAD = 8  # the pen is already a few frames in on the cut


def _drawn(f):
    return vb.ease_in_out_quart(vb.clamp01((f + LEAD) / (DRAW_END + LEAD)))


def _pen(strokes, t):
    """How far along each stroke the pen is at overall fraction t, and the pen tip."""
    lengths = [paths.length(p) for p, _, _ in strokes]
    left = t * sum(lengths)
    out, tip = [], strokes[0][0][0]
    for (pts, _, _), L in zip(strokes, lengths):
        k = vb.clamp01(left / L) if L else 1
        out.append(k)
        if 0 < k:
            part = paths.reveal(pts, k)
            tip = part[-1]
        left -= L
    return out, tip


def diagram(cv, s, st):
    cv.fill(BG)
    c = st.content
    strokes, labels, bounds = BOARDS[st.wide]
    t = _drawn(s.f)
    done, tip = _pen(strokes, t)
    # The camera trails the pen (an average of where it has been), zoomed in, then pulls back.
    trail = [_pen(strokes, _drawn(s.f - k))[1] for k in range(0, 10, 2)]
    cam = (sum(p[0] for p in trail) / len(trail), sum(p[1] for p in trail) / len(trail))
    fit = min(c.w / (bounds.w + 80), c.h / (bounds.h + 80))
    close = fit * pick(st, 2.0, 1.7)
    pull = kit.prog(s.f, *PULL, kit.SMOOTH)
    centre = (bounds.cx, bounds.cy)
    cx, cy = kit.lerp(cam[0], centre[0], pull), kit.lerp(cam[1], centre[1], pull)
    z = vb.log_lerp(close, fit, pull)
    with cv.layer(dx=c.cx - cx * z, dy=c.cy - cy * z, scale=z):
        for gx in range(int(bounds.x - 400) // 60 * 60, int(bounds.right + 400), 60):
            for gy in range(int(bounds.y - 400) // 60 * 60, int(bounds.bottom + 400), 60):
                cv.rect(gx - 1.5, gy - 1.5, 3, 3, LINE)
        for (pts, colour, width), k in zip(strokes, done):
            if k > 0:
                paths.draw(cv, paths.reveal(pts, k), colour, width=width)
        for word, x, y, i in labels:
            a = vb.clamp01((done[i] - 0.6) / 0.4)
            if a > 0:
                w = text.measure(word, STEP_F)
                text.draw(cv, word, STEP_F, x - w / 2, y - text.line_height(STEP_F) / 2, INK, alpha=a)
        if s.f < DRAW_END + 2:
            cv.rect(tip[0] - 7, tip[1] - 7, 14, 14, ACCENT, radius=7)
    cv.mark('diagram', *c)


# ---- shape morph: an idea (the orb) becomes a plan (a document) ----
def _morph_shapes(cx, cy, r):
    circle = [(cx + r * math.cos(2 * math.pi * i / 64), cy + r * math.sin(2 * math.pi * i / 64)) for i in range(64)]
    w, h, fold = r * 1.5, r * 1.92, r * 0.34
    x0, y0 = cx - w / 2, cy - h / 2
    doc = [(x0, y0), (x0 + w - fold, y0), (x0 + w, y0 + fold), (x0 + w, y0 + h), (x0, y0 + h)]
    return circle, doc


def smootherstep(t):
    return 6 * t ** 5 - 15 * t ** 4 + 10 * t ** 3


def morph(cv, s, st):
    cv.fill(BG)
    c = st.content
    r = pick(st, 170, 190)
    cx, cy = (c.cx - 250, c.cy) if st.wide else (c.cx, c.y + c.h * 0.4)
    circle, doc = _morph_shapes(cx, cy, r)
    t = smootherstep(vb.clamp01((s.f - 6) / 28))
    shape = paths.morph(circle, doc, t, closed=True)
    kit.glow(cv, cx, cy, r * 2.2, kit.mix(ACCENT, TEAL, t), 0.25)
    paths.draw(cv, shape, kit.mix(ACCENT, TEAL, t), fill=True)
    if t > 0.85:  # the plan's lines are written once it's a page
        a = (t - 0.85) / 0.15
        for i, frac in enumerate((0.62, 0.8, 0.5, 0.7)):
            y = cy - r * 0.5 + i * r * 0.32
            cv.rect(cx - r * 0.55, y, r * 1.1 * frac, r * 0.1, BG, radius=r * 0.05, alpha=0.55 * a)
    xs, ys = [p[0] for p in shape], [p[1] for p in shape]
    cv.mark('shape', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    f = kit.font(pick(st, 64, 60), 800, tracking=-0.02)
    if st.wide:
        lx, ly, align, width = cx + r + 110, cy - 50, 'left', 460
    else:
        lx, ly, align, width = c.x, cy + r * 1.25 + 50, 'center', c.w
    for word, a in (('An idea', 1 - t), ('A plan', t)):
        if a > 0.01:
            text.draw(cv, word, f, lx, ly + (1 - a) * (14 if word == 'A plan' else -14), INK, align=align,
                      width=width if align == 'center' else None, alpha=a)
    cv.mark('word', lx if st.wide else c.cx - 160, ly, text.measure('An idea', f) if st.wide else 320,
            text.line_height(f))


SCENES = {
    'eased-entrances': eased_entrances,
    'springs-with-character': springs,
    'staggered-reveals': staggered,
    'pop-on-the-beat': pop,
    'character-motion': character,
    'overlap-transitions': week,
    'drawn-on-diagram': diagram,
    'shape-morph': morph,
}
