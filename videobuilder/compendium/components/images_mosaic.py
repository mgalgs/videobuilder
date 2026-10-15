"""Images: photo mosaic. Three to six pictures tile the frame in a tight
grid, each wiped in behind a block of accent colour on the half-beat in a
diagonal sweep; then, on a beat, one of them grows to take the whole frame
while the rest dim under it, and a big headline pops in over it word by word.

The grid is laid out per format and per count: an odd count gets one feature
tile (a tall one on the left in 16:9 and 1:1, a wide one on top in 9:16),
an even count an even grid, two rows in 16:9 and two columns in 9:16.
"""
import math

import videobuilder as vb
from videobuilder import Box, fr, text

from .. import kit
from ..schema import Component, Slot
from . import _images_util as u

GAP = 8
RADIUS = 8
BLOCK_IN = 8    # frames for the colour block to wipe across a tile
IMAGE_IN = 12   # frames for the picture to wipe in over it
WORD_STAGGER = 2
POPPY = vb.damped(0.5, hz=2.6)


def cells(box, n):
    """`n` tiles in `box`, row-major, laid out for its shape."""
    landscape = box.w >= box.h * 0.95
    if n % 2 == 0:
        k = n // 2
        return box.grid(k, 2, gap=GAP) if landscape else box.grid(2, k, gap=GAP)
    k = (n - 1) // 2
    if landscape:
        feat, rest = box.row(1.2 * fr, k * fr, gap=GAP)
        return [feat] + rest.grid(k, 2, gap=GAP)
    feat, rest = box.column(1.1 * fr, k * fr, gap=GAP)
    return [feat] + rest.grid(2, k, gap=GAP)


def _lerp_box(a, b, t):
    return Box(*(x + (y - x) * t for x, y in zip(a, b)))


def _timing(shot, n):
    """(tile start frames by tile, grow start, grow length) for this shot."""
    fpb = u.beat_frames(shot)
    L = shot.length
    stagger = min(fpb / 2, 0.22 * L / n)
    starts = [-4 + i * stagger for i in range(n)]
    intro_end = starts[-1] + BLOCK_IN + 4
    grow_at = math.floor(0.42 * L / fpb) * fpb
    if grow_at < intro_end:
        grow_at = math.ceil(intro_end / fpb) * fpb
    return starts, grow_at, max(10.0, min(fpb, 0.12 * L))


def _tile(cv, img, cell, d, accent, horizontal, breathe):
    """One tile `d` frames into its entrance: an accent block wipes across, then the picture over it."""
    b = vb.ease_out_expo(vb.clamp01(d / BLOCK_IN))
    p = vb.ease_out_expo(vb.clamp01((d - 4) / IMAGE_IN))
    if b <= 0:
        return
    with cv.clip(*cell, RADIUS):
        if p < 1:
            if horizontal:
                cv.rect(cell.x, cell.y, cell.w * b, cell.h, accent)
            else:
                cv.rect(cell.x, cell.y, cell.w, cell.h * b, accent)
        if p > 0:
            win = Box(cell.x, cell.y, cell.w * p, cell.h) if horizontal else Box(cell.x, cell.y, cell.w, cell.h * p)
            with cv.clip(*win):
                u.cover_image(cv, img, cell, zoom=1.0 + 0.22 * (1 - p) + breathe)


def _headline(cv, frame, data, k, accent):
    """The headline over the grown picture, `k` frames after it lands. Returns marks drawn."""
    title, kicker = data['title'], data['kicker']
    if not (title or kicker) or k < 0:
        return
    W, H = frame.w, frame.h
    m = 44 if W >= H else 36
    width = min(W - 2 * m, 700)
    ctx = cv.ctx
    # a scrim, so the type reads over any picture
    ctx.rectangle(0, H * 0.35, W, H * 0.65)
    u.fill(ctx, u.linear(ctx, 0, H * 0.35, 0, H, [(0, (10, 11, 14, 0)), (1, (10, 11, 14, 0.82))]))
    tall = H > W * 1.2
    bottom = H * (0.84 if tall else 1.0) - m
    sizes = (64, 56, 50, 44, 38) if W >= H else (58, 52, 46, 40, 36)
    title_f, lines = u.fit_lines(title, width, sizes, weight=850, max_lines=3) if title else (None, ())
    kick_f = kit.mono(16, 600, tracking=0.18)
    kick_h = text.line_height(kick_f) if kicker else 0
    title_h = text.block_size(lines, title_f)[1] if lines else 0
    y = bottom - title_h - (kick_h + 14 if kicker else 0)
    if kicker:
        q = vb.clamp01(k / 8)
        rule = 40 * vb.ease_out_expo(q)
        cv.rect(m, y + kick_h / 2 - 2, rule, 4, accent)
        box = text.draw(cv, [kicker.upper()], kick_f, m + 54, y, kit.INK, alpha=q)
        cv.mark('kicker', m, y, box.right - m, kick_h)
        y += kick_h + 14
    if not lines:
        return
    lh = text.line_height(title_f)
    word_i = 0
    for li, ln in enumerate(lines):
        words = ln.split(' ')
        for j, word in enumerate(words):
            x = m + (text.measure(' '.join(words[:j]) + ' ', title_f) if j else 0)
            ww = text.measure(word, title_f)
            s = vb.spring_at(k - 4 - word_i * WORD_STAGGER, 30, **POPPY)
            if s > 0.001:
                cx, cy = x + ww / 2, y + li * lh + lh / 2
                with cv.layer(opacity=min(1.0, s * 2), dx=cx * (1 - s), dy=cy * (1 - s) + (1 - s) * 18, scale=s):
                    text.draw(cv, [word], title_f, x, y + li * lh, kit.INK)
            word_i += 1
    w, h = text.block_size(lines, title_f)
    if k >= 4:
        cv.mark('title', m, y, w, h)


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    imgs = list(data['images'])
    accent = data['accent']
    n = len(imgs)
    frame = Box.of(cv)
    grid = frame.pad(20 if cv.width >= cv.height else 24)
    tiles = cells(grid, n)
    hero = int(data['hero'] or 1)
    hero = min(n, max(1, hero)) - 1
    starts, grow_at, grow_len = _timing(shot, n)
    order = sorted(range(n), key=lambda i: (tiles[i].x + tiles[i].y, tiles[i].y))
    start_of = {i: starts[r] for r, i in enumerate(order)}
    g = vb.ease_in_out_quart(vb.clamp01((shot.f - grow_at) / grow_len))
    breathe = 0.03 * vb.clamp01(shot.f / max(1, shot.length))

    for i in range(n):
        if i == hero and g > 0:
            continue
        d = shot.f - start_of[i]
        _tile(cv, imgs[i], tiles[i], d, accent, horizontal=(order.index(i) % 2 == 0), breathe=breathe)
        if g <= 0 and d >= 0:
            cv.mark(f'tile-{i}', *tiles[i])
    if g > 0:
        cv.rect(*frame, kit.BG, alpha=0.6 * g)
        box = _lerp_box(tiles[hero], frame, g)
        cv.shadow(*box, radius=RADIUS * (1 - g), dy=10 * (1 - g), blur=30, color=(0, 0, 0, 0.5 * (1 - g)))
        u.cover_image(cv, imgs[hero], box, zoom=1.0 + breathe + 0.04 * g, radius=RADIUS * (1 - g))
        cv.mark('hero', *box)
        _headline(cv, frame, data, shot.f - (grow_at + grow_len), accent)


def _sample_images():
    return tuple(u.photo(k) for k in ('forest', 'dunes', 'harbor', 'fields', 'poster'))


COMPONENT = Component(
    id='photo-mosaic',
    kind='images',
    description='Three to six pictures wipe into a tight grid on the half-beat, then one grows to fill '
                'the frame and a big headline pops in over it word by word.',
    tags=('images', 'gallery', 'grid', 'mosaic', 'reveal', 'beat'),
    formats=('16x9', '9x16', '1x1'),
    beats=(6, 10),
    slots=(
        Slot('images', 'images', True, 'The pictures in the grid, in order.', min_count=3, max_count=6),
        Slot('hero', 'number', False, 'Which picture grows to fill the frame, counting from 1 (default 1).'),
        Slot('title', 'text', False, 'Headline over the grown picture.', max_length=40),
        Slot('kicker', 'text', False, 'A short label above the headline.', max_length=24),
        Slot('accent', 'color', False, 'Colour of the blocks the pictures wipe in over, and the kicker rule.'),
    ),
    sample={'images': _sample_images(), 'hero': 2, 'title': 'Five places worth the long way round',
            'kicker': 'Field notes', 'accent': kit.ACCENT},
    draw=draw,
    overlap_ok=(('hero', 'title'), ('hero', 'kicker')),
)
