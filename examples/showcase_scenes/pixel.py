"""Pixel-art layer: an 8-bit Lumi runs the day as a level, jumping to grab
each task, then the stage-clear screen. Drawn at 1/8 resolution and scaled
up hard-edged, held on twos; the look's own palette (STYLE.md's style-card
exception)."""
import math

from videobuilder import text

from . import kit
from .kit import ACCENT, BG, LINE

SKY, GROUND, GRASS, SUN, PIX_INK = '#8fd3f4', '#3a7d44', '#2f6a38', '#f4d35e', '#1d1f28'
PIXEL = 8
TASKS = (0.32, 0.54, 0.76)    # where the task blocks float, across the level
JUMP = 70                     # px of level either side of a block where Lumi is in the air


def _sky(px, w, h, floor, scroll):
    px.fill(SKY)
    px.rect(w - 200, 60, 112, 112, SUN, radius=56)
    for k, (u, v) in enumerate(((0.12, 0.2), (0.48, 0.1), (0.82, 0.26))):
        cx = (u * w - scroll * 0.3) % (w + 240) - 120
        px.rect(cx, v * h, 170, 44, '#ffffff', radius=22)
        px.rect(cx + 40, v * h - 26, 90, 44, '#ffffff', radius=22)
    for i in range(-1, int(w // 220) + 2):   # far hills, slower
        hx = i * 220 - (scroll * 0.5) % 220
        px.rect(hx, floor - 120, 260, 240, '#6fbf7a', radius=120)
    px.rect(0, floor, w, h - floor, GROUND)
    for i in range(-1, int(w // 64) + 2):
        px.rect(i * 64 - scroll % 64, floor, 32, 16, GRASS)


def _lumi(px, x, foot, swing, air):
    bw, bh = 140, 124
    by = foot - bh - 50
    px.rect(x - bw / 2, by, bw, bh, ACCENT, radius=44)
    for ex in (-26, 26):
        px.rect(x + ex - 10 + 12, by + 32, 20, 32, PIX_INK)
    if air:
        px.rect(x - 44, foot - 60, 32, 44, PIX_INK)
        px.rect(x + 12, foot - 52, 32, 44, PIX_INK)
    else:
        px.rect(x - 48 + swing * 16, foot - 52, 32, 52, PIX_INK)
        px.rect(x + 16 - swing * 16, foot - 52, 32, 52, PIX_INK)


def pixel_run(cv, s, st):
    cv.fill(BG)
    box = st.content
    n = s.f - s.f % 2   # held on twos
    w, h = box.w, box.h
    floor = h * 0.76
    # The level is wider than the frame: the camera follows Lumi from a quarter in.
    level = w * 1.9
    lx = kit.lerp(w * 0.12, level * 0.86, n / s.length)
    scroll = max(0.0, min(level - w, lx - w * 0.35))
    with cv.pixelated(PIXEL, x=box.x, y=box.y, w=w, h=h) as px:
        _sky(px, w, h, floor, scroll)
        foot, air, got = floor, False, 0
        for i, u in enumerate(TASKS):
            bx = u * level
            d = lx - bx
            if -JUMP <= d <= JUMP:   # mid-jump to the block
                t = (d + JUMP) / (2 * JUMP)
                foot = floor - 4 * t * (1 - t) * 150
                air = True
            if d > 0:
                got += 1
            sx = bx - scroll
            if d <= 0:   # a task block, still to get
                bob = 6 * math.sin(n / 6 + i)
                px.rect(sx - 40, floor - 250 + bob, 80, 80, '#ffffff', radius=6)
                px.outline(sx - 40, floor - 250 + bob, 80, 80, PIX_INK, width=10, radius=6)
            elif d < 140:   # just got: the tick, and +1 floating up
                px.rect(sx - 40, floor - 250, 80, 80, '#7ad38a', radius=6)
                px.outline(sx - 40, floor - 250, 80, 80, PIX_INK, width=10, radius=6)
                text.draw(px, '+1', kit.font(72, 800), sx - 34, floor - 340 - d * 0.6, PIX_INK)
            else:
                px.rect(sx - 40, floor - 250, 80, 80, '#7ad38a', radius=6)
                px.outline(sx - 40, floor - 250, 80, 80, PIX_INK, width=10, radius=6)
        _lumi(px, lx - scroll, foot, math.sin(n / 3), air)
        text.draw(px, f'TASKS {got}/3', kit.font(76, 800), 40, 30, PIX_INK)
    cv.outline(*box, LINE, width=2)
    cv.mark('level', *box)


def pixel_clear(cv, s, st):
    cv.fill(BG)
    box = st.content
    n = s.f - s.f % 2
    w, h = box.w, box.h
    floor = h * 0.76
    with cv.pixelated(PIXEL, x=box.x, y=box.y, w=w, h=h) as px:
        _sky(px, w, h, floor, 0)
        # The flag at the end of the level, Lumi bouncing beside it.
        fx = w * 0.7
        px.rect(fx, floor - 300, 14, 300, PIX_INK)
        rise = min(1.0, n / 12)
        px.rect(fx + 14, floor - 300 + (1 - rise) * 200, 110, 70, ACCENT)
        hop = abs(math.sin(n / 5)) * 60
        _lumi(px, w * 0.42, floor - hop, 0, hop > 10)
        # 9:16 stacks the title on two lines so the glyphs stay big enough to survive
        # the 1/8 grid; an ink outline keeps it off the sun and the clouds behind it
        f = kit.font(min(110, w * 0.11) if st.wide else w * 0.19, 900)
        words = ['STAGE CLEAR!'] if st.wide else ['STAGE', 'CLEAR!']
        y = h * 0.1
        fill = '#ffffff' if (n // 4) % 2 else SUN
        for i, word in enumerate(words):
            wx, wy = w / 2 - text.measure(word, f) / 2, y + i * text.line_height(f) * 0.9
            text.draw(px, word, f, wx + 2 * PIXEL, wy + 2 * PIXEL, PIX_INK)
            for dx, dy in ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)):
                text.draw(px, word, f, wx + dx * PIXEL, wy + dy * PIXEL, PIX_INK)
            text.draw(px, word, f, wx, wy, fill)
        for i in range(7):   # star bits bursting out
            a = 2 * math.pi * i / 7
            r = 60 + n * 9
            px.rect(w / 2 + r * math.cos(a) - 12, y + 60 + r * math.sin(a) * 0.6 - 12, 24, 24, SUN)
    cv.outline(*box, LINE, width=2)
    cv.mark('level', *box)


SCENES = {'pixel-run': pixel_run, 'pixel-clear': pixel_clear}
