"""Images: photo stack. Instant-camera prints drop onto a dark felt table
one per beat: each falls toward the table from above the camera (big, tilted,
its shadow wide and soft), lands on a spring with a little squash and comes
to rest at its own slight angle, its shadow tightening as it touches down.
A handwritten-style note sits on the top print's margin, a torn paper label
is slapped down with a strip of tape, and window light falls across it all.

Laid out per format: the prints spread left to right with the label on the
left in 16:9, cascade top to bottom under the label in 9:16, and cluster
above the label in 1:1.
"""
import math
import random
from functools import lru_cache

import cairo
from PIL import Image as PILImage, ImageDraw, ImageFilter

import videobuilder as vb
from videobuilder import Box, paths, text

from .. import kit
from ..schema import Component, Slot
from . import _images_util as u

TABLE = '#1b1e25'
PAPER = '#f3efe6'
INK_NOTE = '#283a8a'
LABEL_INK = '#1b1916'
DROP = vb.damped(0.42, hz=2.3)
ANGLES = (-7.0, 5.5, -3.0, 8.0, -5.0)  # degrees, one per print in order


def _regions(W, H):
    """(table region for the prints, label region) per format."""
    if W > H * 1.2:
        return Box(318, 16, W - 318 - 16, H - 32), Box(44, 60, 250, H - 120)
    if H > W * 1.2:
        return Box(16, 236, W - 32, H - 236 - 40), Box(40, 52, W - 80, 160)
    return Box(16, 16, W - 32, H * 0.72 - 16), Box(40, H * 0.75, W - 80, H * 0.25 - 32)


def _aabb(cx, cy, w, h, a):
    c, s = abs(math.cos(a)), abs(math.sin(a))
    bw, bh = w * c + h * s, w * s + h * c
    return Box(cx - bw / 2, cy - bh / 2, bw, bh)


def _spots(R, n):
    """(cx, cy, angle radians, print width) for each of `n` prints, inside R."""
    landscape = R.w >= R.h
    pw = min(R.w, R.h) * (0.56 if n <= 3 else 0.5) if landscape else min(R.w * 0.62, R.h * (0.5 if n <= 3 else 0.4))
    ph = pw * 1.2
    out = []
    for i in range(n):
        a = math.radians(ANGLES[i % len(ANGLES)])
        t = i / (n - 1) if n > 1 else 0.5
        side = 1 if i % 2 else -1
        if landscape:
            cx = R.x + pw * 0.62 + (R.w - pw * 1.24) * t
            cy = R.cy + side * R.h * 0.07
        else:
            cy = R.y + ph * 0.6 + (R.h - ph * 1.2) * t
            cx = R.cx + side * R.w * 0.13
        bb = _aabb(cx, cy, pw, ph, a)
        cx += max(0, R.x - bb.x) - max(0, bb.right - R.right)
        cy += max(0, R.y - bb.y) - max(0, bb.bottom - R.bottom)
        out.append((cx, cy, a, pw))
    return out


@lru_cache(maxsize=8)
def _light(W, H):
    """Window light as a soft-light map: lighter panes across a diagonal, darker
    mullions between, a broad falloff toward the far corner."""
    s = 4
    w, h = W // s, H // s
    m = PILImage.new('L', (w, h), 108)
    d = ImageDraw.Draw(m)
    slope = 0.5
    unit = max(w, h) / 9
    for x0, width in ((-unit * 2.2, unit * 1.7), (-unit * 0.3, unit * 1.5), (unit * 1.4, unit * 1.0)):
        d.polygon([(x0, 0), (x0 + width, 0), (x0 + width + h * slope, h), (x0 + h * slope, h)], fill=176)
    m = m.filter(ImageFilter.GaussianBlur(3)).resize((W, H), PILImage.BICUBIC)
    return vb.Image.from_pil(PILImage.merge('RGB', (m, m, m)))


def _soft_light(cv, img, dx=0.0):
    ctx = cv.ctx
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
    cv.image(img, dx - 30, 0, cv.width + 60, cv.height)
    ctx.restore()


def _print(cv, img, cx, cy, a, pw, scale, note=None):
    """One print centred at (cx, cy), turned `a`, `scale`d; its photo cover-cropped square."""
    ph = pw * 1.2
    border = pw * 0.06
    ctx = cv.ctx
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(a)
    ctx.scale(scale, scale)
    x, y = -pw / 2, -ph / 2
    cv.rect(x, y, pw, ph, PAPER, radius=3)
    with cv.clip(x, y, pw, ph, 3):
        u.grain(cv, 0.35, seed=4, w=400, h=400)
    win = Box(x + border, y + border, pw - 2 * border, pw - 2 * border)
    u.cover_image(cv, img, win)
    cv.rect(*win, (255, 236, 200), alpha=0.07)  # a print's warm cast
    cv.outline(*win, (0, 0, 0), width=1, alpha=0.18)
    if note:
        f, lines = note
        margin = Box(win.x, win.bottom, win.w, y + ph - win.bottom)
        tw, th = text.block_size(lines, f)
        text.draw(cv, lines, f, margin.x + 4, margin.cy - th / 2, INK_NOTE)
    ctx.restore()


def _note_font(note, width, size0):
    for size in (size0, size0 * 0.88, size0 * 0.76, size0 * 0.66):
        f = kit.font(round(size), 700, tracking=-0.01)
        if text.measure(note, f) <= width:
            return f, (note,)
    return f, (note,)


def _label(cv, box, title, tape, k):
    """The torn paper label slapped into `box`, `k` frames after it lands."""
    if k < 0:
        return
    for size in (46, 42, 38, 34, 30, 26, 22):
        f, lines = u.fit_lines(title, box.w - 40, (size,), weight=850, max_lines=3)
        tw, th = text.block_size(lines, f)
        if tw <= box.w - 40 and th + 34 <= box.h:
            break
    lw, lh = tw + 40, th + 34
    if box.h < box.w:   # wide label area: sit at its left, centred vertically
        lx, ly = box.x, box.cy - lh / 2
    else:               # tall label area: low in it, above the table's light pool
        lx, ly = box.x, box.y + box.h * 0.55 - lh / 2
    cx, cy = lx + lw / 2, ly + lh / 2
    pts = paths.torn([(lx, ly), (lx + lw, ly), (lx + lw, ly + lh), (lx, ly + lh)], seed=17, amount=3.0)
    slam = {0: 1.16, 1: 1.08}.get(k, 1.0)  # slapped down on twos, like a stop-motion cut-out
    ctx = cv.ctx
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(math.radians(-2.0))
    ctx.scale(slam, slam)
    ctx.translate(-cx, -cy)
    cv.shape_shadow(pts, dx=3, dy=6, blur=10, color=(0, 0, 0, 0.5))
    u.poly(ctx, pts)
    u.fill(ctx, PAPER)
    with cv.clip(lx - 6, ly - 6, lw + 12, lh + 12):
        u.poly(ctx, pts)
        ctx.save()
        ctx.clip()
        u.grain(cv, 0.5, seed=6, w=300, h=200)
        ctx.restore()
    text.draw(cv, lines, f, lx + 20, ly + 17, LABEL_INK)
    if k >= 2:
        tape_pts = paths.torn([(-48, -13), (48, -13), (48, 13), (-48, 13)], seed=23, amount=1.6, step=2)
        ctx.save()
        ctx.translate(lx + lw * 0.78, ly + 2)
        ctx.rotate(math.radians(-14))
        u.poly(ctx, tape_pts)
        r, g, b, _ = vb.rgba(tape)
        u.fill(ctx, (r * 255, g * 255, b * 255, 0.78))
        ctx.restore()
    ctx.restore()
    cv.mark('title', *_aabb(cx, cy, lw * slam, lh * slam, math.radians(-2.0)))


def draw(cv, shot):
    data = shot.data
    imgs = list(data['images'])
    n = len(imgs)
    W, H = cv.width, cv.height
    cv.fill(TABLE)
    ctx = cv.ctx
    ctx.rectangle(0, 0, W, H)
    u.fill(ctx, u.radial(ctx, W * 0.6, H * 0.55, max(W, H) * 0.7, [(0, '#2a2f3a'), (1, (20, 22, 28, 0))]))
    u.grain(cv, 0.6, seed=2)

    R, T = _regions(W, H)
    spots = _spots(R, n)
    fpb = u.beat_frames(shot)
    interval = min(fpb, 0.45 * shot.length / n)
    for i, (img, (cx, cy, a, pw)) in enumerate(zip(imgs, spots)):
        d = shot.f - (-3 + i * interval)
        if d < 0:
            continue
        p = vb.spring_at(d, 30, **DROP)
        lift = max(0.0, 1 - p)
        rnd = random.Random(i)
        side = -1 if i % 2 else 1
        x = cx + side * 90 * lift
        y = cy - 140 * lift
        ang = a + math.radians(side * 16) * lift
        scale = 1 + 0.55 * (1 - p)
        ph = pw * 1.2
        corners = u.rotated_corners(x + 6 + 34 * lift, y + 10 + 60 * lift, pw * scale, ph * scale, ang)
        cv.shape_shadow(corners, blur=8 + 26 * lift + rnd.random(), color=(0, 0, 0, 0.55 - 0.3 * lift))
        note = None
        if i == n - 1 and data['note']:
            border = pw * 0.06
            note = _note_font(data['note'], pw - 2 * border - 8, pw * 0.085)
        with cv.layer(opacity=vb.clamp01(d / 3)):
            _print(cv, img, x, y, ang, pw, scale, note)
        cv.mark(f'print-{i}', *_aabb(x, y, pw * scale, ph * scale, ang))
        if note and d >= 3:
            border = pw * 0.06
            # the note's own box: the bottom margin, turned with the print
            my = -pw * 0.6 + pw - border
            mcx, mcy = 0, my + (pw * 1.2 / 2 - my) / 2
            ox = x + (mcx * math.cos(ang) - mcy * math.sin(ang)) * scale
            oy = y + (mcx * math.sin(ang) + mcy * math.cos(ang)) * scale
            cv.mark('note', *_aabb(ox, oy, (pw - 2 * border) * scale, pw * 0.16 * scale, ang))

    if data['title']:
        _label(cv, T, data['title'], data['tape'], round(shot.f - (-3 + n * interval)))

    drift = 24 * math.sin(shot.f / max(1, shot.length) * math.pi)
    _soft_light(cv, _light(W, H), dx=drift)


def _sample_images():
    return tuple(u.photo(k) for k in ('coast', 'harbor', 'fields', 'dunes'))


def _overlaps(n=5):
    pairs = [(f'print-{i}', f'print-{j}') for i in range(n) for j in range(i + 1, n)]
    return tuple(pairs + [('note', f'print-{i}') for i in range(n)])


COMPONENT = Component(
    id='photo-stack',
    kind='images',
    description='Instant-camera prints drop onto a dark table one per beat, landing on springs at slight '
                'angles under window light, with a note on the top print and a torn paper label taped down.',
    tags=('images', 'photos', 'polaroid', 'collage', 'paper', 'spring', 'memories'),
    formats=('16x9', '9x16', '1x1'),
    beats=(4, 8),
    slots=(
        Slot('images', 'images', True, 'The pictures, dropped in this order; the last lands on top.',
             min_count=2, max_count=5),
        Slot('title', 'text', False, 'Words on the torn paper label, like an album title.', max_length=28),
        Slot('note', 'text', False, 'A short note written on the top print\'s white margin.', max_length=22),
        Slot('tape', 'color', False, 'Colour of the tape holding the label down.'),
    ),
    sample={'images': _sample_images(), 'title': 'Summer, mostly outside', 'note': 'the long way home',
            'tape': kit.TEAL},
    draw=draw,
    overlap_ok=_overlaps(),
)
