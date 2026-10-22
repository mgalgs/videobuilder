"""Score bug: a compact scoreboard pinned in a corner of live footage -- team
names, scores, period and clock -- that wipes on at the start and, when a
score changes, rolls the new number in under a flash of the team's colour."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def draw_score_bug(cv, x, y, teams, scores, clock, period, reveal=1.0, previous=None, change=1.0,
                   size=1.0, panel='#0d0e12', ink=demo.INK, muted=demo.MUTED):
    """Draw a two-row score bug from its top-left (x, y). `teams` is a pair of
    `(name, color)`, `scores` the pair of current scores, `clock` and
    `period` the game-state strings in the right-hand cell. `reveal` (0 -> 1)
    wipes the panel on from the left with the rows following a beat behind;
    pass `previous` scores and a `change` progress (0 -> 1) to roll any score
    that differs up into its new value under a flash of the team colour.
    `size` scales the whole bug. Returns its Box."""
    s = size
    row_h, name_w, score_w, state_w, pad = 44 * s, 170 * s, 72 * s, 104 * s, 14 * s
    w, h = pad + name_w + score_w + state_w, 2 * row_h + 2 * pad
    nf, sf = demo.font(24 * s, 800), demo.mono(32 * s, 700)
    cf, pf = demo.mono(24 * s, 700), demo.font(16 * s, 800)
    wipe = vb.ease_out_expo(vb.clamp01(reveal / 0.7))
    if wipe <= 0:
        return vb.Box(x, y, w, h)
    cv.shadow(x, y, w * wipe, h, radius=10 * s, dy=6 * s, blur=20 * s, color=(0, 0, 0, 0.5))
    with cv.clip(x, y, w * wipe, h, 10 * s):
        cv.rect(x, y, w, h, panel, radius=10 * s, alpha=0.94)
        sx = x + pad + name_w
        cv.line(sx + score_w, y + pad, sx + score_w, y + h - pad, demo.LINE, width=2 * s)
        for i, ((name, color), score) in enumerate(zip(teams, scores)):
            ry = y + pad + i * row_h
            k = vb.ease_out_quint(vb.clamp01((reveal - 0.25 - 0.12 * i) / 0.5))
            old = previous[i] if previous is not None else score
            rolling = old != score and change < 1
            if old != score and 0 < change:   # the row flashes in the team colour, then fades back
                cv.rect(x, ry, w - state_w, row_h, color, alpha=0.55 * math.exp(-4 * change))
            with cv.layer(opacity=k, dx=-30 * s * (1 - k)):
                cv.rect(x, ry + 6 * s, 6 * s, row_h - 12 * s, color, radius=3 * s)
                th = vb.text.line_height(nf)
                vb.text.draw(cv, [name], nf, x + pad + 6 * s, ry + (row_h - th) / 2, ink)
                sh = vb.text.line_height(sf)
                with cv.clip(sx, ry, score_w, row_h):
                    t = vb.ease_out_back(vb.clamp01(change))   # old number leaves upward, new one rises in
                    shown = ((old, -t, ink), (score, 1 - t, color if rolling else ink)) if old != score \
                        else ((score, 0.0, ink),)
                    for value, off, c in shown:
                        txt = str(value)
                        tw = vb.text.measure(txt, sf)
                        vb.text.draw(cv, [txt], sf, sx + score_w - pad - tw, ry + (row_h - sh) / 2 + off * row_h, c)
        cx = sx + score_w + state_w / 2
        k = vb.ease_out_quint(vb.clamp01((reveal - 0.45) / 0.5))
        with cv.layer(opacity=k):
            for txt, f, color, cy in ((period, pf, muted, y + pad + row_h * 0.5),
                                      (clock, cf, ink, y + pad + row_h * 1.3)):
                tw, th = vb.text.block_size([txt], f)
                vb.text.draw(cv, [txt], f, cx - tw / 2, cy - th / 2, color)
    return vb.Box(x, y, w, h)


HOME, AWAY = ('LIONS', demo.ACCENT), ('HAWKS', demo.TEAL)


def _pitch(cv, n):
    """The 'live footage' under the bug: a court drawn in lines, players drifting."""
    cv.fill('#1b2a24')
    left, top, right, bottom = 70, 70, demo.W - 70, demo.H - 40
    cv.outline(left, top, right - left, bottom - top, '#3d5a4e', width=3)
    cv.line(demo.W / 2, top, demo.W / 2, bottom, '#3d5a4e', width=3)
    cv.arc(demo.W / 2, (top + bottom) / 2, 70, 0, 2 * math.pi, '#3d5a4e', width=3)
    t = n / demo.FPS
    for i in range(10):
        color = HOME[1] if i % 2 else AWAY[1]
        px = demo.W / 2 + 300 * math.sin(1.7 * i + 0.35 * t * (1 + i % 3)) + 40 * math.sin(t + i)
        py = (top + bottom) / 2 + 150 * math.cos(2.3 * i + 0.3 * t)
        demo.dot(cv, px, py, r=14, color=color, alpha=0.85)
    demo.dot(cv, demo.W / 2 + 120 * math.sin(1.3 * t), (top + bottom) / 2 + 60 * math.cos(2.1 * t), r=7,
             color=demo.INK)


def draw(n, cv):
    _pitch(cv, n)
    t = n / demo.FPS
    secs = 4 * 60 + 28 - int(t)                      # the game clock keeps running down
    box = draw_score_bug(cv, 28, 24, (HOME, AWAY), (43, 68), f'{secs // 60}:{secs % 60:02d}', 'Q3',
                         reveal=demo.phase(n, 0.2, 1.3), previous=(42, 68), change=demo.phase(n, 1.8, 2.5))
    cv.mark('score-bug', *box)


TECHNIQUE = Technique(
    id='score-bug',
    name='Score bug',
    family='broadcast',
    group='Sports graphics',
    aliases=('scorebug', 'score strip', 'scoreboard overlay'),
    definition='A small scoreboard tucked into a corner of the picture keeps the teams, score, period '
               'and clock on screen, sliding in at the start and flashing when a score changes.',
    phrasings=('put a little scoreboard in the corner like a TV sports broadcast',
               'show the teams and the score up top and have it update when someone scores',
               'a live game overlay with the score, quarter and time remaining'),
    related=('station-id-bug', 'camcorder-timecode-overlay', 'pop-on-captions', 'coachmark-spotlight-cutout',
             'breaking-news-banner-slam', 'screen-tearing'),
    api=('videobuilder.techniques.broadcast.score_bug.draw_score_bug',),
    demo=lambda: demo.film(draw),
)
