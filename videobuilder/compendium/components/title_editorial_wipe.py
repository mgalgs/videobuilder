"""Title: editorial wipe. A magazine-cover title on warm newsprint: heavy
uppercase type stacked tight and set as big as the frame allows, each line
revealed by a solid colour block that sweeps across it and peels away,
staggered on half beats. A halftone colour plate fills the space the type
leaves (the top of a tall frame, a band in a wide one), and an optional
kicker sits over a hairline rule that draws across first.

The type is fitted per format (wide: two or three long lines; tall: a word
or two a line, much bigger), so 9:16 is a poster, not a letterbox.
"""
import math

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot
from ._title_util import fit, frames_per_beat, grain

PAPER = '#efebe2'
PRINT = '#16171b'
SIZES = tuple(range(200, 39, -4))
PAD = 40
KICK_F = kit.font(20, 700, tracking=0.14)


def _title_font(size):
    return kit.font(size, 900, tracking=-0.035, line_height=0.86)


def _layout(cv, has_kicker):
    """(safe box, the kicker's height, the most height the title may take)."""
    s = vb.Box.of(cv).pad(PAD)
    tall = cv.height > cv.width * 1.2
    kick_h = text.line_height(KICK_F) + 18 if has_kicker else 0
    # The type may take up to this much of the height; the plate gets the rest.
    share = 0.62 if tall else 0.7
    return s, kick_h, s.h * share - (0 if tall else kick_h * 0.5)


def draw(cv, shot):
    data = shot.data
    accent = data['accent']
    fpb = frames_per_beat(shot)
    n = shot.f
    cv.fill(PAPER)
    grain(cv, 0.35, seed=4)

    title = data['title'].upper()
    kicker = data['kicker'].upper()
    s, kick_h, max_title_h = _layout(cv, bool(kicker))
    f, lines = fit(title, _title_font, s.w, max_title_h, SIZES)
    lh = text.line_height(f)
    block_h = lh * len(lines)
    title_top = s.bottom - block_h

    # ---- the kicker: a rule that draws across, the words settling over it ----
    rule_y = s.y + kick_h - 8 if kicker else s.y
    rule_t = vb.ease_in_out_quart(vb.clamp01(n / (fpb * 1.0)))
    if rule_t > 0:
        cv.line(s.x, rule_y, s.x + s.w * rule_t, rule_y, PRINT, width=2)
    if kicker:
        k = vb.clamp01(vb.spring_at(n - fpb * 0.5, 30, **vb.damped(0.8, hz=3.0)))
        kf = next((ff for ff in (kit.font(sz, 700, tracking=0.14) for sz in range(20, 11, -1))
                   if text.measure(kicker, ff) <= s.w - 24), kit.font(12, 700, tracking=0.04))
        ky = s.y + (1 - k) * 10 + (text.line_height(KICK_F) - text.line_height(kf)) / 2
        with cv.layer(opacity=k):
            cv.rect(s.x, ky + text.line_height(kf) / 2 - 6, 12, 12, accent)
            box = text.draw(cv, [kicker], kf, s.x + 22, ky, PRINT)
        if k > 0.01:
            cv.mark('kicker', box.x - 22, box.y, box.w + 22, box.h)

    # ---- the plate: a halftone colour field in whatever room the type leaves ----
    plate_top = rule_y + 18
    plate_bot = title_top - 22
    if plate_bot - plate_top > 48:
        p = vb.ease_in_out_quart(vb.clamp01((n - fpb * 0.25) / (fpb * 0.75)))
        if p > 0:
            pw = s.w * p
            cv.rect(s.x, plate_top, pw, plate_bot - plate_top, accent)
            # A halftone ramp: the dots swell band by band toward the far edge,
            # like ink pooling across a print, and drift slowly so it isn't a still.
            bands = 7
            ctx = cv.ctx
            for b in range(bands):
                x0 = s.x + s.w * b / bands
                bw = min(s.w / bands + 0.5, s.x + pw - x0)
                if bw <= 0:
                    break
                with cv.clip(x0, plate_top, bw, plate_bot - plate_top):
                    ctx.save()
                    ctx.translate(-n * 0.25, 0)
                    ctx.set_source(vb.halftone_pattern(8, 0.6 + 2.9 * b / (bands - 1), math.radians(30),
                                                       (0, 0, 0, 0.17)))
                    ctx.paint()
                    ctx.restore()

    # ---- the title: one block per line sweeps on, the type is there as it peels off ----
    stagger, cover, peel = fpb * 0.25, fpb * 0.4, fpb * 0.45
    start0 = fpb * 0.75
    for i, line in enumerate(lines):
        y = title_top + i * lh
        w = text.measure(line, f)
        bx, bw = s.x - 6, w + 12
        t = n - start0 - i * stagger
        if t <= 0:
            continue
        if t >= cover:
            q = vb.ease_out_quint(vb.clamp01((t - cover) / (peel * 1.6)))
            box = text.draw(cv, [line], f, s.x - (1 - q) * 18, y, PRINT)
            cv.mark(f'title-{i}', box.x, box.y, box.w, box.h)
        if t < cover:
            a = vb.ease_in_out_quart(t / cover)
            cv.rect(bx, y + lh * 0.06, bw * a, lh * 0.88, accent)
        elif t < cover + peel:
            a = vb.ease_in_out_quart((t - cover) / peel)
            cv.rect(bx + bw * a, y + lh * 0.06, bw * (1 - a), lh * 0.88, accent)


COMPONENT = Component(
    id='editorial-wipe-title',
    kind='title',
    description=('A magazine-cover title on warm newsprint: huge stacked uppercase type, each line revealed by a '
                 'colour block that sweeps across and peels away, over a halftone colour plate, with an optional '
                 'kicker on a ruled line.'),
    tags=('title', 'editorial', 'magazine', 'wipe', 'print', 'halftone', 'poster'),
    formats=('16x9', '9x16', '1x1'),
    beats=(3, 6),
    slots=(
        Slot('title', 'text', True, 'The headline, two to five short words; set in capitals, as big as fits.',
             max_length=28),
        Slot('kicker', 'text', False, 'A small line above the headline: a section name, a date or a series.',
             max_length=32),
        Slot('accent', 'color', False, 'The wipe block and colour plate; a strong colour that sits on cream paper.'),
    ),
    sample={'title': 'Make less, mean more', 'kicker': 'Field notes · Issue twelve', 'accent': kit.ACCENT},
    draw=draw,
)
