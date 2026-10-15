"""The looks that get room to breathe: generated art in three seeded
patterns, the 3D render in three framings, and hard window light raking
across Lumen on a desk at dusk. Every picture is made here."""
import math
import random
from functools import lru_cache

import cairo
from PIL import Image as PILImage, ImageChops, ImageEnhance

import videobuilder as vb
from videobuilder import Box, text

from . import kit
from .kit import ACCENT, BG, FPB, INK, MUTED, TEAL, pick

LABEL = kit.font(28, 600)
CHIP_F = kit.mono(24, 600)


def chip(cv, st, words, name='chip', dark=True):
    """A small mono label, top left of the safe area: which variant this cut is."""
    w = text.measure(words, CHIP_F) + 36
    h = text.line_height(CHIP_F) + 18
    x, y = st.safe.x, st.safe.y
    cv.rect(x, y, w, h, (14, 15, 19, 0.82) if dark else (255, 255, 255, 0.85), radius=h / 2)
    text.draw(cv, words, CHIP_F, x + 18, y + 9, INK if dark else '#1c1e25')
    cv.mark(name, x, y, w, h)


def wordmark_plate(cv, cx, cy, size):
    """Lumen's logo and wordmark on a dark pill."""
    word_f = kit.font(size, 850, tracking=-0.03)
    ww = text.measure('Lumen', word_f)
    lh = text.line_height(word_f)
    r = lh * 0.38
    pw, ph = ww + 2 * r + 30 + 96, lh + 70
    plate = Box(cx - pw / 2, cy - ph / 2, pw, ph)
    cv.shadow(*plate, radius=ph / 2, dy=16, blur=40, color=(0, 0, 0, 0.5))
    cv.rect(*plate, (20, 21, 26, 0.92), radius=ph / 2)
    kit.logo(cv, plate.x + 48 + r, plate.cy, r, -0.6, name=None)
    text.draw(cv, 'Lumen', word_f, plate.x + 48 + 2 * r + 30, plate.cy - lh / 2, INK)
    cv.mark('wordmark', *plate)


# ---- generated art: three seeded patterns, a cut on each ----
def _arc_field(seed):
    rnd = random.Random(seed)
    return [dict(u=rnd.random(), v=rnd.random(), r=rnd.uniform(30, 150), a0=rnd.uniform(0, 2 * math.pi),
                 span=rnd.uniform(0.9, 2.8), speed=rnd.choice((-1, 1)) * rnd.uniform(0.15, 0.4),
                 width=rnd.uniform(3, 9), teal=rnd.random() < 0.4, alpha=rnd.uniform(0.35, 0.8)) for _ in range(90)]


ARCS = _arc_field(7)


def _ground(cv, frame, a, b):
    g = cairo.LinearGradient(0, 0, frame.w, frame.h)
    g.add_color_stop_rgb(0, *vb.rgba(a)[:3])
    g.add_color_stop_rgb(1, *vb.rgba(b)[:3])
    cv.ctx.set_source(g)
    cv.ctx.paint()


def gen_arcs(cv, s, st):
    frame = st.frame
    ctx = cv.ctx
    _ground(cv, frame, '#1a1420', '#0f1b1d')
    phase = s.f / 45
    grow = kit.prog(s.f, -4, 20)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for f in ARCS:
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
    wordmark_plate(cv, st.content.cx, st.content.cy, pick(st, 96, 88))
    chip(cv, st, 'arcs · seed 7')


_rf = random.Random(21)
FLOW = [(_rf.random(), _rf.random(), _rf.random()) for _ in range(340)]


def _flow_angle(x, y, t):
    return (math.sin(x * 0.0042 + 1.6 * math.sin(y * 0.0031 + t)) + math.cos(y * 0.0047 - 0.8 * t + x * 0.001)) * 1.9


def gen_flow(cv, s, st):
    frame = st.frame
    ctx = cv.ctx
    _ground(cv, frame, '#0e1216', '#17121a')
    t = s.f / 30 * 0.7
    steps = int(4 + 30 * kit.prog(s.f, -6, 18))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for u, v, k in FLOW:
        x, y = frame.x + u * frame.w, frame.y + v * frame.h
        ctx.new_path()
        ctx.move_to(x, y)
        for _ in range(steps):
            a = _flow_angle(x, y, t)
            x += 9 * math.cos(a)
            y += 9 * math.sin(a)
            ctx.line_to(x, y)
        col = kit.mix(TEAL, ACCENT, (u + 0.6 * v) / 1.6)
        ctx.set_source_rgba(col[0] / 255, col[1] / 255, col[2] / 255, 0.35 + 0.5 * k)
        ctx.set_line_width(1.5 + 3 * k)
        ctx.stroke()
    chip(cv, st, 'flow field · seed 21')
    cv.mark('field', *st.content.pad(60))


TRUCHET_CELL = 96


@lru_cache(maxsize=2)
def _truchet(wide):
    w, h = (1280, 720) if wide else (720, 1280)
    rnd = random.Random(64)
    cols, rows = math.ceil(w / TRUCHET_CELL) + 1, math.ceil(h / TRUCHET_CELL) + 1
    cells = []
    for j in range(rows):
        for i in range(cols):
            flips = tuple(b for b in range(1, 6) if rnd.random() < 0.3)   # beats this cell turns on
            cells.append((i, j, rnd.random() < 0.5, rnd.random() < 0.22, flips))
    return cells


def gen_tiles(cv, s, st):
    cv.fill('#121318')
    ctx = cv.ctx
    c = TRUCHET_CELL
    ox = (st.frame.w - math.ceil(st.frame.w / c) * c) / 2
    oy = (st.frame.h - math.ceil(st.frame.h / c) * c) / 2
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    grow = kit.prog(s.f, -6, 10)
    for i, j, o, teal, flips in _truchet(st.wide):
        turns = 0.0
        for b in flips:   # a quarter turn on each of its beats, sprung
            turns += max(0.0, min(1.1, kit.spring(s.f, b * FPB - 3, vb.damped(0.5, hz=3))))
        cx, cy = ox + i * c + c / 2, oy + j * c + c / 2
        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate((o + turns) * math.pi / 2)
        ctx.set_line_width(c * 0.17)
        col = vb.rgba(TEAL if teal else ACCENT)
        ctx.set_source_rgba(col[0], col[1], col[2], 0.9)
        for (ax, ay, a0) in ((-c / 2, -c / 2, 0), (c / 2, c / 2, math.pi)):
            ctx.new_path()
            ctx.arc(ax, ay, c / 2, a0, a0 + math.pi / 2 * grow)
            ctx.stroke()
        ctx.restore()
    chip(cv, st, 'tiles · seed 64')
    cv.mark('tiles', *st.content.pad(60))


# ---- 3D shots: the pre-rendered orbit clip in three framings ----
ORBIT = vb.Clip(str(kit.ASSETS / 'orbit.mp4'))
ORBIT_BG = (11, 16, 32)
CROP = (60, 340, 600, 600)   # the ring and sun, inside the 720x1280 clip


@lru_cache(maxsize=8)
def keyed(i):
    """Clip frame `i`, cropped to the object and with its flat navy backdrop
    keyed out, so the render can sit in front of type or on any ground."""
    pil = ORBIT.frame(i % ORBIT.frames)._pil.convert('RGB')
    x, y, w, h = CROP
    rgb = pil.crop((x, y, x + w, y + h))
    r, g, b = ImageChops.difference(rgb, PILImage.new('RGB', rgb.size, ORBIT_BG)).split()
    d = ImageChops.lighter(ImageChops.lighter(r, g), b)
    rgb.putalpha(d.point(lambda v: int(min(max((v - 8) / 20, 0), 1) * 255)))
    return vb.Image.from_pil(rgb)


def _navy(cv, frame, cx, cy, r):
    ctx = cv.ctx
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    g.add_color_stop_rgb(0, *vb.rgba('#1a2547')[:3])
    g.add_color_stop_rgb(1, *vb.rgba('#0b1020')[:3])
    ctx.set_source(g)
    ctx.paint()


def orbit_type(cv, s, st):
    """Behind type: the render turns in front of the wordmark."""
    c = st.content
    _navy(cv, st.frame, c.cx, c.cy, max(st.frame.w, st.frame.h) * 0.7)
    f = kit.font(pick(st, 300, 250), 900, tracking=-0.04, line_height=pick(st, 1.0, 1.5))
    lines = ['LUMEN'] if st.wide else ['LUM', 'EN']   # stacked in 9:16, the render between the lines
    w, h = text.block_size(lines, f)
    p = kit.prog(s.f, -3, 12)
    with cv.layer(opacity=p, dy=(1 - p) * 30):
        text.draw(cv, lines, f, c.cx - w / 2, c.cy - h / 2, INK, align='center', width=w)
    cv.mark('type', c.cx - w / 2, c.cy - h / 2, w, h)
    d = pick(st, 560, 600)
    q = kit.spring(s.f, 2, kit.BOUNCY)
    with kit.scaled(cv, c.cx, c.cy, 0.7 + 0.3 * min(1.04, q)):
        cv.image(keyed(s.f + 8), c.cx - d / 2, c.cy - d / 2, d, d)
    chip(cv, st, 'behind type')


def _phone(cv, box, draw_screen):
    cv.shadow(*box, radius=box.w * 0.14, dy=24, blur=50, color=(0, 0, 0, 0.6))
    cv.rect(*box, '#08090c', radius=box.w * 0.14)
    cv.outline(*box, (255, 255, 255, 0.14), width=2, radius=box.w * 0.14)
    scr = box.pad(box.w * 0.045)
    with cv.clip(*scr, radius=box.w * 0.1):
        draw_screen(scr)
    cv.rect(box.cx - box.w * 0.15, scr.y + 10, box.w * 0.3, 18, '#08090c', radius=9)


def orbit_device(cv, s, st):
    """In a device: the clip as a phone's screen, uncropped and unkeyed."""
    cv.fill(BG)
    c = st.content
    kit.glow(cv, c.cx, c.cy, pick(st, 520, 600), TEAL, 0.16)
    ph = pick(st, c.h, c.h * 0.82)
    pw = ph * 9 / 19
    px = pick(st, c.x + c.w * 0.3 - pw / 2, c.cx - pw / 2)
    py = pick(st, c.y, c.bottom - ph)
    rise = kit.spring(s.f, -3, vb.damped(0.7, hz=2))
    box = Box(px, py + (1 - rise) * 120, pw, ph)

    def screen(scr):
        pic = ORBIT.frame((s.f + 20) % ORBIT.frames)
        cv.image(pic, *scr.cover(*ORBIT.size))
        hf = kit.font(scr.w * 0.1, 800, tracking=-0.02)
        text.draw(cv, 'Lumen', hf, scr.x + scr.w * 0.1, scr.y + scr.h * 0.1, INK)
        text.draw(cv, 'Your day, in orbit.', kit.font(scr.w * 0.06, 600), scr.x + scr.w * 0.1,
                  scr.y + scr.h * 0.1 + text.line_height(hf) + 4, MUTED)

    _phone(cv, box, screen)
    cv.mark('phone', *box)
    head = kit.font(pick(st, 64, 52), 800, tracking=-0.025, line_height=1.05)
    copy = 'Placed like any picture.'
    if st.wide:
        tx, tw = c.x + c.w * 0.56, c.w * 0.44
    else:
        tx, tw = c.x, c.w
    lines, (w, h) = kit.lines_of(copy, head, tw)
    ty = pick(st, c.cy - h / 2, c.y + 70)
    a = kit.prog(s.f, 2, 16)
    with cv.layer(opacity=a, dx=(1 - a) * 30):
        text.draw(cv, lines, head, tx, ty, INK, align='left' if st.wide else 'center', width=None if st.wide else tw)
    cv.mark('copy', tx, ty, w if st.wide else tw, h)
    chip(cv, st, 'in a device')


def orbit_bleed(cv, s, st):
    """Full bleed: the render fills the frame, the camera drifting in."""
    frame = st.frame
    cx, cy = pick(st, (frame.w * 0.6, frame.h * 0.5), (frame.w * 0.5, frame.h * 0.42))
    _navy(cv, frame, cx, cy, max(frame.w, frame.h) * 0.8)
    push = vb.log_lerp(1.0, 1.1, s.f / s.length)
    d = pick(st, 1050, 1000) * push
    cv.image(keyed(s.f + 30), cx - d / 2, cy - d / 2, d, d)
    c = st.content
    head = kit.font(pick(st, 72, 64), 850, tracking=-0.03)
    word = 'Lumen, in 3D.'
    w, h = text.measure(word, head), text.line_height(head)
    x, y = pick(st, (c.x, c.bottom - h), (c.cx - w / 2, c.bottom - h))
    a = kit.prog(s.f, 0, 14)
    with cv.layer(opacity=a, dy=(1 - a) * 20):
        text.draw(cv, word, head, x, y, INK)
    cv.mark('headline', x, y, w, h)
    chip(cv, st, 'full bleed')


# ---- hard-light sweep: window light rakes across Lumen on a desk at dusk ----
DESK_ZOOM = 2   # the desk is drawn at 2x, so the close-up stays sharp


def _desk(w, h, wide):
    """The desk from above, at film size w x h (drawn at DESK_ZOOM); returns the
    PIL image and the phone's box in film px."""
    k = DESK_ZOOM
    cv = vb.Canvas(w, h, scale=k)
    ctx = cv.ctx
    g = cairo.LinearGradient(0, 0, w, h)
    g.add_color_stop_rgb(0, *vb.rgba('#9a7656')[:3])
    g.add_color_stop_rgb(1, *vb.rgba('#6e523b')[:3])
    ctx.set_source(g)
    ctx.paint()
    rnd = random.Random(3)
    for i in range(70):   # wood grain
        y = rnd.uniform(-40, h + 40) if wide else None
        x = rnd.uniform(-40, w + 40) if not wide else None
        ctx.new_path()
        if wide:
            ctx.move_to(0, y)
            ctx.curve_to(w * 0.3, y + rnd.uniform(-14, 14), w * 0.7, y + rnd.uniform(-14, 14), w, y + rnd.uniform(-8, 8))
        else:
            ctx.move_to(x, 0)
            ctx.curve_to(x + rnd.uniform(-14, 14), h * 0.3, x + rnd.uniform(-14, 14), h * 0.7, x + rnd.uniform(-8, 8), h)
        ctx.set_source_rgba(0.25, 0.15, 0.08, rnd.uniform(0.05, 0.16))
        ctx.set_line_width(rnd.uniform(1, 4))
        ctx.stroke()
    if wide:
        nb = Box(w * 0.07, h * 0.18, w * 0.25, h * 0.62)
        mug = (w * 0.86, h * 0.26, h * 0.1)
        phone = Box(w * 0.5 - h * 0.2, h * 0.1, h * 0.4, h * 0.8)
        plant = (w * 0.84, h * 0.76, h * 0.12)
    else:
        nb = Box(w * 0.06, h * 0.04, w * 0.52, h * 0.24)
        mug = (w * 0.82, h * 0.14, w * 0.11)
        phone = Box(w * 0.18, h * 0.32, w * 0.64, h * 0.58)
        plant = (w * 0.86, h * 0.93, w * 0.13)
    cv.shadow(*nb, radius=6, dx=6, dy=10, blur=22, color=(0, 0, 0, 0.35))
    cv.rect(*nb, '#ece5d8', radius=6)
    for i in range(1, 10):
        cv.rect(nb.x + 18, nb.y + i * nb.h / 10, nb.w - 36, 2, '#c9bfae')
    cv.rect(nb.x + nb.w * 0.1, nb.y + nb.h * 0.12, nb.w * 0.5, 6, '#3b3a44', radius=3)
    pen = (nb.right + 26, nb.y + nb.h * 0.15)
    ctx.save()
    ctx.translate(*pen)
    ctx.rotate(math.radians(78))
    cv.rect(0, -6, nb.h * 0.7, 12, '#20232c', radius=6)
    cv.rect(nb.h * 0.62, -6, nb.h * 0.08, 12, '#c9a14a', radius=4)
    ctx.restore()
    mx, my, mr = mug
    cv.shadow(mx - mr, my - mr, 2 * mr, 2 * mr, radius=mr, dx=6, dy=10, blur=20, color=(0, 0, 0, 0.4))
    cv.rect(mx - mr, my - mr, 2 * mr, 2 * mr, '#e8e3db', radius=mr)
    cv.rect(mx - mr * 0.76, my - mr * 0.76, 1.52 * mr, 1.52 * mr, '#4a2e1e', radius=mr * 0.76)
    cv.rect(mx + mr * 0.9, my - mr * 0.2, mr * 0.5, mr * 0.4, '#e8e3db', radius=mr * 0.2)
    px, py, pr = plant
    cv.shadow(px - pr, py - pr, 2 * pr, 2 * pr, radius=pr, dx=6, dy=10, blur=20, color=(0, 0, 0, 0.4))
    cv.rect(px - pr, py - pr, 2 * pr, 2 * pr, '#b8653f', radius=pr)
    for a in range(7):
        ang = a * 2 * math.pi / 7 + 0.3
        lx, ly = px + pr * 0.55 * math.cos(ang), py + pr * 0.55 * math.sin(ang)
        cv.rect(lx - pr * 0.42, ly - pr * 0.42, pr * 0.84, pr * 0.84, '#3f7a4a' if a % 2 else '#4f9159', radius=pr * 0.42)
    cv.shadow(*phone, radius=phone.w * 0.13, dx=8, dy=16, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(*phone, '#14151a', radius=phone.w * 0.13)
    scr = phone.pad(phone.w * 0.045)
    cv.rect(*scr, '#f1f2f4', radius=phone.w * 0.1)
    u = scr.w / 300
    kit.logo(cv, scr.x + 40 * u, scr.y + 52 * u, 18 * u, -0.6, name=None)
    text.draw(cv, 'Lumen', kit.font(22 * u, 800), scr.x + 66 * u, scr.y + 38 * u, '#1c1e25')
    text.draw(cv, 'Good evening,', kit.font(30 * u, 800, tracking=-0.02), scr.x + 22 * u, scr.y + 96 * u, '#1c1e25')
    text.draw(cv, 'all done today.', kit.font(30 * u, 800, tracking=-0.02), scr.x + 22 * u, scr.y + 134 * u, ACCENT)
    rows = 5
    top = scr.y + 196 * u
    rh = (scr.bottom - 24 * u - top) / rows
    for i in range(rows):
        y = top + i * rh
        cv.rect(scr.x + 18 * u, y, scr.w - 36 * u, rh - 10 * u, '#ffffff', radius=10 * u)
        r = 9 * u
        cv.rect(scr.x + 32 * u, y + rh / 2 - 5 * u - r, 2 * r, 2 * r, TEAL, radius=r)
        cv.rect(scr.x + 62 * u, y + rh / 2 - 10 * u, (scr.w - 110 * u) * (0.8 - 0.12 * (i % 3)), 10 * u, '#c3c7cf',
                radius=5 * u)
    return kit.to_pil(cv).convert('RGB'), phone


def _tinted(img, colour, amount):
    return PILImage.blend(img, PILImage.new('RGB', img.size, colour), amount)


@lru_cache(maxsize=2)
def desk_images(wide):
    w, h = (1280, 720) if wide else (720, 1280)
    base, phone = _desk(w, h, wide)
    dim = ImageEnhance.Brightness(ImageEnhance.Color(base).enhance(0.4)).enhance(0.26)
    dim = _tinted(dim, (12, 18, 42), 0.3)
    # Lit: the same desk under low warm sun, saturated and contrasty rather than
    # washed out, so the beam reads as light on things, not a pale stripe.
    lit = ImageEnhance.Color(ImageEnhance.Contrast(base).enhance(1.18)).enhance(1.3)
    r, g, b = lit.split()
    lit = PILImage.merge('RGB', (r.point(lambda v: min(255, v * 1.12)), g.point(lambda v: v * 0.93),
                                 b.point(lambda v: v * 0.7)))
    return vb.Image.from_pil(dim), vb.Image.from_pil(lit), phone


def _beam_path(ctx, x, h, width, skew, bars):
    """The beam: a slanted band with hard edges, crossed by the window's bars."""
    ctx.new_path()
    ctx.move_to(x, 0)
    ctx.line_to(x + width, 0)
    ctx.line_to(x + width + skew, h)
    ctx.line_to(x + skew, h)
    ctx.close_path()
    for u, bw in bars:
        bx = x + u * width
        ctx.move_to(bx, 0)
        ctx.line_to(bx + bw, 0)
        ctx.line_to(bx + bw + skew, h)
        ctx.line_to(bx + skew, h)
        ctx.close_path()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)


def _light(cv, st, zoom, centre, p, width, skew, bars=((0.48, 16),)):
    """The desk at `zoom` about `centre` (film px), dim, and lit warm inside
    the beam, whose left edge is at fraction `p` across the frame."""
    dim, lit, phone = desk_images(st.wide)
    frame = st.frame
    fw, fh = frame.w, frame.h
    dx, dy = fw / 2 - centre[0] * zoom, fh / 2 - centre[1] * zoom
    with cv.layer(dx=dx, dy=dy, scale=zoom):
        cv.image(dim, 0, 0, fw, fh)
    ctx = cv.ctx
    x = -width - skew + p * (fw + width + skew)
    ctx.save()
    _beam_path(ctx, x, fh, width, skew, bars)
    ctx.clip()
    with cv.layer(dx=dx, dy=dy, scale=zoom):
        cv.image(lit, 0, 0, fw, fh)
    g = cairo.LinearGradient(x, 0, x + width + skew, fh)   # a warm haze in the air of the beam
    g.add_color_stop_rgba(0, 1, 0.78, 0.45, 0.16)
    g.add_color_stop_rgba(1, 1, 0.66, 0.32, 0.04)
    ctx.set_source(g)
    ctx.paint()
    ctx.restore()
    box = Box(dx + phone.x * zoom, dy + phone.y * zoom, phone.w * zoom, phone.h * zoom)
    return box


def light_wide(cv, s, st):
    p = kit.lerp(0.12, 0.82, s.f / s.length)
    box = _light(cv, st, 1.0, (st.frame.w / 2, st.frame.h / 2), p, pick(st, 420, 330), pick(st, 300, 420),
                 bars=((0.36, 14), (0.68, 14)))
    c = st.content
    cv.mark('phone', max(box.x, c.x), max(box.y, c.y), min(box.right, c.right) - max(box.x, c.x),
            min(box.bottom, c.bottom) - max(box.y, c.y))


def light_close(cv, s, st):
    _, _, phone = desk_images(st.wide)
    zoom = pick(st, 1.75, 1.45)
    centre = (phone.cx, phone.y + phone.h * pick(st, 0.36, 0.42))
    p = kit.lerp(0.0, 0.62, vb.ease_in_out_quart(s.f / s.length))
    box = _light(cv, st, zoom, centre, p, pick(st, 700, 560), pick(st, 360, 500), bars=((0.5, 22),))
    c = st.content
    cv.mark('phone', max(box.x, c.x), max(box.y, c.y), min(box.right, c.right) - max(box.x, c.x),
            min(box.bottom, c.bottom) - max(box.y, c.y))


SCENES = {
    'gen-arcs': gen_arcs, 'gen-flow': gen_flow, 'gen-tiles': gen_tiles,
    'orbit-type': orbit_type, 'orbit-device': orbit_device, 'orbit-bleed': orbit_bleed,
    'light-wide': light_wide, 'light-close': light_close,
}
