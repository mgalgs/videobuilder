"""Ending: end card. A closing headline and up to two supporting lines settle
in around a small turning accent mark -- the resting state a film comes back
to, so a loop's last frame can match its first.

Ported and generalised from the end card in `examples/showcase.py` (`end`),
with the brand mark replaced by a generic turning ring.
"""
import math

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot

ORBIT = 60  # frames per turn of the mark


def _mark(cv, cx, cy, r, spin, color):
    cv.arc(cx, cy, r * 0.8, 0, 2 * math.pi, kit.TEAL, width=r * 0.3)
    cv.rect(cx - r * 0.4, cy - r * 0.4, r * 0.8, r * 0.8, color, radius=r * 0.4)
    mx, my = cx + r * 0.8 * math.cos(spin), cy + r * 0.8 * math.sin(spin)
    cv.rect(mx - r * 0.1, my - r * 0.1, r * 0.2, r * 0.2, kit.INK, radius=r * 0.1)


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    s = kit.safe(cv)
    big = kit.font(44, 800, tracking=-0.015)
    body = kit.font(22, 500)
    lines1 = text.wrap(data['headline'], big, s.w, balance=True)
    w1, h1 = text.block_size(lines1, big)
    extra = [t for t in (data.get('line2'), data.get('line3')) if t]
    extra_sizes = [text.block_size(text.wrap(t, body, s.w, balance=True), body) for t in extra]

    r = 36
    gap = 24
    block_h = 2 * r + gap + h1 + sum(h + 10 for _, h in extra_sizes)
    top = s.cy - block_h / 2

    spin = 2 * math.pi * (shot.f % ORBIT) / ORBIT
    cx, cy = s.cx, top + r
    p = vb.clamp01(vb.spring_at(shot.f - 2, 30, **vb.damped(0.5, hz=2.6)))
    scale = max(0.001, p)
    with cv.layer(dx=cx * (1 - scale), dy=cy * (1 - scale), scale=scale):
        _mark(cv, cx, cy, r, spin, data['accent'])
    cv.mark('mark', cx - r, cy - r, 2 * r, 2 * r)

    y = top + 2 * r + gap
    q = vb.clamp01(vb.spring_at(shot.f - 3, 30, **vb.damped(0.6)))
    with cv.layer(opacity=q, dy=(1 - q) * 20):
        text.draw(cv, lines1, big, s.cx - w1 / 2, y, kit.INK, align='center', width=w1)
    cv.mark('headline', s.cx - w1 / 2, y, w1, h1)
    y += h1 + 10
    for i, (t, (w, h)) in enumerate(zip(extra, extra_sizes)):
        a = vb.clamp01(vb.interpolate(shot.f, [(i + 1) * 10, (i + 1) * 10 + 14], [0, 1], ease=vb.ease_out_expo))
        with cv.layer(opacity=a, dy=(1 - a) * 14):
            lines = text.wrap(t, body, s.w, balance=True)
            color = kit.MUTED if i == 0 else kit.INK
            text.draw(cv, lines, body, s.cx - w / 2, y, color, align='center', width=w)
        cv.mark(f'line-{i + 1}', s.cx - w / 2, y, w, h)
        y += h + 10


COMPONENT = Component(
    id='end-card',
    kind='ending',
    description='A closing headline and up to two supporting lines settle around a small turning accent mark.',
    tags=('ending', 'end card', 'outro'),
    formats=('16x9', '9x16', '1x1'),
    beats=(3, 6),
    slots=(
        Slot('headline', 'text', True, 'The closing line, e.g. "Thanks for watching".', max_length=40),
        Slot('line2', 'text', False, 'A supporting line under the headline.', max_length=60),
        Slot('line3', 'text', False, 'A second supporting line.', max_length=60),
        Slot('accent', 'color', False, 'Colour of the accent mark.'),
    ),
    sample={'headline': 'Made with videobuilder', 'line2': 'Every shot here is a component.',
           'line3': 'Pick one for your next scene.', 'accent': kit.ACCENT},
    draw=draw,
)
