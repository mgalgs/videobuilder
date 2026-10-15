"""Images: slow push. One picture fills the frame and the camera creeps in on
it -- a Ken Burns push with a slow drift, live film grain and a lens's
falloff -- while a lower-third caption bar wipes open on the first beat, its
lines rising in one after another, and a hairline ticks off the beats.

Laid out per format: in 16:9 and 1:1 the camera pushes in and drifts a
little; in 9:16, where a landscape picture is far wider than the frame, it
travels across the picture instead, so the tall frame sees the whole scene
over the shot rather than a static centre crop.
"""
import math

import videobuilder as vb
from videobuilder import Box, text

from .. import kit
from ..schema import Component, Slot
from . import _images_util as u

WIPE = 12        # frames for the caption bar to open
LINE_STAGGER = 4  # frames between caption lines rising in
PAD = 22


def _camera(fmt_aspect, t):
    """(zoom, fx, fy) at shot progress t in 0-1: a push in, or a sideways travel."""
    e = 0.5 - 0.5 * math.cos(math.pi * t)  # slow at both ends
    if fmt_aspect < 0.8:   # tall frame: travel across the picture
        return 1.0 + 0.08 * e, 0.24 + 0.42 * e, 0.5
    return 1.06 + 0.16 * e, 0.47 + 0.07 * e, 0.52 - 0.05 * e


def _bar_layout(cv, kicker, caption):
    """The caption bar's box, and its kicker and caption (font, lines), per format."""
    W, H = cv.width, cv.height
    tall = H > W * 1.2
    if tall:
        bar_w, bottom = W - 2 * 36, H * 0.83
    elif W > H * 1.2:
        bar_w, bottom = min(620, W - 2 * 40), H - 40
    else:
        bar_w, bottom = W - 2 * 36, H - 36
    inner = bar_w - 2 * PAD - 8
    kick_f = kit.mono(15, 600, tracking=0.16)
    kick_lines = text.wrap(kicker.upper(), kick_f, inner) if kicker else ()
    cap_f, cap_lines = (u.fit_lines(caption, inner, (40, 36, 32, 28) if not tall else (38, 34, 30, 26), max_lines=3)
                        if caption else (None, ()))
    h = PAD * 2
    if kick_lines:
        h += text.block_size(kick_lines, kick_f)[1]
    if cap_lines:
        h += text.block_size(cap_lines, cap_f)[1]
    if kick_lines and cap_lines:
        h += 10
    h += 10  # the beat hairline
    x = (W - bar_w) / 2 if tall or abs(W - H) < 2 else 40
    return Box(x, bottom - h, bar_w, h), (kick_f, kick_lines), (cap_f, cap_lines)


def draw(cv, shot):
    data = shot.data
    img = data['image']
    accent = data['accent']
    frame = Box.of(cv)
    t = vb.clamp01(shot.f / max(1, shot.length - 1))
    zoom, fx, fy = _camera(cv.width / cv.height, t)
    u.cover_image(cv, img, frame, zoom=zoom, fx=fx, fy=fy)
    u.vignette(cv, frame, 0.5)
    # A grain that slides on twos: film, not a dirty lens.
    step = shot.f // 2
    u.grain(cv, 0.14, seed=7, dx=(step * 37) % 211, dy=(step * 53) % 197)
    cv.mark('photo', *frame)

    kicker, caption = data['kicker'], data['caption']
    if not (kicker or caption):
        return
    fpb = u.beat_frames(shot)
    start = fpb - 6  # open on the first beat, landing just after it
    k = shot.f - start
    if k < 0:
        return
    bar, (kick_f, kick_lines), (cap_f, cap_lines) = _bar_layout(cv, kicker, caption)
    open_p = vb.ease_out_expo(vb.clamp01(k / WIPE))
    with cv.clip(bar.x, bar.y, bar.w * open_p, bar.h):
        cv.rect(*bar, kit.BG, alpha=0.82)
    cv.rect(bar.x, bar.y, 6, bar.h * vb.ease_out_expo(vb.clamp01(k / 8)), accent)
    cv.mark('caption-bar', *bar)

    x, y = bar.x + PAD + 8, bar.y + PAD
    if kick_lines:
        q = vb.clamp01((k - 4) / 10)
        box = text.draw(cv, kick_lines, kick_f, x + (1 - vb.ease_out_quint(q)) * -14, y, accent, alpha=q)
        if q > 0:
            cv.mark('kicker', x, y, box.w, box.h)
        y += box.h + (10 if cap_lines else 0)
    lh = text.line_height(cap_f) if cap_f else 0
    for i, ln in enumerate(cap_lines):
        q = vb.ease_out_quint(vb.clamp01((k - 6 - i * LINE_STAGGER) / 12))
        if q <= 0:
            continue
        with cv.clip(bar.x, y + i * lh, bar.w, lh):
            text.draw(cv, [ln], cap_f, x, y + i * lh + (1 - q) * lh * 0.8, kit.INK)
    if cap_lines:
        w, h = text.block_size(cap_lines, cap_f)
        cv.mark('caption', x, y, w, h)

    # The hairline: the shot's progress, with a tick on every beat.
    hy = bar.bottom - PAD + 4
    span = bar.w - 2 * PAD - 8
    cv.rect(x, hy, span * open_p, 2, kit.LINE)
    cv.rect(x, hy, span * t * open_p, 2, accent)
    beats = shot.segment.until - shot.segment.at
    for b in range(1, int(beats)):
        bx = x + span * b / beats
        if bx <= x + span * open_p:
            lit = shot.f >= b * fpb
            pop = 1 + 0.8 * max(0.0, 1 - (shot.f - b * fpb) / 6) if lit else 1
            cv.rect(bx - 1.5, hy - 3 * pop, 3, 2 + 6 * pop, accent if lit else kit.MUTED)


COMPONENT = Component(
    id='slow-push',
    kind='images',
    description='One picture filling the frame with a slow Ken Burns push and drift, film grain, and a '
                'lower-third caption bar that wipes open on the first beat. In 9:16 the camera travels across the picture.',
    tags=('images', 'photo', 'ken-burns', 'full-bleed', 'caption', 'cinematic'),
    formats=('16x9', '9x16', '1x1'),
    beats=(4, 10),
    slots=(
        Slot('image', 'image', True, 'The picture, ideally landscape; it fills the whole frame.'),
        Slot('caption', 'text', False, 'One sentence about the picture, shown in the caption bar.', max_length=64),
        Slot('kicker', 'text', False, 'A short label above the caption, like a chapter or place name.', max_length=28),
        Slot('accent', 'color', False, 'Colour of the bar\'s edge, the kicker and the beat ticks.'),
    ),
    sample={'image': u.photo('coast'), 'caption': 'The light keeps watch long after the last ferry leaves.',
            'kicker': 'Chapter two · The coast', 'accent': kit.ACCENT},
    draw=draw,
    overlap_ok=(('photo', 'caption-bar'), ('photo', 'kicker'), ('photo', 'caption'),
                ('caption-bar', 'kicker'), ('caption-bar', 'caption')),
)
