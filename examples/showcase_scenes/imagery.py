"""The product, on screen: a camera gliding down Lumen's dashboard, and the
focus settings panel redrawn as vectors, its blocks easing in. Every picture
is made here."""
from functools import lru_cache

import videobuilder as vb
from videobuilder import Box, fr, text

from . import kit
from .kit import ACCENT, BG, CARD, CARD_HI, INK, LINE, MUTED, TEAL, pick

LABEL = kit.font(28, 600)
SMALL = kit.font(24, 600)


# ---- Lumen's dashboard: a page taller than any window, drawn once at 2x ----
# Two layouts: the web page for 16:9, the phone app's single column for 9:16.
NAV_H, PAGE_SCALE = 110, 2
PAGES = {True: (1200, 2000), False: (640, 2440)}
MARGIN = 80   # the camera's push-in crops less than this off each side


def _draw_page(cv, wide):
    W, H = PAGES[wide]
    m = MARGIN if wide else 44
    cv.fill('#f1f2f4')
    dark, muted, card, border = '#1c1e25', '#7b818d', '#ffffff', '#dfe2e7'
    cv.rect(0, 0, W, NAV_H, BG)
    kit.logo(cv, m + 4, NAV_H / 2, 26, -0.6, name=None)
    text.draw(cv, 'Lumen', kit.font(34, 800, tracking=-0.02), m + 44, NAV_H / 2 - 22, INK)
    if wide:
        for i, word in enumerate(('Today', 'Week', 'Focus', 'Insights')):
            text.draw(cv, word, kit.font(24, 600), 560 + i * 150, NAV_H / 2 - 15, INK if i == 0 else MUTED)
    else:
        text.draw(cv, 'Today', kit.font(24, 600), W - m - text.measure('Today', kit.font(24, 600)), NAV_H / 2 - 15, INK)
    text.draw(cv, 'Good morning, Alex', kit.font(64 if wide else 52, 800, tracking=-0.02), m, 160, dark)
    sub = 'Friday · 5 things planned, 2 hours of focus booked'
    sub_f = kit.font(28 if wide else 26, 500)
    lines = text.wrap(sub, sub_f, W - 2 * m)
    box = text.draw(cv, lines, sub_f, m, 250 if wide else 236, muted)
    stats = (('Focus today', '4h 20m', '+40m on last Friday', TEAL), ('Tasks done', '12 / 14', '2 left before 6pm', ACCENT),
             ('Streak', '9 days', 'Your longest yet', TEAL))
    inner = W - 2 * m
    if wide:
        y, cw, ch = 330, (inner - 2 * 30) / 3, 220
        spots = [(m + i * (cw + 30), y) for i in range(3)]
    else:
        y, cw, ch = box.bottom + 40, inner, 170
        spots = [(m, y + i * (ch + 24)) for i in range(3)]
    for (x, y), (lab, val, sub, col) in zip(spots, stats):
        cv.rect(x, y, cw, ch, card, radius=22)
        cv.outline(x, y, cw, ch, border, width=2, radius=22)
        text.draw(cv, lab, kit.font(24, 600), x + 30, y + 26, muted)
        text.draw(cv, val, kit.mono(56, 700), x + 30, y + 64, dark)
        text.draw(cv, sub, kit.font(22, 600), x + 30, y + ch - 50, col)
    y = spots[-1][1] + ch + 50
    chart_h = 600 if wide else 560
    cv.rect(m, y, inner, chart_h, card, radius=22)
    cv.outline(m, y, inner, chart_h, border, width=2, radius=22)
    text.draw(cv, 'Focus hours this week', kit.font(34, 750), m + 40, y + 40, dark)
    hours = (3.5, 4.2, 2.8, 5.1, 4.3, 1.2, 0.6)
    step = (inner - 80) / 7
    bw = step * 0.62
    for i, (h, day) in enumerate(zip(hours, ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'))):
        x = m + 40 + i * step + (step - bw) / 2
        bh = (chart_h - 240) * h / 5.5
        base = y + chart_h - 80
        cv.rect(x, base - bh, bw, bh, ACCENT if i == 3 else TEAL, radius=10)
        df = kit.font(24 if wide else 20, 600)
        text.draw(cv, day, df, x + bw / 2 - text.measure(day, df) / 2, base + 20, muted)
        nf = kit.mono(22 if wide else 18, 600)
        v = f'{h:.1f}'
        text.draw(cv, v, nf, x + bw / 2 - text.measure(v, nf) / 2, base - bh - 32, dark)
    y += chart_h + 50
    cv.rect(m, y, inner, H - y - 50, card, radius=22)
    cv.outline(m, y, inner, H - y - 50, border, width=2, radius=22)
    text.draw(cv, 'Up next', kit.font(34, 750), m + 40, y + 40, dark)
    for i, (t, task) in enumerate((('12:30', 'Lunch with Sam'), ('14:00', 'Deep work: pricing'),
                                   ('15:30', 'Launch checklist'), ('16:30', 'Reply to the beta'),
                                   ('17:30', 'Plan Monday'))):
        ry = y + 120 + i * 112
        if ry + 80 > H - 50:
            break
        cv.outline(m + 40, ry + 22, 30, 30, ACCENT if i % 2 else TEAL, width=4, radius=15)
        text.draw(cv, task, kit.font(30 if wide else 28, 600), m + 100, ry + 18, dark)
        tw = text.measure(t, kit.mono(26, 500))
        text.draw(cv, t, kit.mono(26, 500), W - m - 40 - tw, ry + 20, muted)
        if i:
            cv.rect(m + 40, ry - 4, inner - 80, 2, border)
    return spots[-1][1] + ch + 50   # the chart card's top


@lru_cache(maxsize=2)
def page_image(wide):
    W, H = PAGES[wide]
    cv = vb.Canvas(W, H, scale=PAGE_SCALE)
    chart_y = _draw_page(cv, wide)
    return kit.to_image(cv), chart_y


def camera(cv, s, st):
    cv.fill(BG)
    window = st.content
    img, chart_y = page_image(st.wide)
    W, H = PAGES[st.wide]
    k = PAGE_SCALE
    fit = window.w / W
    # From the top of the page, a glide down that settles in on the week's
    # chart; the push-in only ever crops the page's side margins.
    p = kit.prog(s.f, 4, 58, kit.SMOOTH)
    push = pick(st, 1.14, 1.12)
    zoom = vb.log_lerp(fit, fit * push, p)
    view_h = window.h / zoom
    top = (window.h / fit) / 2
    end = chart_y + pick(st, 300, 280)
    cy = kit.lerp(top, min(end, H - view_h / 2), p)
    v = cv.view(img, window, center=(W / 2 * k, cy * k), scale=zoom / k, radius=16, background=BG)
    v.pin(Box(0, 0, img.w, NAV_H * k), y=window.y)
    cv.outline(*window, LINE, width=2, radius=16)
    cv.mark('screenshot', *window)


# ---- redrawn product UI: the focus settings panel, built from measured blocks ----
TOGGLES = ('Silence notifications', 'Dim other apps', 'Play rain sounds')
EASES = (vb.ease_out_expo, vb.ease_out_quint, vb.ease_out_back, vb.ease_in_out_quart)


def _toggle(cv, x, y, on, scale=1.0):
    w, h = 64 * scale, 36 * scale
    cv.rect(x, y, w, h, kit.mix(LINE, TEAL, on), radius=h / 2)
    k = h - 8 * scale
    cv.rect(x + 4 * scale + (w - k - 8 * scale) * on, y + 4 * scale, k, k, INK, radius=k / 2)


def redrawn(cv, s, st):
    cv.fill(BG)
    c = st.content
    pw = pick(st, 560, 600)
    blocks = pick(st, [84, 66] + [64] * len(TOGGLES) + [72], [92, 76] + [78] * len(TOGGLES) + [84])
    panel_h = sum(blocks) + 16 * (len(blocks) - 1) + 64
    panel = Box(c.cx - pw / 2, c.cy - panel_h / 2, pw, panel_h)
    # A push-in after it's built: vector all the way down, so it stays sharp.
    # It comes to rest with the whole panel just inside the content box, so no
    # label is cropped and the button stays clear of the tag.
    z1 = 0.97 * min(c.w / pw, c.h / panel_h)
    zp = kit.prog(s.f, 30, 56, kit.SMOOTH)
    z = vb.log_lerp(z1 / 1.22, z1, zp)
    fx, fy = panel.cx, panel.cy
    tx, ty = c.cx, c.cy
    with cv.clip(*st.frame), cv.layer(dx=tx - fx * z, dy=ty - fy * z, scale=z):
        cv.shadow(*panel, radius=26, dy=20, blur=50, color=(0, 0, 0, 0.5))
        cv.rect(*panel, CARD, radius=26)
        cv.outline(*panel, LINE, width=2, radius=26)
        boxes, _ = panel.pad(32).stack(blocks, gap=16)
        for i, b in enumerate(boxes):
            p = kit.prog(s.f, -4 + 3 * i, 14 + 3 * i, EASES[i % len(EASES)])   # each block, its own ease
            with cv.layer(opacity=vb.clamp01(p * 1.6), dx=(1 - p) * -90):
                if i == 0:
                    text.draw(cv, 'Focus mode', kit.font(44, 800, tracking=-0.02), b.x, b.y, INK)
                    text.draw(cv, 'Settings › Focus', SMALL, b.x, b.y + 56, MUTED)
                elif i == 1:
                    cv.rect(*b, CARD_HI, radius=16)
                    seg = b.pad(6).row(fr, fr, fr, gap=6)
                    for j, (sb, word) in enumerate(zip(seg, ('25 min', '50 min', '90 min'))):
                        if j == 1:
                            cv.rect(*sb, BG, radius=12)
                        w = text.measure(word, LABEL)
                        text.draw(cv, word, LABEL, sb.cx - w / 2, sb.cy - text.line_height(LABEL) / 2,
                                  INK if j == 1 else MUTED)
                elif i < len(blocks) - 1:
                    word = TOGGLES[i - 2]
                    text.draw(cv, word, LABEL, b.x, b.cy - text.line_height(LABEL) / 2, INK)
                    on = 1.0 if i != 3 else kit.prog(s.f, 22, 32, vb.ease_in_out_quart)
                    _toggle(cv, b.right - 64, b.cy - 18, on)
                    cv.rect(b.x, b.bottom + 7, b.w, 2, LINE)
                else:
                    cv.rect(*b, ACCENT, radius=b.h / 2)
                    w = text.measure('Start focus', kit.font(30, 750))
                    text.draw(cv, 'Start focus', kit.font(30, 750), b.cx - w / 2, b.cy - 20, BG)
    cv.mark('panel', tx + (panel.x - fx) * z, ty + (panel.y - fy) * z, pw * z, panel_h * z)


SCENES = {
    'camera': camera,
    'redrawn': redrawn,
}
