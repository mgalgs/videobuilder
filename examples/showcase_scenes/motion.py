"""The product's motion: Lumi the mascot hopping down today's tasks to check
them off (character motion, a staggered reveal, springs) and a whiteboard
flow drawn on with the camera on the pen. The transitions between sections
live in examples/showcase.py."""
import math

import videobuilder as vb
from videobuilder import Box, paths, text

from . import kit
from .kit import ACCENT, BG, CARD, CARD_HI, FPB, FPS, INK, LINE, MUTED, TEAL, pick

LABEL = kit.font(28, 600)
MONO = kit.mono(24, 500)


# ---- Lumi checks off the day: four task tiles stagger in, Lumi hops onto each on the beat ----
TASKS = (('Draft launch notes', '9:30'), ('Review the beta', '11:00'), ('Lunch with Sam', '12:30'),
         ('Deep work: pricing', '14:00'))
DROP, LANDS, JOY = 18, (30, 45, 60, 75), (94, 110)   # frames: Lumi drops in, lands on each tile, jumps for joy
FLIGHT = 9                                            # frames in the air between tiles
REST, CROUCH, STRETCH, SQUASH = (1.0, 1.0), (1.2, 0.76), (0.84, 1.26), (1.3, 0.7)


def lumi_layout(st):
    """The four task tiles and Lumi's size."""
    c = st.content
    if st.wide:
        gap, th = 32, 236
        tw = (c.w - 3 * gap) / 4
        tiles = [Box(c.x + i * (tw + gap), c.bottom - th, tw, th) for i in range(4)]
        return tiles, 136
    gap_x, th, gap_y = 30, 236, 196
    tw = (c.w - gap_x) / 2
    low = c.bottom - th
    high = low - gap_y - th
    tiles = [Box(c.x + (i % 2) * (tw + gap_x), (high, low)[i // 2], tw, th) for i in range(4)]
    return tiles, 140


def _lumi_path(f, spots):
    """Where Lumi's feet are, how squashed it is, and which way it looks, at frame f."""
    def squash(age):   # after a landing: a springy settle from the squash
        k = vb.spring_at(age, FPS, **vb.damped(0.3, hz=3.0))
        return kit.lerp(SQUASH[0], 1, k), kit.lerp(SQUASH[1], 1, k)

    if f < LANDS[0]:   # the drop onto the first tile
        t = vb.clamp01((f - DROP) / (LANDS[0] - DROP))
        x, y = spots[0]
        return (x, kit.lerp(y - 900, y, t * t)), STRETCH, 0
    hops = list(zip(LANDS, spots)) + [(JOY[1], spots[-1])]
    for k in range(len(hops) - 1):
        (t0, p0), (t1, p1) = hops[k], hops[k + 1]
        if f >= t1:
            continue
        flight = FLIGHT if k < len(hops) - 2 else JOY[1] - JOY[0]
        launch = t1 - flight
        look = (p1[0] > p0[0]) - (p1[0] < p0[0])
        if f < launch - 4:
            return p0, squash(f - t0), look
        if f < launch:
            u = vb.ease_in_out_quart((f - launch + 4) / 4)
            return p0, (kit.lerp(1, CROUCH[0], u), kit.lerp(1, CROUCH[1], u)), look
        u = (f - launch) / flight
        height = 150 if p0 == p1 else 120
        x = kit.lerp(p0[0], p1[0], u)
        y = kit.lerp(p0[1], p1[1], u) - height * 4 * u * (1 - u) - (60 * u if p1[1] < p0[1] else 0) * 4 * u * (1 - u)
        s = vb.clamp01(u / 0.4)
        return (x, y), (kit.lerp(STRETCH[0], 1, s), kit.lerp(STRETCH[1], 1, s)), look
    return spots[-1], squash(f - JOY[1]), 0


def draw_lumi(cv, cx, foot, base, scale, look=0.0, happy=False, name='lumi'):
    """Lumi: a warm blob with two eyes, its feet at (cx, foot)."""
    w, h = base * scale[0], base * scale[1]
    x, y = cx - w / 2, foot - h
    cv.rect(x, y, w, h, ACCENT, radius=min(w, h) / 2)
    cv.rect(x + w * 0.2, y + h * 0.1, w * 0.3, h * 0.14, (255, 255, 255, 0.22), radius=h * 0.07)
    er = 0.075 * base
    for ex in (-0.17, 0.17):
        ehx, ehy = cx + ex * w + look * 0.06 * w, y + h * 0.42
        if happy:   # closed, smiling eyes
            cv.arc(ehx, ehy + er * 0.6, er * 1.1, math.pi * 1.15, math.pi * 1.85, INK, width=er * 0.7)
        else:
            cv.rect(ehx - er, ehy - er * 1.3, 2 * er, 2.6 * er, INK, radius=er)
    if name:
        cv.mark(name, x, y, w, h - 2)


def lumi_tasks(cv, s, st):
    cv.fill(BG)
    c = st.content
    tiles, base = lumi_layout(st)
    f = s.f
    landed = [vb.clamp01((f - t) / 6) for t in LANDS]
    done = sum(1 for t in LANDS if f >= t)
    # The headline and the count, which turns over as tasks go.
    head_f = kit.font(pick(st, 52, 56), 800, tracking=-0.02)
    joy = kit.prog(f, JOY[0], JOY[0] + 10)
    for word, a in (('Today', 1 - joy), ('Done by lunch.', joy)):
        if a > 0.01:
            text.draw(cv, word, head_f, c.x, c.y + (1 - a) * (12 if word != 'Today' else -12), INK, alpha=a)
    hw = max(text.measure('Done by lunch.', head_f), text.measure('Today', head_f))
    cv.mark('headline', c.x, c.y, hw, text.line_height(head_f))
    count_f = kit.mono(pick(st, 30, 30), 600)
    count = f'{done} of 4 done'
    cw = text.measure('4 of 4 done', count_f)
    cy = c.y + (text.line_height(head_f) - text.line_height(count_f)) / 2
    cx = c.right - cw
    text.draw(cv, count, count_f, cx, cy, TEAL if done == 4 else MUTED)
    cv.mark('count', cx, cy, cw, text.line_height(count_f))
    # The tiles: staggered in on springs, each dipping when Lumi lands on it.
    spots = []
    title_f = kit.font(pick(st, 30, 30), 700, line_height=1.15)
    for i, (tile, (task, time)) in enumerate(zip(tiles, TASKS)):
        p = kit.spring(f, -3 + 4 * i, kit.BOUNCY)
        age = f - LANDS[i]
        dip = 14 * math.exp(-age / 5) * math.sin(age / 2.2) if age >= 0 else 0
        dy = (1 - p) * 120 + max(0, dip)
        spots.append((tile.cx, tile.y))
        with cv.layer(opacity=vb.clamp01(p * 1.5), dy=dy):
            cv.shadow(*tile, radius=22, dy=14, blur=34, color=(0, 0, 0, 0.4))
            cv.rect(*tile, kit.mix(CARD, '#1c2b2b', landed[i]), radius=22)
            cv.outline(*tile, kit.mix(LINE, TEAL, landed[i]), width=2, radius=22)
            inner = tile.pad(26, 26)
            r = 22
            bx, by = inner.x + r, inner.y + r
            cv.arc(bx, by, r - 2, 0, 2 * math.pi, kit.mix(MUTED, TEAL, landed[i]), width=4)
            if landed[i] > 0:
                k = landed[i]
                cv.rect(bx - r * k, by - r * k, 2 * r * k, 2 * r * k, TEAL, radius=r * k)
                tick = [(bx - 9, by + 1), (bx - 2, by + 8), (bx + 11, by - 8)]
                paths.draw(cv, paths.reveal(tick, k), BG, width=5)
            lines, (lw, lh) = kit.lines_of(task, title_f, inner.w)
            ty = inner.y + 2 * r + 22
            text.draw(cv, lines, title_f, inner.x, ty, kit.mix(INK, MUTED, landed[i]))
            if landed[i] > 0:   # struck through as it's done
                for j, line in enumerate(lines):
                    ly = ty + j * text.line_height(title_f) + text.line_height(title_f) * 0.55
                    cv.rect(inner.x, ly, text.measure(line, title_f) * landed[i], 3, MUTED)
            text.draw(cv, time, MONO, inner.x, inner.bottom - text.line_height(MONO), MUTED)
        cv.mark(f'tile-{i}', tile.x, tile.y + dy, tile.w, tile.h)
    if f < DROP:
        return
    (x, foot), scale, look = _lumi_path(f, spots)
    # Feet follow the tile under them as it dips.
    for i, t in enumerate(LANDS):
        if abs(x - spots[i][0]) < 1 and abs(foot - spots[i][1]) < 1 and f >= t:
            age = f - t
            foot += max(0, 14 * math.exp(-age / 5) * math.sin(age / 2.2))
    draw_lumi(cv, x, foot, base, scale, look, happy=f >= JOY[0])


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


SCENES = {
    'lumi': lumi_tasks,
    'diagram': diagram,
}
