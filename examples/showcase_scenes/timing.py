"""The Timing, sound and formats block: four hard cuts on four beats, and a
frame that reflows between three shapes. (The loop is the end card, in
examples/showcase.py.)"""
import math

import videobuilder as vb
from videobuilder import Box, text

from . import kit
from .kit import ACCENT, BG, CARD, CARD_HI, FPB, INK, LINE, MUTED, TEAL, pick

MONO = kit.mono(26, 600)

# ---- cuts locked to the music: a word a beat, a hard cut on each ----
BEAT_WORDS = ('Cut', 'on', 'every', 'beat.')
BEAT_SPOTS = ((0.28, 0.38), (0.72, 0.30), (0.30, 0.58), (0.66, 0.50))   # where each word lands, in the stage


def beat_lock(cv, s, st):
    k = int(s.name.split('-')[1]) - 1
    cv.fill(BG if k % 2 == 0 else CARD)
    c = st.content
    strip_h = pick(st, 120, 150)
    stage = Box(c.x, c.y, c.w, c.h - strip_h - 30)
    word = BEAT_WORDS[k]
    f = kit.font(pick(st, 190, 170), 900, tracking=-0.04)
    w = text.measure(word, f)
    lh = text.line_height(f)
    u, v = BEAT_SPOTS[k] if st.wide else (0.5, (0.22, 0.42, 0.58, 0.76)[k])
    x = min(max(stage.x, stage.x + u * stage.w - w / 2), stage.right - w)
    y = stage.y + v * stage.h - lh / 2
    p = min(1.0, kit.spring(s.f, -3, vb.damped(0.5, hz=3)))
    with kit.scaled(cv, x + w / 2, y + lh / 2, 1.25 - 0.25 * p):
        text.draw(cv, word, f, x, y, ACCENT if k == 3 else INK)
    cv.mark('word', x, y, w, lh)
    # The music under it: a kick envelope per beat, the four cuts marked, a playhead.
    strip = Box(c.x, c.bottom - strip_h, c.w, strip_h)
    g = s.group_f
    span = 4 * FPB
    bars = 64
    for i in range(bars):
        t = i / bars
        beat_phase = (t * 4) % 1
        amp = 0.18 + 0.82 * math.exp(-beat_phase * 7) + 0.12 * math.exp(-((beat_phase - 0.5) % 1) * 20)
        bh = (strip_h - 40) * min(1, amp)
        bx = strip.x + t * strip.w
        cv.rect(bx, strip.y + (strip_h - 40) / 2 - bh / 2 + 4, strip.w / bars - 3, bh,
                TEAL if t * span <= g else LINE, radius=2)
    for j in range(4):
        mx = strip.x + j * strip.w / 4
        hit = j <= k
        cv.rect(mx - 1.5, strip.y - 6, 3, strip_h - 30, ACCENT if hit else MUTED, alpha=1 if hit else 0.5)
        lab = f'cut {j + 1}'
        text.draw(cv, lab, MONO, mx + 10, strip.bottom - 30, ACCENT if hit else MUTED)
    px = strip.x + strip.w * g / span
    cv.rect(px - 2, strip.y - 14, 4, strip_h - 14, INK)
    cv.mark('music', *strip)


# ---- every format, recomposed: one promo card, laid out for each shape ----
# Each element by centre (fractions of the frame) and size (fractions of its short side).
SHAPES = {
    '16:9': dict(aspect=16 / 9, logo=(0.1, 0.27, 0.13), word=(0.36, 0.27, 0.19), tag=(0.3, 0.5, 0.075, 0.48),
                 button=(0.27, 0.73, 0.36, 0.14), phone=(0.76, 0.5, 0.84)),
    '1:1': dict(aspect=1.0, logo=(0.16, 0.15, 0.11), word=(0.55, 0.15, 0.15), tag=(0.5, 0.31, 0.06, 0.84),
                button=(0.5, 0.89, 0.5, 0.1), phone=(0.5, 0.6, 0.42)),
    '9:16': dict(aspect=9 / 16, logo=(0.5, 0.1, 0.2), word=(0.5, 0.22, 0.2), tag=(0.5, 0.35, 0.075, 0.86),
                 button=(0.5, 0.9, 0.7, 0.075), phone=(0.5, 0.62, 0.36)),
}
HOLD_A, MOVE_A, HOLD_B, MOVE_B = 16, 30, 40, 54


def _mix(a, b, t):
    if isinstance(a, tuple):
        return tuple(kit.lerp(x, y, t) for x, y in zip(a, b))
    return math.exp(kit.lerp(math.log(a), math.log(b), t))


def every_format(cv, s, st):
    cv.fill(BG)
    c = st.content
    order = ('9:16', '1:1', '16:9') if st.wide else ('16:9', '1:1', '9:16')   # end on the film's own shape
    t1 = vb.ease_in_out_quart(vb.clamp01((s.f - HOLD_A) / (MOVE_A - HOLD_A)))
    t2 = vb.ease_in_out_quart(vb.clamp01((s.f - HOLD_B) / (MOVE_B - HOLD_B)))
    a, b, z = (SHAPES[n] for n in order)
    L = {key: _mix(_mix(a[key], b[key], t1), z[key], t2) if t2 > 0 else _mix(a[key], b[key], t1) for key in a}
    label_h = 64
    area = Box(c.x, c.y + label_h, c.w, c.h - label_h)
    ar = L['aspect']
    w = min(area.w, area.h * ar)
    h = w / ar
    dev = Box(area.cx - w / 2, area.cy - h / 2, w, h)
    cv.shadow(*dev, radius=24, dy=18, blur=40, color=(0, 0, 0, 0.45))
    cv.rect(*dev, CARD, radius=24)
    cv.outline(*dev, LINE, width=2, radius=24)
    cv.mark('frame', *dev)
    short = min(w, h)

    def at(u, v):
        return dev.x + u * w, dev.y + v * h

    px, py = at(*L['phone'][:2])
    ph = L['phone'][2] * h
    pw = ph * 0.5
    phone = Box(px - pw / 2, py - ph / 2, pw, ph)
    cv.rect(*phone, '#0b0c10', radius=pw * 0.14)
    scr = phone.pad(pw * 0.05)
    cv.rect(*scr, BG, radius=pw * 0.1)
    kit.logo(cv, scr.cx, scr.y + scr.h * 0.22, scr.w * 0.18, -0.6, name=None)
    for i in range(4):
        cv.rect(scr.x + scr.w * 0.1, scr.y + scr.h * (0.42 + i * 0.12), scr.w * (0.8 - 0.12 * (i % 2)),
                scr.h * 0.07, CARD_HI, radius=scr.h * 0.035)
    lx, ly = at(*L['logo'][:2])
    kit.logo(cv, lx, ly, L['logo'][2] * short / 2, -0.6, name=None)
    wx, wy = at(*L['word'][:2])
    wf = kit.font(max(8, L['word'][2] * short), 850, tracking=-0.03)
    ww, wh = text.measure('Lumen', wf), text.line_height(wf)
    text.draw(cv, 'Lumen', wf, wx - ww / 2, wy - wh / 2, INK)
    tx, ty = at(*L['tag'][:2])
    tf = kit.font(max(8, L['tag'][2] * short), 600)
    width = L['tag'][3] * w
    lines, (lw, lh) = kit.lines_of('One calm plan for your day.', tf, width)
    text.draw(cv, lines, tf, tx - width / 2, ty - lh / 2, MUTED, align='center', width=width)
    bx, by = at(*L['button'][:2])
    bw, bh = L['button'][2] * w, L['button'][3] * h
    cv.rect(bx - bw / 2, by - bh / 2, bw, bh, ACCENT, radius=bh / 2)
    bf = kit.font(max(8, bh * 0.42), 800)
    bt = 'Get Lumen'
    text.draw(cv, bt, bf, bx - text.measure(bt, bf) / 2, by - text.line_height(bf) / 2, BG)
    # Which shape it is right now.
    name = order[0] if s.f < (HOLD_A + MOVE_A) / 2 else order[1] if s.f < (HOLD_B + MOVE_B) / 2 else order[2]
    chip_f = kit.mono(30, 700)
    cw = text.measure(name, chip_f)
    cx = c.cx - (cw + 40) / 2
    cv.rect(cx, c.y, cw + 40, 46, CARD_HI, radius=23)
    text.draw(cv, name, chip_f, cx + 20, c.y + 23 - text.line_height(chip_f) / 2, INK)
    cv.mark('shape-name', cx, c.y, cw + 40, 46)


SCENES = {f'beat-{i + 1}': beat_lock for i in range(4)}
SCENES['every-format'] = every_format
