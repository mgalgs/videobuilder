"""The Imagery and camera block (all but the paper collage, in paper.py):
a camera on Lumen's dashboard, the settings panel redrawn as vectors, one
picture treated three ways, a seeded brand pattern, the 3D render, a hard
light sweep, a comic panel and an 8-bit level. Every picture is made here."""
import math
import random
from functools import lru_cache

import cairo
from PIL import Image as PILImage, ImageDraw, ImageEnhance, ImageFilter

import videobuilder as vb
from videobuilder import Box, fr, text

from . import kit
from .kit import ACCENT, BG, CARD, CARD_HI, FPB, FPS, INK, LINE, MUTED, TEAL, pick

LABEL = kit.font(28, 600)
SMALL = kit.font(24, 600)
MONO = kit.mono(24, 500)


def big_head(st, size=None):
    return kit.font(size or pick(st, 64, 60), 800, tracking=-0.025, line_height=1.05)


# ---- Lumen's web dashboard: a page taller than any window, drawn once at 2x ----
PAGE_W, PAGE_H, NAV_H, PAGE_SCALE = 1200, 2000, 110, 2


def _draw_page(cv):
    cv.fill('#f1f2f4')
    dark, muted, card, border = '#1c1e25', '#7b818d', '#ffffff', '#dfe2e7'
    cv.rect(0, 0, PAGE_W, NAV_H, BG)
    kit.logo(cv, 64, NAV_H / 2, 26, -0.6, name=None)
    text.draw(cv, 'Lumen', kit.font(34, 800, tracking=-0.02), 104, NAV_H / 2 - 22, INK)
    for i, word in enumerate(('Today', 'Week', 'Focus', 'Insights')):
        text.draw(cv, word, kit.font(24, 600), 560 + i * 150, NAV_H / 2 - 15, INK if i == 0 else MUTED)
    text.draw(cv, 'Good morning, Alex', kit.font(64, 800, tracking=-0.02), 60, 160, dark)
    text.draw(cv, 'Friday · 5 things planned, 2 hours of focus booked', kit.font(28, 500), 60, 250, muted)
    y = 330
    for i, (lab, val, sub, col) in enumerate((('Focus today', '4h 20m', '+40m on last Friday', TEAL),
                                              ('Tasks done', '12 / 14', '2 left before 6pm', ACCENT),
                                              ('Streak', '9 days', 'Your longest yet', TEAL))):
        x = 60 + i * 370
        cv.rect(x, y, 340, 220, card, radius=22)
        cv.outline(x, y, 340, 220, border, width=2, radius=22)
        text.draw(cv, lab, kit.font(24, 600), x + 30, y + 30, muted)
        text.draw(cv, val, kit.mono(56, 700), x + 30, y + 74, dark)
        text.draw(cv, sub, kit.font(22, 600), x + 30, y + 160, col)
    y = 600
    cv.rect(60, y, 1080, 600, card, radius=22)
    cv.outline(60, y, 1080, 600, border, width=2, radius=22)
    text.draw(cv, 'Focus hours this week', kit.font(34, 750), 100, y + 40, dark)
    hours = (3.5, 4.2, 2.8, 5.1, 4.3, 1.2, 0.6)
    for i, (h, day) in enumerate(zip(hours, ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'))):
        x = 120 + i * 145
        bh = 360 * h / 5.5
        cv.rect(x, y + 520 - bh, 90, bh, ACCENT if i == 3 else TEAL, radius=12)
        text.draw(cv, day, kit.font(24, 600), x + 45 - text.measure(day, kit.font(24, 600)) / 2, y + 540, muted)
        text.draw(cv, f'{h:.1f}', kit.mono(22, 600), x + 22, y + 520 - bh - 34, dark)
    y = 1250
    cv.rect(60, y, 1080, 700, card, radius=22)
    cv.outline(60, y, 1080, 700, border, width=2, radius=22)
    text.draw(cv, 'Up next', kit.font(34, 750), 100, y + 40, dark)
    for i, (t, task) in enumerate((('12:30', 'Lunch with Sam'), ('14:00', 'Deep work: pricing'),
                                   ('15:30', 'Launch checklist'), ('16:30', 'Reply to the beta group'),
                                   ('17:30', 'Plan Monday'))):
        ry = y + 120 + i * 112
        cv.outline(100, ry + 22, 30, 30, ACCENT if i % 2 else TEAL, width=4, radius=15)
        text.draw(cv, task, kit.font(30, 600), 160, ry + 18, dark)
        text.draw(cv, t, kit.mono(26, 500), 1000, ry + 20, muted)
        if i:
            cv.rect(100, ry - 4, 1000, 2, border)


@lru_cache(maxsize=1)
def page_image():
    cv = vb.Canvas(PAGE_W, PAGE_H, scale=PAGE_SCALE)
    _draw_page(cv)
    return kit.to_image(cv)


def camera(cv, s, st):
    cv.fill(BG)
    c = st.content
    img = page_image()
    k = PAGE_SCALE
    window = c
    fit = window.w / PAGE_W
    p = kit.prog(s.f, 6, 50, kit.SMOOTH)
    # Wide on the whole page, then down and in on the week's chart.
    cy = kit.lerp(pick(st, 420, 900), pick(st, 880, 900), p)
    cx = kit.lerp(PAGE_W / 2, pick(st, 600, 520), p)
    zoom = vb.log_lerp(fit, fit * pick(st, 1.3, 1.6), p)
    v = cv.view(img, window, center=(cx * k, cy * k), scale=zoom / k, radius=16, background=BG)
    v.pin(Box(0, 0, img.w, NAV_H * k), y=window.y)
    cv.outline(*window, LINE, width=2, radius=16)
    cv.mark('screenshot', *window)


# ---- redrawn product UI: the focus settings panel, built from measured blocks ----
TOGGLES = ('Silence notifications', 'Dim other apps', 'Play rain sounds')


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
    zp = kit.prog(s.f, 30, 56, kit.SMOOTH)
    z = vb.log_lerp(1.0, pick(st, 1.6, 1.45), zp)
    fx, fy = panel.x + pw * 0.62, panel.y + panel_h * 0.45
    tx, ty = kit.lerp(fx, c.cx, zp), kit.lerp(fy, c.cy, zp)
    with cv.clip(*st.frame), cv.layer(dx=tx - fx * z, dy=ty - fy * z, scale=z):
        cv.shadow(*panel, radius=26, dy=20, blur=50, color=(0, 0, 0, 0.5))
        cv.rect(*panel, CARD, radius=26)
        cv.outline(*panel, LINE, width=2, radius=26)
        boxes, _ = panel.pad(32).stack(blocks, gap=16)
        for i, b in enumerate(boxes):
            p = kit.spring(s.f, -3 + 3 * i, kit.BOUNCY)
            with cv.layer(opacity=vb.clamp01(p), dy=(1 - p) * 30):
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
                    on = 1.0 if i != 3 else vb.clamp01(kit.spring(s.f, 22, kit.BOUNCY))
                    _toggle(cv, b.right - 64, b.cy - 18, on)
                    cv.rect(b.x, b.bottom + 7, b.w, 2, LINE)
                else:
                    cv.rect(*b, ACCENT, radius=b.h / 2)
                    w = text.measure('Start focus', kit.font(30, 750))
                    text.draw(cv, 'Start focus', kit.font(30, 750), b.cx - w / 2, b.cy - 20, BG)
    cv.mark('panel', *(panel if zp == 0 else c))


# ---- image treatments: one generated picture, three ways ----
def _landscape(w=1600, h=1000, seed=7):
    rnd = random.Random(seed)
    im = PILImage.new('RGB', (w, h))
    d = ImageDraw.Draw(im)
    top, bottom = (31, 40, 70), (239, 130, 96)
    for y in range(h):
        t = y / (h - 1)
        d.line([(0, y), (w, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    sun = PILImage.new('L', (w, h), 0)
    ImageDraw.Draw(sun).ellipse((w * 0.58, h * 0.28, w * 0.58 + 230, h * 0.28 + 230), fill=255)
    im.paste((255, 214, 160), mask=sun.filter(ImageFilter.GaussianBlur(4)))
    for i, colour in enumerate([(84, 92, 128), (52, 66, 98), (33, 46, 70), (20, 26, 40)]):
        base = h * (0.55 + 0.11 * i)
        pts, x = [(0, h)], 0
        while x <= w:
            pts.append((x, base - rnd.uniform(0, 140 - 25 * i)))
            x += rnd.randint(60, 160)
        pts += [(w, base - 40), (w, h)]
        d.polygon(pts, fill=colour)
    return im


PICTURE = vb.Image.from_pil(_landscape())


def treatments(cv, s, st):
    cv.fill(BG)
    c = st.content
    if st.wide:
        cells = Box(c.x, c.y + 20, c.w, c.h - 70).row(fr, fr, fr, gap=48)
        cards = [cell.contain(1, 1, at='top') for cell in cells]
    else:
        cells = Box(c.x, c.y, c.w, c.h).column(fr, fr, fr, gap=40)
        cards = [Box(cell.x + 60, cell.y, cell.w - 120, cell.h - 56) for cell in cells]
    words = ('cover', 'contain', 'rounded + shadow')
    for i, (card, word) in enumerate(zip(cards, words)):
        p = kit.spring(s.f, -3 + 5 * i, kit.BOUNCY)
        sc = 0.85 + 0.15 * min(1.05, p)
        with cv.layer(opacity=vb.clamp01(p)), kit.scaled(cv, card.cx, card.cy, sc):
            if i == 0:   # cover: fills the card, cropped, with a slow push
                zoom = vb.log_lerp(1.0, 1.15, s.f / s.length)
                with cv.clip(*card):
                    cv.image(PICTURE, *card.cover(PICTURE.w, PICTURE.h).scaled(zoom))
            elif i == 1:  # contain: the whole picture, letterboxed
                cv.rect(*card, CARD)
                cv.image(PICTURE, *card.contain(PICTURE.w, PICTURE.h))
            else:         # a rounded clip, lifted with a soft shadow
                cv.shadow(*card, radius=28, dy=22, blur=44, color=(0, 0, 0, 0.6))
                with cv.clip(*card, radius=28):
                    cv.image(PICTURE, *card.cover(PICTURE.w, PICTURE.h))
        cv.mark(f'card-{i}', *card)
        w = text.measure(word, MONO)
        text.draw(cv, word, MONO, card.cx - w / 2, card.bottom + 16, INK)
        cv.mark(f'label-{i}', card.cx - w / 2, card.bottom + 16, w, text.line_height(MONO))


# ---- generated art: Lumen's brand pattern, seeded ----
ART_PERIOD = 45  # frames; the pattern turns a whole cycle across the shot
_rnd = random.Random(7)
FIELD = [dict(u=_rnd.random(), v=_rnd.random(), r=_rnd.uniform(30, 150), a0=_rnd.uniform(0, 2 * math.pi),
              span=_rnd.uniform(0.9, 2.8), speed=_rnd.choice((-1, 1)) * _rnd.uniform(0.15, 0.4),
              width=_rnd.uniform(3, 9), teal=_rnd.random() < 0.4, alpha=_rnd.uniform(0.35, 0.8)) for _ in range(90)]


def generated(cv, s, st):
    frame = st.frame
    ctx = cv.ctx
    g = cairo.LinearGradient(0, 0, frame.w, frame.h)
    g.add_color_stop_rgb(0, *vb.rgba('#1a1420')[:3])
    g.add_color_stop_rgb(1, *vb.rgba('#0f1b1d')[:3])
    ctx.set_source(g)
    ctx.paint()
    phase = s.f / ART_PERIOD
    grow = kit.prog(s.f, -4, 20)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for f in FIELD:
        cx, cy = frame.x + f['u'] * frame.w, frame.y + f['v'] * frame.h
        ang = f['a0'] + f['speed'] * 2 * math.pi * phase
        ctx.new_path()
        ctx.arc(cx, cy, f['r'], ang, ang + f['span'] * grow)
        ctx.set_line_width(f['width'])
        if f['teal']:
            x0, y0 = cx + f['r'] * math.cos(ang), cy + f['r'] * math.sin(ang)
            x1, y1 = cx + f['r'] * math.cos(ang + f['span']), cy + f['r'] * math.sin(ang + f['span'])
            lg = cairo.LinearGradient(x0, y0, x1, y1)
            lg.add_color_stop_rgba(0, *vb.rgba(TEAL)[:3], f['alpha'])
            lg.add_color_stop_rgba(1, *vb.rgba(ACCENT)[:3], f['alpha'])
            ctx.set_source(lg)
        else:
            ctx.set_source_rgba(*vb.rgba(ACCENT)[:3], f['alpha'])
        ctx.stroke()
    # The wordmark on a dark plate in the middle.
    word_f = kit.font(pick(st, 96, 88), 850, tracking=-0.03)
    ww = text.measure('Lumen', word_f)
    lh = text.line_height(word_f)
    r = lh * 0.38
    pw, ph = ww + 2 * r + 30 + 96, lh + 70
    plate = Box(st.content.cx - pw / 2, st.content.cy - ph / 2, pw, ph)
    cv.shadow(*plate, radius=ph / 2, dy=16, blur=40, color=(0, 0, 0, 0.5))
    cv.rect(*plate, (20, 21, 26, 0.92), radius=ph / 2)
    kit.logo(cv, plate.x + 48 + r, plate.cy, r, -0.6, name=None)
    text.draw(cv, 'Lumen', word_f, plate.x + 48 + 2 * r + 30, plate.cy - lh / 2, INK)
    cv.mark('wordmark', *plate)


# ---- 3D shots: the pre-rendered orbit, composited like a picture ----
ORBIT = vb.Clip(str(kit.ASSETS / 'orbit.mp4'))
ORBIT_PERIOD = 30


def orbit(cv, s, st):
    cv.fill(BG)
    c = st.content
    if st.wide:
        card = Box(c.x + 60, c.y + 10, 440, c.h - 20)
        tx, ty, tw = card.right + 80, None, c.right - card.right - 80
    else:
        card = Box(c.x + 40, c.y, c.w - 80, 620)
        tx, ty, tw = c.x, card.bottom + 50, c.w
    p = kit.spring(s.f, -4, kit.BOUNCY)
    kit.glow(cv, card.cx, card.cy, card.h * 0.75, TEAL, 0.18)
    with kit.scaled(cv, card.cx, card.cy, 0.92 + 0.08 * min(1.05, p)):
        cv.shadow(*card, radius=30, dy=24, blur=50, color=(0, 0, 0, 0.55))
        with cv.clip(*card, radius=30):
            pic = ORBIT.frame((s.f + 8) % ORBIT_PERIOD)
            cv.image(pic, *card.cover(*ORBIT.size))
        cv.outline(*card, (255, 255, 255, 0.12), width=2, radius=30)
    cv.mark('render', *card)
    head = big_head(st)
    lines, (w, h) = kit.lines_of('Lumen, in 3D.', head, tw)
    sub = 'A pre-rendered clip, placed like any picture.'
    sl, (sw, sh) = kit.lines_of(sub, LABEL, tw)
    if ty is None:
        ty = c.cy - (h + 20 + sh) / 2
    align = 'left' if st.wide else 'center'
    a = kit.prog(s.f, -2, 12)
    with cv.layer(opacity=a):
        text.draw(cv, lines, head, tx, ty, INK, align=align, width=None if st.wide else tw)
        text.draw(cv, sl, LABEL, tx, ty + h + 20, MUTED, align=align, width=None if st.wide else tw)
    cv.mark('copy', tx, ty, w if st.wide else tw, h + 20 + sh)


# ---- hard-light sweep: a beam of window light crosses Lumen on a desk ----
def _desk(w, h):
    cv = vb.Canvas(w, h)
    ctx = cv.ctx
    g = cairo.LinearGradient(0, 0, 0, h)
    g.add_color_stop_rgb(0, *vb.rgba('#8c7a68')[:3])
    g.add_color_stop_rgb(1, *vb.rgba('#5e5145')[:3])
    ctx.set_source(g)
    ctx.paint()
    # A notebook, a mug, and the phone with Lumen open.
    nb = Box(w * 0.08, h * 0.2, w * 0.3, h * 0.6) if w > h else Box(w * 0.06, h * 0.06, w * 0.5, h * 0.28)
    cv.shadow(*nb, radius=6, dy=10, blur=24, color=(0, 0, 0, 0.35))
    cv.rect(*nb, '#e9e2d6', radius=6)
    for i in range(1, 9):
        cv.rect(nb.x + 20, nb.y + i * nb.h / 9, nb.w - 40, 2, '#c9bfae')
    mx, my, mr = (w * 0.84, h * 0.3, h * 0.11) if w > h else (w * 0.8, h * 0.82, w * 0.12)
    cv.shadow(mx - mr, my - mr, 2 * mr, 2 * mr, radius=mr, dy=10, blur=24, color=(0, 0, 0, 0.35))
    cv.rect(mx - mr, my - mr, 2 * mr, 2 * mr, '#e4e0d9', radius=mr)
    cv.rect(mx - mr * 0.75, my - mr * 0.75, 1.5 * mr, 1.5 * mr, '#5a3a28', radius=mr * 0.75)
    ph = Box(w * 0.5 - h * 0.21, h * 0.08, h * 0.42, h * 0.84) if w > h else Box(w * 0.2, h * 0.24, w * 0.6, h * 0.66)
    cv.shadow(*ph, radius=34, dx=6, dy=16, blur=30, color=(0, 0, 0, 0.45))
    cv.rect(*ph, '#16171c', radius=34)
    scr = ph.pad(12)
    cv.rect(*scr, '#f1f2f4', radius=24)
    kit.logo(cv, scr.x + 46, scr.y + 52, 22, -0.6, name=None)
    text.draw(cv, 'Today', kit.font(30, 800), scr.x + 80, scr.y + 34, '#1c1e25')
    for i in range(5):
        y = scr.y + 110 + i * (scr.h - 140) / 5
        cv.rect(scr.x + 20, y, scr.w - 40, (scr.h - 140) / 5 - 12, '#ffffff', radius=10)
        cv.outline(scr.x + 34, y + 16, 18, 18, ACCENT if i % 2 else TEAL, width=3, radius=9)
        cv.rect(scr.x + 64, y + 20, (scr.w - 120) * (0.8 - 0.1 * (i % 3)), 10, '#c3c7cf', radius=5)
    return kit.to_pil(cv).convert('RGB')


def _tinted(img, colour, amount):
    return PILImage.blend(img, PILImage.new('RGB', img.size, colour), amount)


@lru_cache(maxsize=2)
def desk_images(w, h):
    base = _desk(w, h)
    dim = _tinted(ImageEnhance.Brightness(ImageEnhance.Color(base).enhance(0.55)).enhance(0.5), (10, 14, 30), 0.35)
    lit = _tinted(ImageEnhance.Brightness(ImageEnhance.Contrast(base).enhance(1.08)).enhance(1.25), (255, 196, 120), 0.2)
    return vb.Image.from_pil(dim), vb.Image.from_pil(lit)


def _beam(ctx, x, w, h, skew, bars=3, bar_w=18):
    gap = (w - bars * bar_w) / (bars + 1)
    ctx.new_path()
    for x0, x1 in [(x, x + w)] + [(x + gap * (i + 1) + bar_w * i, x + gap * (i + 1) + bar_w * (i + 1)) for i in range(bars)]:
        ctx.move_to(x0, 0)
        ctx.line_to(x1, 0)
        ctx.line_to(x1 + skew, h)
        ctx.line_to(x0 + skew, h)
        ctx.close_path()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.clip()


def hard_light(cv, s, st):
    cv.fill(BG)
    box = st.content
    dim, lit = desk_images(round(box.w), round(box.h))
    band, skew = pick(st, 380, 300), pick(st, 260, 380)
    with cv.clip(*box, radius=18):
        cv.image(dim, *box)
        p = vb.clamp01((s.f + 12) / (s.length + 18))  # crosses the middle mid-shot
        bx = box.x - band - skew + p * (box.w + band + skew)
        ctx = cv.ctx
        ctx.save()
        ctx.translate(0, box.y)
        _beam(ctx, bx, band, box.h, skew)
        ctx.translate(0, -box.y)
        cv.image(lit, *box)
        ctx.restore()
    cv.mark('scene', *box)


# ---- comic-book halftone: launch day, as a panel ----
PAPER, CINK, RED, BLUE, YELLOW = '#f4ecd8', '#15120f', '#c81e3a', '#2e6f9e', '#f0a202'
COMIC_PERIOD = 45


def comic(cv, s, st):
    cv.fill(PAPER)
    c = st.content
    ctx = cv.ctx
    panel = c.pad(6)
    cv.outline(*panel, CINK, width=8)
    # The caption box, top left.
    cap_f = kit.font(pick(st, 28, 30), 850, tracking=0.02)
    cap = 'MEANWHILE, AT LUMEN HQ...'
    cw = text.measure(cap, cap_f)
    cb = Box(panel.x + 4, panel.y + 4, cw + 40, text.line_height(cap_f) + 24)
    cv.rect(*cb, YELLOW)
    cv.outline(*cb, CINK, width=5)
    text.draw(cv, cap, cap_f, cb.x + 20, cb.y + 12, CINK)
    cv.mark('caption', *cb)
    # The Lumen orb as a comic ball: flat sun, halftone shadow, thick ink.
    r = pick(st, 175, 190)
    bx, by = (panel.x + panel.w * 0.32, panel.cy + 40) if st.wide else (panel.cx - 30, panel.y + panel.h * 0.7)
    for radius, colour in ((r, BLUE), (r * 0.62, YELLOW)):
        ctx.save()
        ctx.new_path()
        ctx.arc(bx, by, radius, 0, 2 * math.pi)
        ctx.clip()
        cv.rect(bx - radius, by - radius, 2 * radius, 2 * radius, colour)
        ctx.new_path()
        ctx.rectangle(bx, by - radius, radius, 2 * radius)
        ctx.clip()
        ctx.translate(3, -3)  # the dot plate, off register
        ctx.set_source(vb.halftone_pattern(13, 4.4, angle=0.5, color=CINK if colour == BLUE else RED))
        ctx.paint_with_alpha(0.55)
        ctx.restore()
        cv.arc(bx, by, radius - 4, 0, 2 * math.pi, CINK, width=9)
    cv.mark('ball', bx - r, by - r, 2 * r, 2 * r)
    # The burst, wobbling on harmonics of the shot, punched in on the cut.
    q = s.f / COMIC_PERIOD
    rot = math.radians(7) * math.sin(2 * math.pi * 3 * q) + math.radians(3) * math.sin(2 * math.pi * 7 * q + 1.3)
    wob = 1 + 0.06 * math.sin(2 * math.pi * 5 * q + 0.4)
    pop = min(1.15, kit.spring(s.f, -3, vb.damped(0.4, hz=3)))
    ro = pick(st, 215, 175)
    sx, sy = (panel.x + panel.w * 0.72, panel.cy - 10) if st.wide else (panel.cx + 70, panel.y + panel.h * 0.26)
    sc = max(0.01, wob * pop)
    with kit.scaled(cv, sx, sy, sc):
        ctx.save()
        ctx.translate(sx, sy)
        ctx.rotate(rot)
        pts = []
        for i in range(26):
            rr = ro if i % 2 == 0 else ro * 0.58
            a = math.pi * i / 13 - math.pi / 2
            pts.append((rr * math.cos(a), rr * math.sin(a)))
        kit.poly(ctx, pts)
        ctx.set_source_rgba(*vb.rgba(RED))
        ctx.fill_preserve()
        ctx.set_source_rgba(*vb.rgba(CINK))
        ctx.set_line_width(8)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
        ctx.restore()
        bf = kit.font(pick(st, 56, 50), 900, tracking=0.01)
        w = text.measure('LAUNCH!', bf)
        text.draw(cv, 'LAUNCH!', bf, sx - w / 2, sy - text.line_height(bf) / 2, PAPER)
    cv.mark('burst', sx - ro, sy - ro, 2 * ro, 2 * ro)


# ---- pixel-art layer: an 8-bit Lumi collects the day's tasks ----
SKY, GROUND, SUN, PIX_INK = '#8fd3f4', '#3a7d44', '#f4d35e', '#1d1f28'
PIXEL = 8


def pixel(cv, s, st):
    cv.fill(BG)
    box = st.content
    n = s.f - s.f % 2  # held on twos
    w, h = box.w, box.h
    with cv.pixelated(PIXEL, x=box.x, y=box.y, w=w, h=h) as px:
        px.fill(SKY)
        gh = h * 0.24
        px.rect(0, h - gh, w, gh, GROUND)
        for i in range(0, int(w), 64):
            px.rect(i, h - gh, 32, 16, '#2f6a38')
        px.rect(w - 180, 60, 96, 96, SUN, radius=48)
        for cx, cy in ((w * 0.2, h * 0.2), (w * 0.55, h * 0.12)):
            px.rect(cx, cy, 160, 40, '#ffffff', radius=20)
            px.rect(cx + 40, cy - 24, 80, 40, '#ffffff', radius=20)
        floor = h - gh
        x = kit.lerp(w * 0.08, w * 0.78, n / s.length)
        coins = (0.3, 0.5, 0.7)
        got = sum(1 for k in coins if x > w * k)
        for i, k in enumerate(coins):
            cx = w * k
            if x <= cx:   # a task, still to collect: a checkbox floating above the ground
                bob = 6 * math.sin(n / 6 + i)
                px.rect(cx - 36, floor - 230 + bob, 72, 72, '#ffffff', radius=6)
                px.outline(cx - 36, floor - 230 + bob, 72, 72, PIX_INK, width=10, radius=6)
            elif x - cx < 90:  # just collected: +1 floats up
                text.draw(px, '+1', kit.font(80, 800), cx - 40, floor - 300 - (x - cx), PIX_INK)
        swing = math.sin(n / 3)
        bw, bh = 140, 124
        by = floor - bh - 50 - abs(swing) * 10
        px.rect(x - bw / 2, by, bw, bh, ACCENT, radius=44)
        for ex in (-26, 26):
            px.rect(x + ex - 10 + 12, by + 32, 20, 32, PIX_INK)
        px.rect(x - 48 + swing * 16, floor - 52, 32, 52, PIX_INK)
        px.rect(x + 16 - swing * 16, floor - 52, 32, 52, PIX_INK)
        hud = kit.font(80, 800)
        text.draw(px, f'TASKS {got}/3', hud, 40, 30, PIX_INK)
    cv.outline(*box, LINE, width=2)
    cv.mark('scene', *box)


SCENES = {
    'camera-on-a-screenshot': camera,
    'redrawn-product-ui': redrawn,
    'image-treatments': treatments,
    'generated-art': generated,
    'orbit-3d': orbit,
    'hard-light-sweep': hard_light,
    'comic-halftone': comic,
    'pixel-art-layer': pixel,
}
