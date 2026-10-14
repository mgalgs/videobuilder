"""Capability: image treatments. One generated landscape-ish photo shown in
three panels at once: cover-cropped into a square card, contain-fitted
inside a bordered (letterboxed) square, and clipped to a rounded rect with
a soft drop shadow — the box-model moves for putting a picture in a layout.

    python -m videobuilder preview examples/capabilities/image-treatments.py

LOOP = True: the three panels cascade in left to right, each starting while
the one before it is still settling, hold together, then leave the same
way, so both ends of the clip are the same empty "not yet arrived" rest
state.
"""
import random
import sys
from pathlib import Path

from PIL import Image as PILImage, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, fr, text  # noqa: E402

LOOP = True
FPS = 30
START = 6             # frames of rest before the first panel starts entering
STAGGER = 6           # frames between one panel's start and the next's (200 ms)
ENTER, HOLD, LEAVE = 16, 40, 16
N_PANELS = 3
LAST_ENTER_END = START + (N_PANELS - 1) * STAGGER + ENTER
LEAVE_START = LAST_ENTER_END + HOLD
TOTAL = LEAVE_START + (N_PANELS - 1) * STAGGER + LEAVE + 6   # +6 frames tail rest
RISE = 40

PHOTO_W, PHOTO_H = 1400, 900


def _build_photo():
    """A seeded procedural 'photo': a vertical gradient with a soft sun disc
    and a couple of overlapping hill shapes — imagery, not a flat colour."""
    rnd = random.Random(11)
    top, bottom = (31, 94, 86), (233, 142, 88)
    grad = PILImage.new('RGB', (1, PHOTO_H))
    for y in range(PHOTO_H):
        t = y / (PHOTO_H - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    img = grad.resize((PHOTO_W, PHOTO_H)).convert('RGBA')

    overlay = PILImage.new('RGBA', (PHOTO_W, PHOTO_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    sun_cx, sun_cy, sun_r = PHOTO_W * 0.72, PHOTO_H * 0.30, PHOTO_W * 0.11
    d.ellipse((sun_cx - sun_r, sun_cy - sun_r, sun_cx + sun_r, sun_cy + sun_r), fill=(255, 219, 168, 190))
    img = PILImage.alpha_composite(img, overlay)

    d = ImageDraw.Draw(img)
    for i, (cx_f, base_r, tone) in enumerate((
        (0.18, 0.30, (18, 48, 44)), (0.55, 0.34, (23, 60, 55)), (0.88, 0.26, (15, 40, 38)),
    )):
        jitter = 1 + 0.08 * (rnd.random() - 0.5)
        cx, r = PHOTO_W * cx_f, PHOTO_W * base_r * jitter
        cy = PHOTO_H * 0.86
        d.ellipse((cx - r, cy - r * 0.6, cx + r, cy + r * 1.4), fill=tone)
    return img.convert('RGB')


PHOTO = vb.Image.from_pil(_build_photo())

TITLE_F = _kit.font(32, 700)
CAPTION_F = _kit.font(20, 600)

PANELS = (
    ('cover', 'cover'),
    ('contain', 'contain'),
    ('shadow', 'shadow + rounded'),
)


def panel_p(i, n):
    """0 (gone) .. 1 (in place) .. 0 (gone), eased both ways, for panel i,
    staggered STAGGER frames after panel i - 1."""
    enter_n = n - (START + i * STAGGER)
    if enter_n < 0:
        return 0.0
    if enter_n < ENTER:
        return vb.interpolate(enter_n, [0, ENTER], [0, 1], ease=vb.ease_out_quint)
    if n < LEAVE_START:
        return 1.0
    leave_n = n - (LEAVE_START + i * STAGGER)
    if leave_n < 0:
        return 1.0
    if leave_n < LEAVE:
        return vb.interpolate(leave_n, [0, LEAVE], [1, 0], ease=vb.ease_in_expo)
    return 0.0


def draw_panel(cv, name, caption, card, caption_y):
    if name == 'cover':
        with cv.clip(*card, radius=12):
            cv.image(PHOTO, *card.cover(PHOTO.w, PHOTO.h))
        cv.outline(*card, _kit.MUTED, width=2, radius=12)
    elif name == 'contain':
        cv.rect(*card, _kit.LINE, radius=12)
        cv.image(PHOTO, *card.contain(PHOTO.w, PHOTO.h))
        cv.outline(*card, _kit.MUTED, width=2, radius=12)
    else:
        cv.shadow(*card, radius=18, dy=14, blur=28, spread=0, color=(0, 0, 0, 0.5))
        with cv.clip(*card, radius=18):
            cv.image(PHOTO, *card.cover(PHOTO.w, PHOTO.h))
    cv.mark(f'{name}-image', *card)
    _kit.text_marked(cv, f'{name}-caption', text.wrap(caption, CAPTION_F, card.w), CAPTION_F,
                      card.x, caption_y, _kit.MUTED, align='center', width=card.w)


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 48)
    title_box = _kit.text_marked(cv, 'title', text.wrap('Image treatments', TITLE_F, s.w), TITLE_F,
                                  s.x, s.y, _kit.INK)

    content = Box(s.x, title_box.bottom + 32, s.w, s.bottom - title_box.bottom - 32)
    cols = content.row(fr, fr, fr, gap=24)
    card_size = cols[0].w
    caption_h = text.block_size(['cover'], CAPTION_F)[1]
    group_h = card_size + 16 + caption_h
    top = content.y + (content.h - group_h) / 2

    for i, (col, (name, caption)) in enumerate(zip(cols, PANELS)):
        p = panel_p(i, n)
        if p <= 0.0:
            continue
        card = Box(col.x, top, card_size, card_size)
        with cv.layer(opacity=p, dy=(1 - p) * RISE):
            draw_panel(cv, name, caption, card, top + card_size + 16)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((LAST_ENTER_END + 5, 'settled'), (LEAVE_START - 5, 'hold')))

if __name__ == '__main__':
    vb.main(__file__)
