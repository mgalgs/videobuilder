"""End card with subscribe slot: the closing screen lays out panels for a
watch-next video, a channel badge with a subscribe button and a link bar,
each panel fading up into its place in turn."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def end_card_slots(box, header=90, gap=16, link=56, split=0.64):
    """The slot layout inside `box` as a dict of `vb.Box`es: `header` (title
    strip across the top), `video` (the large watch-next panel on the left),
    `subscribe` (the channel panel beside it) and `link` (a bar across the
    bottom). `split` is the video panel's share of the width."""
    x, y, w, h = box.x, box.y, box.w, box.h
    body_y = y + header
    body_h = h - header - gap - link
    vw = (w - gap) * split
    return {
        'header': vb.Box(x, y, w, header - gap),
        'video': vb.Box(x, body_y, vw, body_h),
        'subscribe': vb.Box(x + vw + gap, body_y, w - vw - gap, body_h),
        'link': vb.Box(x, y + h - link, w, link),
    }


def slot_reveal(p, i, count=4, overlap=0.5):
    """Eased 0 -> 1 progress of slot `i` of `count` at overall progress `p`:
    the slots start in turn, each overlapping the one before by `overlap`."""
    span = 1 / (count - (count - 1) * overlap)
    start = i * span * (1 - overlap)
    return vb.ease_out_quint(vb.clamp01((p - start) / span))


def _panel(cv, b, color, alpha):
    cv.shadow(b.x, b.y, b.w, b.h, radius=14, dy=8, blur=22, color=(0, 0, 0, 0.4 * alpha))
    cv.rect(b.x, b.y, b.w, b.h, color, radius=14)
    cv.outline(b.x, b.y, b.w, b.h, demo.LINE, width=1.5, radius=14)


def _play(cv, cx, cy, r, color):
    demo.dot(cv, cx, cy, r, demo.INK, alpha=0.92)
    c = cv.ctx
    c.new_path()
    c.move_to(cx - r * 0.3, cy - r * 0.45)
    c.line_to(cx + r * 0.5, cy)
    c.line_to(cx - r * 0.3, cy + r * 0.45)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color))
    c.fill()


def draw_end_card(cv, box, p, title='Thanks for watching', subtitle='Thanks for sticking around.',
                  video_title='Watch this next', channel='Your channel', action='SUBSCRIBE', link_text='See the whole series',
                  thumbnail=None, panel='#1d1f26', accent=demo.ACCENT, rise=24):
    """Draw the end card into `box` at progress `p` (0 -> 1): the header, the
    watch-next panel (with `thumbnail`, an image, if given), the subscribe
    panel and the link bar fade up and settle in that order. Returns the slot
    boxes from `end_card_slots`, so a film can lay real content over them."""
    s = end_card_slots(box)
    tf = demo.font(44, 850)
    sub = demo.font(18, 500)
    small = demo.mono(12, 700)

    a = slot_reveal(p, 0)
    if a > 0:
        h = s['header']
        with cv.layer(opacity=a, dy=(1 - a) * rise):
            vb.text.draw(cv, [title], tf, h.x, h.y, demo.INK)
            vb.text.draw(cv, [subtitle], sub, h.x + 2, h.y + 52, demo.MUTED)
        cv.mark('header', *h)

    a = slot_reveal(p, 1)
    if a > 0:
        b = s['video']
        with cv.layer(opacity=a, dy=(1 - a) * rise):
            _panel(cv, b, panel, a)
            th = vb.Box(b.x + 12, b.y + 12, b.w - 24, b.h - 84)
            with cv.clip(*th, radius=8):
                if thumbnail is not None:
                    cv.image(thumbnail, *th.cover(thumbnail.w, thumbnail.h))
                else:
                    cv.rect(*th, demo.LINE)
            _play(cv, th.x + th.w / 2, th.y + th.h / 2, 26, panel)
            vb.text.draw(cv, ['WATCH NEXT'], small, th.x + 4, th.y + th.h + 14, demo.TEAL)
            vb.text.draw(cv, [video_title], demo.font(22, 700), th.x + 4, th.y + th.h + 32, demo.INK)
        cv.mark('video', *b)

    a = slot_reveal(p, 2)
    if a > 0:
        b = s['subscribe']
        cx = b.x + b.w / 2
        with cv.layer(opacity=a, dy=(1 - a) * rise):
            _panel(cv, b, panel, a)
            r = min(46, b.w * 0.2)
            cy = b.y + b.h * 0.3
            demo.dot(cv, cx, cy, r, demo.TEAL)
            demo.word(cv, channel[:1].upper(), cx, cy, size=round(r * 1.1), color=demo.BG, weight=900)
            demo.word(cv, channel, cx, cy + r + 26, size=20, weight=700)
            bw, bh = b.w * 0.7, 44
            by = b.y + b.h * 0.72
            cv.rect(cx - bw / 2, by, bw, bh, accent, radius=bh / 2)
            demo.word(cv, action, cx, by + bh / 2, size=16, weight=800, font=demo.mono(16, 800))
        cv.mark('subscribe', *b)

    a = slot_reveal(p, 3)
    if a > 0:
        b = s['link']
        with cv.layer(opacity=a, dy=(1 - a) * rise):
            _panel(cv, b, panel, a)
            f = demo.font(19, 600)
            _, lh = vb.text.block_size([link_text], f)
            vb.text.draw(cv, [link_text], f, b.x + 22, b.y + (b.h - lh) / 2, demo.INK)
            ax, ay = b.x + b.w - 34, b.y + b.h / 2
            cv.line(ax - 8, ay - 9, ax + 1, ay, demo.TEAL, width=3)
            cv.line(ax + 1, ay, ax - 8, ay + 9, demo.TEAL, width=3)
        cv.mark('link', *b)
    return s


def draw(n, cv):
    cv.fill(demo.BG)
    box = vb.Box(96, 52, demo.W - 192, demo.H - 104)
    s = draw_end_card(cv, box, demo.phase(n, 0.2, 1.9), thumbnail=demo.photo(), channel='Motion Lab')
    # Once everything has landed, a soft ring pulses around the subscribe button.
    q = demo.phase(n, 2.1, 2.9)
    if 0 < q < 1:
        b = s['subscribe']
        bw, bh = b.w * 0.7, 44
        g = 10 * math.sin(math.pi * q)
        cv.outline(b.x + b.w / 2 - bw / 2 - g, b.y + b.h * 0.72 - g, bw + 2 * g, bh + 2 * g,
                   demo.ACCENT, width=2.5, radius=bh / 2 + g, alpha=1 - q)


TECHNIQUE = Technique(
    id='end-card-with-subscribe-slot',
    name='End card with subscribe slot',
    family='broadcast',
    group='End cards',
    aliases=('end screen', 'outro card'),
    definition='The last screen of a video settles into a tidy grid of panels, one for the next video '
               'to watch, one with a subscribe button and one for a link, each fading in after the last.',
    phrasings=('finish with an end screen that points to another video and asks people to subscribe',
               'an outro card with a watch-next box, a subscribe button and a link',
               'lay out the closing slots for a recommended video and a subscribe prompt'),
    related=('stacked-card-reveal', 'sticky-card-stack-on-scroll', 'title-card-reveal',
             'broadcast-title-card-stinger', 'card-deck-fan', 'swipe-to-dismiss'),
    api=('videobuilder.techniques.broadcast.end_card_with_subscribe_slot.draw_end_card',
         'videobuilder.techniques.broadcast.end_card_with_subscribe_slot.end_card_slots',
         'videobuilder.techniques.broadcast.end_card_with_subscribe_slot.slot_reveal'),
    demo=lambda: demo.film(draw),
)
