"""Capability: camera on a screenshot. A generated "dashboard" page, taller
than the window, with a camera window that pans down the page and zooms in
on the chart card, while the navbar strip stays pinned to the window's top
edge the whole time.

    python -m videobuilder preview examples/capabilities/camera-on-a-screenshot.py

LOOP = True: the pan/zoom is driven by a continuous phase
`p = 0.5 - 0.5*cos(2*pi*n/TOTAL)`, which is 0 at both n=0 and n=TOTAL, so the
camera is at the same position at both ends by construction. The window
itself never moves or fades; only the phase loops.
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image as PILImage, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, text  # noqa: E402

LOOP = True
FPS = 30
TOTAL = 90   # 3.0 s

PAGE_W, PAGE_H = 1000, 2000
NAVBAR_H = 130

PAGE_BG = '#eef0f2'
CARD_BG = '#ffffff'
CARD_BORDER = '#dadde3'
TEXT_DARK = '#20222a'
TEXT_MUTED = '#868c97'


def _font(size, name='Inter-Variable.ttf'):
    return ImageFont.truetype(str(_kit.ASSETS / name), size)


def _rect(draw, x, y, w, h, fill=None, outline=None, width=1, radius=0):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill, outline=outline, width=width)


def _build_page():
    """A mock dashboard page, generated once at import: navbar, two stat
    cards, a bar chart card and a short list card, stacked top to bottom."""
    rnd = random.Random(7)
    img = PILImage.new('RGB', (PAGE_W, PAGE_H), PAGE_BG)
    d = ImageDraw.Draw(img)

    # Navbar: dark strip, logo mark, two nav labels.
    d.rectangle((0, 0, PAGE_W, NAVBAR_H), fill=_kit.BG)
    d.ellipse((40, 45, 80, 85), fill=_kit.ACCENT)
    label_f = _font(30)
    d.text((104, 52), 'Overview', font=label_f, fill=_kit.INK)
    d.text((300, 52), 'Settings', font=label_f, fill=_kit.MUTED)

    # Row 1: two stat cards.
    row1_y, row1_h = NAVBAR_H + 40, 300
    card_w, gap = 440, 40
    stats = (('Active users', '12,480', '+4.2%'), ('Avg. session', '6m 12s', '+0.8%'))
    for i, (label, value, delta) in enumerate(stats):
        x = 40 + i * (card_w + gap)
        _rect(d, x, row1_y, card_w, row1_h, fill=CARD_BG, outline=CARD_BORDER, width=2, radius=18)
        d.text((x + 36, row1_y + 40), label, font=_font(26), fill=TEXT_MUTED)
        d.text((x + 36, row1_y + 90), value, font=_font(64), fill=TEXT_DARK)
        d.text((x + 36, row1_y + 180), delta, font=_font(26), fill=_kit.TEAL)

    # Row 2: a bar-chart card.
    row2_y, row2_h = row1_y + row1_h + 40, 480
    _rect(d, 40, row2_y, 920, row2_h, fill=CARD_BG, outline=CARD_BORDER, width=2, radius=18)
    d.text((76, row2_y + 32), 'Weekly conversions', font=_font(28), fill=TEXT_DARK)
    n_bars, bar_w, bar_gap = 7, 84, 32
    base_x, base_y, top_y = 76, row2_y + row2_h - 56, row2_y + 110
    max_bar_h = base_y - top_y
    for i in range(n_bars):
        bh = max_bar_h * (0.35 + 0.6 * rnd.random())
        bx = base_x + i * (bar_w + bar_gap)
        color = _kit.ACCENT if i % 3 == 0 else _kit.TEAL
        _rect(d, bx, base_y - bh, bar_w, bh, fill=color, radius=8)
    d.line((base_x, base_y, base_x + n_bars * (bar_w + bar_gap) - bar_gap, base_y), fill=CARD_BORDER, width=2)

    # Row 3: a short list card.
    row3_y = row2_y + row2_h + 40
    row3_h = PAGE_H - row3_y - 40
    _rect(d, 40, row3_y, 920, row3_h, fill=CARD_BG, outline=CARD_BORDER, width=2, radius=18)
    items = (('Billing', 'Invoices and payment methods'), ('Team', '6 members, 2 pending invites'),
             ('Integrations', '3 connected, 1 needs attention'), ('API keys', '2 active keys'))
    item_h = (row3_h - 40) / len(items)
    for i, (title, sub) in enumerate(items):
        iy = row3_y + 20 + i * item_h
        d.rounded_rectangle((76, iy + 14, 76 + 36, iy + 50), radius=8,
                             fill=_kit.ACCENT if i % 2 == 0 else _kit.TEAL)
        d.text((132, iy + 10), title, font=_font(28), fill=TEXT_DARK)
        d.text((132, iy + 44), sub, font=_font(22), fill=TEXT_MUTED)
        if i:
            d.line((76, iy, 924, iy), fill=CARD_BORDER, width=1)
    return img


PAGE_IMG = vb.Image.from_pil(_build_page())
NAVBAR_SRC = Box(0, 0, PAGE_W, NAVBAR_H)

TITLE_F = _kit.font(32, 700)

CENTER_X = 500.0
CENTER_Y0, CENTER_Y1 = 480.0, 750.0   # wide overview -> pushed in on the chart card
SCALE0, SCALE1 = 0.60, 1.05


def phase(n):
    """0 at n=0 and n=TOTAL, peaking at the midpoint: a true back-and-forth."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * n / TOTAL)


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    title_box = _kit.text_marked(cv, 'title', text.wrap('Camera on a screenshot', TITLE_F, s.w), TITLE_F,
                                  s.x, s.y, _kit.INK)

    window = Box(s.x, title_box.bottom + 28, s.w, s.bottom - title_box.bottom - 28)
    p = phase(n)
    center = (CENTER_X, CENTER_Y0 + (CENTER_Y1 - CENTER_Y0) * p)
    scale = vb.log_lerp(SCALE0, SCALE1, p)
    view = cv.view(PAGE_IMG, window, center=center, scale=scale, radius=14, background=_kit.BG)
    view.pin(NAVBAR_SRC, y=window.y)
    cv.outline(*window, _kit.LINE, width=2, radius=14)
    cv.mark('screenshot', *window)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((0, 'wide'), (TOTAL // 2, 'pushed in')))

if __name__ == '__main__':
    vb.main(__file__)
