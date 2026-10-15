"""Images: image showcase. One picture shown two ways at once: cover-cropped
into a rounded card with a soft drop shadow, and contain-fitted inside a
bordered card -- the box-model moves for putting a picture in a layout.

Ported and generalised from `examples/capabilities/image-treatments.py`.
"""
import videobuilder as vb
from videobuilder import Box, fr, text

from .. import kit
from ..schema import Component, Slot

ENTER = 16
STAGGER = 8

PANELS = ('cover', 'contain')


def _panel_p(i, n):
    enter_n = n - i * STAGGER
    if enter_n < 0:
        return 0.0
    if enter_n < ENTER:
        return vb.interpolate(enter_n, [0, ENTER], [0, 1], ease=vb.ease_out_quint)
    return 1.0


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    img = data['image']
    s = kit.safe(cv)
    caption = data.get('caption') or ''
    has_caption = bool(caption)
    caption_f = kit.font(16, 600)
    caption_h = text.block_size([caption or ' '], caption_f)[1] if has_caption else 0
    top = s.y
    content = Box(s.x, top, s.w, s.h)
    cols = content.row(fr, fr, gap=24)
    card_size = min(cols[0].w, content.h - (caption_h + 12 if has_caption else 0))
    top = content.y + (content.h - (card_size + (caption_h + 12 if has_caption else 0))) / 2

    for i, (col, mode) in enumerate(zip(cols, PANELS)):
        p = _panel_p(i, shot.f)
        if p <= 0.0:
            continue
        card = Box(col.cx - card_size / 2, top, card_size, card_size)
        with cv.layer(opacity=p, dy=(1 - p) * 30):
            if mode == 'cover':
                cv.shadow(*card, radius=18, dy=12, blur=26, color=(0, 0, 0, 0.5))
                with cv.clip(*card, radius=18):
                    cv.image(img, *card.cover(img.w, img.h))
            else:
                cv.rect(*card, kit.LINE, radius=18)
                cv.image(img, *card.contain(img.w, img.h))
                cv.outline(*card, kit.MUTED, width=2, radius=18)
            cv.mark(f'panel-{i}', *card)
            if has_caption:
                box = text.draw(cv, [caption], caption_f, card.x, card.bottom + 12, kit.MUTED,
                                align='center', width=card.w)
                cv.mark(f'caption-{i}', *box)


COMPONENT = Component(
    id='image-showcase',
    kind='images',
    description='One picture shown two ways at once: cover-cropped with a soft shadow, and contain-fitted in a bordered card.',
    tags=('images', 'photo', 'treatment'),
    formats=('16x9', '9x16', '1x1'),
    beats=(2, 5),
    slots=(
        Slot('image', 'image', True, 'The picture shown in both panels.'),
        Slot('caption', 'text', False, 'A short caption under each panel.', max_length=40),
    ),
    sample={'image': kit.sample_photo(), 'caption': 'Product shot'},
    draw=draw,
)
