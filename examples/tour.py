"""A 12-second tour: one film, three formats.

    python -m videobuilder preview examples/tour.py
    python -m videobuilder render examples/tour.py --format all

Shows the beat timeline, springs and easing, balanced text wrapping, a
generated image fitted into a card, and a per-format layout table. The
picture and the click track are made here in code; the font is vendored
with its licence in examples/assets/. The colours and sizes are this
film's choices, not the framework's.
"""
import array
import hashlib
import math
import os
import random
import tempfile
import wave
from pathlib import Path

from PIL import Image as PILImage, ImageDraw, ImageFilter

import videobuilder as vb
from videobuilder import Box, fr, per_format, text

HERE = Path(__file__).resolve().parent
text.register(HERE / 'assets' / 'Cantarell-VF.otf')

# ---- time: 120 bpm at 30 fps is 15 frames a beat; 24 beats is 12 s ----
GRID = vb.Grid(fps=30, bpm=120)
TIMELINE = vb.Timeline(GRID, [
    vb.Segment('title', 0, 6),
    vb.Segment('picture', 6, 13),
    vb.Segment('mechanisms', 13, 20),
    vb.Segment('end', 20, 24),
], end=24)
FPS = GRID.fps

# ---- look: this film's own palette and type ----
BG = '#0f1420'
INK = '#f4f1ea'
MUTED = '#9aa3b5'
ACCENT = '#ffb547'
CARD = '#1b2333'
FAMILY = 'Cantarell'

# ---- layout per format: the same film, laid out three ways ----
LAYOUT = {
    '*': dict(pad=96, title=124, sub=50, body=46, label=44, small=30,
              picture='column', cards='column', card_gap=36),
    '16x9': dict(pad=120, title=132, sub=52, picture='row', cards='row', card_gap=48),
    '1x1': dict(pad=80, title=108, sub=44, body=40, label=38, small=26,
                picture='column', cards='row', card_gap=28),
}

EASE_OUT = vb.bezier(0.16, 1, 0.3, 1)
EASE_IN_OUT = vb.bezier(0.65, 0, 0.35, 1)
BOUNCY = dict(stiffness=170, damping=12)
SETTLE = vb.critical(120)


def font(size, weight=400, **kw):
    return vb.Font(FAMILY, size, weight=weight, **kw)


# ---- a picture, generated: a layered landscape, seeded so it never changes ----
def _landscape(w=1600, h=1000, seed=7):
    rnd = random.Random(seed)
    im = PILImage.new('RGB', (w, h))
    d = ImageDraw.Draw(im)
    top, bottom = (34, 52, 92), (255, 166, 102)
    for y in range(h):
        t = y / (h - 1)
        d.line([(0, y), (w, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    sun = PILImage.new('L', (w, h), 0)
    ImageDraw.Draw(sun).ellipse((w * 0.62, h * 0.30, w * 0.62 + 220, h * 0.30 + 220), fill=255)
    im.paste((255, 226, 170), mask=sun.filter(ImageFilter.GaussianBlur(3)))
    for i, colour in enumerate([(92, 82, 120), (60, 58, 96), (36, 38, 66), (20, 24, 42)]):
        base = h * (0.55 + 0.11 * i)
        pts, x = [(0, h)], 0
        while x <= w:
            pts.append((x, base - rnd.uniform(0, 140 - 25 * i)))
            x += rnd.randint(60, 160)
        pts += [(w, base - 40), (w, h)]
        d.polygon(pts, fill=colour)
    return im


PICTURE = vb.Image.from_pil(_landscape())


# ---- sound, generated: a click on every beat (accented on the bar) over a quiet two-note pad ----
def _click_track():
    rate, beats = 48000, int(TIMELINE.end)
    seconds = TIMELINE.frames / FPS
    n = int(rate * seconds)
    spb = 60 / GRID.bpm
    key = hashlib.sha1(f'{rate}{beats}{GRID.bpm}{n}v1'.encode()).hexdigest()[:12]
    path = os.path.join(tempfile.gettempdir(), f'videobuilder-tour-{key}.wav')
    if os.path.exists(path):
        return path
    buf = array.array('h', bytes(2 * n))
    for i in range(n):
        t = i / rate
        pad = 0.06 * (math.sin(2 * math.pi * 220 * t) + 0.6 * math.sin(2 * math.pi * 329.63 * t))
        pad *= min(1.0, t / 1.5, (seconds - t) / 1.5)  # fade the pad in and out
        k = int(t / spb)
        dt = t - k * spb
        click = 0.0
        if dt < 0.06:
            f = 1760 if k % 4 == 0 else 1320
            click = (0.5 if k % 4 == 0 else 0.3) * math.exp(-dt * 90) * math.sin(2 * math.pi * f * dt)
        buf[i] = int(max(-1.0, min(1.0, pad + click)) * 32767)
    tmp = f'{path}.{os.getpid()}.tmp'
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(buf.tobytes())
    os.replace(tmp, path)
    return path


# ---- helpers ----
def appear(f, delay=0, spring=SETTLE):
    """0 -> 1 progress of an entrance `delay` frames into the segment."""
    return vb.spring_at(f - delay, FPS, **spring)


def exit_fade(f, length, frames=8):
    """1 -> 0 over the last `frames` of a segment `length` long."""
    return vb.interpolate(f, [length - frames, length], [1, 0], EASE_IN_OUT)


def wrapped(s, fnt, width):
    lines = text.wrap(s, fnt, width, balance=True)
    w, h = text.block_size(lines, fnt)
    return lines, w, h


def beat_pulse(cv, n, box):
    """A dot that swells on every beat: the grid made visible."""
    beat = n / GRID.frames_per_beat
    p = beat - math.floor(beat)
    r = 10 + 10 * math.exp(-p * 6)
    cv.rect(box.x - r, box.y - r, 2 * r, 2 * r, ACCENT, radius=r, alpha=0.9)
    cv.mark('beat', box.x - r, box.y - r, 2 * r, 2 * r)


# ---- scenes: each is a pure function of the frame within its segment ----
def title(cv, f, length, L, frame):
    title_font = font(L['title'], 760, tracking=-0.02, line_height=1.05)
    sub_font = font(L['sub'], 400, line_height=1.3)
    lines, w, h = wrapped('Films made in code, one frame at a time', title_font, frame.w * 0.86)
    sub, sw, sh = wrapped('A timeline, springs, text and layout. Nothing else.', sub_font, frame.w * 0.8)
    block = frame.center(max(w, sw), h + 40 + sh)
    lh = text.line_height(title_font)
    out = exit_fade(f, length)
    for i, line in enumerate(lines):
        s = appear(f, 4 + 5 * i, BOUNCY)
        with cv.layer(opacity=min(1, s) * out, dy=(1 - s) * 70):
            text.draw(cv, line, title_font, block.x, block.y + i * lh, INK, align='center', width=block.w)
    p = EASE_OUT(vb.clamp01((f - 24) / 24))
    with cv.layer(opacity=p * out, dy=(1 - p) * 24):
        text.draw(cv, sub, sub_font, block.x, block.y + h + 40, MUTED, align='center', width=block.w)


def picture(cv, f, length, L, frame):
    out = exit_fade(f, length)
    body = font(L['body'], 400, line_height=1.35)
    head = font(L['label'] * 1.3, 700, line_height=1.1)
    if L['picture'] == 'row':
        img_box, txt_box = frame.row(1.25 * fr, fr, gap=L['pad'])
        img_box = img_box.contain(16, 10)
    else:
        img_box, txt_box = frame.column(fr, 0.62 * fr, gap=L['pad'] * 0.6)
        img_box = img_box.contain(16, 10, at='bottom')
    # The card springs in; the picture inside drifts in scale, evenly in log space.
    s = appear(f, 0, SETTLE)
    card = img_box.scaled(0.92 + 0.08 * s)
    zoom = vb.log_lerp(1.0, 1.18, vb.interpolate(f, [0, length], [0, 1]))
    radius = 28
    with cv.layer(opacity=min(1, s) * out):
        cv.shadow(*card, radius=radius, dy=18, blur=50, color=(0, 0, 0, 0.45))
        with cv.clip(*card, radius=radius):
            cv.image(PICTURE, *card.cover(PICTURE.w, PICTURE.h, at='center').scaled(zoom))
        cv.mark('picture_card', *card)
    heading, hw, hh = wrapped('Pictures fit, cover or contain', head, txt_box.w)
    copy, cw, ch = wrapped('Formats are layouts, not crops: each one places this card and this '
                           'paragraph for its own shape, from one source.', body, txt_box.w)
    anchor = 'left' if L['picture'] == 'row' else 'top'
    block = txt_box.anchor(txt_box.w, hh + 24 + ch, anchor)
    align = 'left' if L['picture'] == 'row' else 'center'
    for k, (lines, fnt, colour, y) in enumerate([(heading, head, INK, block.y),
                                                 (copy, body, MUTED, block.y + hh + 24)]):
        p = EASE_OUT(vb.clamp01((f - 10 - 8 * k) / 20))
        with cv.layer(opacity=p * out, dx=(1 - p) * 40 if align == 'left' else 0, dy=0 if align == 'left' else (1 - p) * 30):
            text.draw(cv, lines, fnt, block.x, y, colour, align=align, width=block.w)


def _plot(cv, box, fn, colour, progress):
    """A curve y = fn(x) on [0, 1], drawn up to `progress`."""
    ctx = cv.ctx
    steps = 64
    ctx.new_path()
    for i in range(int(steps * progress) + 1):
        x = i / steps
        y = fn(x)
        ctx.line_to(box.x + x * box.w, box.bottom - y * box.h)
    ctx.set_source_rgba(*vb.canvas.rgba(colour))
    ctx.set_line_width(max(3, min(box.w, box.h) / 40))
    ctx.set_line_cap(1)  # round
    ctx.set_line_join(1)
    ctx.stroke()


def mechanisms(cv, f, length, L, frame):
    out = exit_fade(f, length)
    head = font(L['label'] * 1.3, 700)
    _, _, hh = wrapped('Three mechanisms', head, frame.w)
    top, rest = frame.column(hh, fr, gap=L['pad'] * 0.5)
    p = EASE_OUT(vb.clamp01(f / 16))
    with cv.layer(opacity=p * out):
        text.draw(cv, 'Three mechanisms', head, top.x, top.y, INK, align='center', width=top.w)
    split = rest.row if L['cards'] == 'row' else rest.column
    cards = split(fr, fr, fr, gap=L['card_gap'])
    label = font(L['label'], 700)
    small = font(L['small'], 400)
    items = [
        ('Springs', 'real physics, any frame alone', lambda x: vb.spring(x * 1.6, **BOUNCY) / 1.25),
        ('Easing', 'CSS cubic-bezier curves', lambda x: EASE_IN_OUT(x)),
        ('Beats', 'cuts land on the grid', lambda x: math.floor(x * 8 + 1e-9) / 8),
    ]
    for i, (box, (name, note, fn)) in enumerate(zip(cards, items)):
        s = appear(f, 6 + 6 * i, BOUNCY)
        with cv.layer(opacity=min(1, s) * out, dy=(1 - s) * 60):
            cv.rect(*box, CARD, radius=24)
            inner = box.pad(min(box.w, box.h) * 0.1)
            lh = text.line_height(label)
            note_lines = text.wrap(note, small, inner.w)
            graph, words = inner.column(fr, lh + 8 + text.line_height(small) * len(note_lines), gap=inner.h * 0.06)
            graph = graph.contain(16, 9) if L['cards'] == 'column' else graph
            draw_p = EASE_IN_OUT(vb.clamp01((f - 12 - 6 * i) / 30))
            cv.rect(graph.x, graph.bottom, graph.w, 2, MUTED, alpha=0.4)
            _plot(cv, graph, fn, ACCENT, draw_p)
            text.draw(cv, name, label, words.x, words.y, INK)
            text.draw(cv, note_lines, small, words.x, words.y + lh + 8, MUTED)


def end(cv, f, length, L, frame):
    big = font(L['title'] * 0.8, 760, tracking=-0.01)
    small = font(L['sub'], 400)
    s = appear(f, 0, SETTLE)
    fade = vb.interpolate(f, [length - 20, length - 1], [1, 0], EASE_IN_OUT)
    lines, w, h = wrapped('Now make yours.', big, frame.w * 0.9)
    sh = text.line_height(small)
    block = frame.center(frame.w, h + 28 + sh)
    with cv.layer(opacity=min(1, s) * fade, scale=1, dy=(1 - s) * 40):
        text.draw(cv, lines, big, block.x, block.y, INK, align='center', width=block.w)
        text.draw(cv, 'python -m videobuilder preview film.py', small, block.x, block.y + h + 28, ACCENT,
                  align='center', width=block.w)


SCENES = {'title': title, 'picture': picture, 'mechanisms': mechanisms, 'end': end}


def draw(n, cv):
    L = per_format(LAYOUT, cv)
    frame = Box.of(cv).pad(L['pad'])
    seg, f = TIMELINE.at(n)
    length = GRID.b(seg.until) - GRID.b(seg.at)
    SCENES[seg.name](cv, f, length, L, frame)
    beat_pulse(cv, n, Box.of(cv).pad(L['pad'] * 0.5))


EXPECT = [
    vb.visible('beat', vb.seg('title'), note='The beat is visible from the first frame.'),
    vb.visible('beat', vb.seg('end', 'mid'), note='Keep the beat visible through the ending.'),
    vb.visible('picture_card', vb.seg('picture', 5), note='Keep the picture card visible.'),
]


FILM = vb.Film(
    draw=draw,
    timeline=TIMELINE,
    formats=('16x9', '9x16', '1x1'),
    background=BG,
    audio=vb.Audio(_click_track(), gain_db=-3),
)
