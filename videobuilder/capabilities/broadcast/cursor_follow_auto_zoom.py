"""Cursor-follow auto zoom: a screen capture eases in close around the
pointer when it is about to click, glides along behind it while it moves
on, and pulls back out to the whole screen once the clicking is done."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ..ui.cursor_state_change import draw_cursor


def zoom_amount(t, clicks, lead=0.5, hold=0.45, ramp=0.5):
    """How zoomed in the camera is at time `t` seconds, 0 -> 1, given the
    click times `clicks`. Each click keeps the camera in from `lead` before
    it to `hold` after it; clicks whose spans overlap merge into one stay,
    so a quick run of clicks doesn't bob in and out. The zoom eases in over
    `ramp` from the start of a span and back out over `ramp` after its end."""
    spans = []
    for c in sorted(clicks):
        a, b = c - lead, c + hold
        if spans and a <= spans[-1][1] + ramp:
            spans[-1][1] = max(spans[-1][1], b)
        else:
            spans.append([a, b])
    amount = 0.0
    for a, b in spans:
        if t < a or t > b + ramp:
            continue
        rise = vb.ease_in_out_quart((t - a) / ramp)
        fall = 1 - vb.ease_in_out_quart((t - b) / ramp) if t > b else 1.0
        amount = max(amount, min(rise, fall))
    return amount


def follow(cursor, t, lag=0.18, step=1 / 60, window=4.0):
    """Where the camera aims at time `t`: the pointer path `cursor(t) ->
    (x, y)` smoothed by an exponential lag of `lag` seconds (sampled back
    over `window` lags), so the frame trails the pointer instead of
    jittering with it. Stateless, so any frame renders on its own."""
    if lag <= 0:
        return cursor(t)
    sx = sy = total = 0.0
    for i in range(int(window * lag / step) + 1):
        w = math.exp(-i * step / lag)
        x, y = cursor(max(0.0, t - i * step))
        sx, sy, total = sx + w * x, sy + w * y, total + w
    return sx / total, sy / total


def auto_zoom_camera(t, cursor, clicks, width, height, zoom=2.2, lag=0.18, **timing):
    """The camera at time `t`: `(cx, cy, scale)`, the screen point at the
    middle of the frame and the magnification. The scale runs from 1 to
    `zoom` (evenly in log space) by `zoom_amount(t, clicks, **timing)`; the
    aim follows the pointer with `lag`, clamped so the view never leaves the
    `width` x `height` screen (at scale 1 that pins it to the centre)."""
    s = vb.log_lerp(1.0, zoom, zoom_amount(t, clicks, **timing))
    x, y = follow(cursor, t, lag)
    hw, hh = width / (2 * s), height / (2 * s)
    return min(max(x, hw), width - hw), min(max(y, hh), height - hh), s


def cursor_follow_auto_zoom(cv, screen, t, cursor, clicks, zoom=2.2, lag=0.18, **timing):
    """Draw `screen(cv)` (a full-frame screen capture, pointer and all, in
    frame px) through the auto-zoom camera at time `t` seconds: pushed in
    around `cursor(t) -> (x, y)` while near any time in `clicks`, panning
    after it, and fully out otherwise. Returns `(cx, cy, scale)`.

    In a film, wrap the recording's draw call, e.g.
    `cursor_follow_auto_zoom(cv, lambda c: recording(c, n), n / fps, pointer_at, click_times)`."""
    w, h = cv.width, cv.height
    cx, cy, s = auto_zoom_camera(t, cursor, clicks, w, h, zoom, lag, **timing)
    with cv.layer(dx=w / 2 - cx * s, dy=h / 2 - cy * s, scale=s):
        screen(cv)
    return cx, cy, s


# --- demo: a small photo-editor screen; the pointer clicks a thumbnail, then a slider.

W, H = demo.W, demo.H
CLICKS = (1.1, 2.1)
SECONDS = 3.4
WIN = vb.Box(60, 40, W - 120, H - 80)
STAGE = vb.Box(WIN.x + 70, WIN.y + 70, 560, 290)
THUMBS = [vb.Box(STAGE.x + i * 142, STAGE.y + 310, 128, 70) for i in range(4)]
PANEL_X = WIN.x + WIN.w - 190
SLIDERS = [WIN.y + 120 + i * 80 for i in range(3)]
PICK = 1   # the thumbnail clicked


def _knob(t):
    """The second slider's knob position, 0 -> 1: dragged right after its click."""
    return 0.45 + 0.3 * vb.ease_in_out_quart(vb.clamp01((t - CLICKS[1]) / 0.35))


def _pointer(t):
    """The pointer path: in to the thumbnail, click, across to the slider knob, click and drag."""
    thumb = THUMBS[PICK].x + 74, THUMBS[PICK].y + 44
    knob = PANEL_X + 20 + 150 * 0.45, SLIDERS[1] + 30
    keys = ((0.0, (W * 0.62, H * 0.42)), (0.95, thumb), (1.3, thumb), (1.95, knob))
    if t >= CLICKS[1]:
        return PANEL_X + 20 + 150 * _knob(t), knob[1]
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            e = vb.ease_in_out_quart((t - t0) / (t1 - t0))
            return a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e
    return keys[-1][1]


def _landscape(cv, box):
    with cv.clip(*box, radius=8):
        cv.fill('#6a74c9')
        cv.sector(box.x + box.w * 0.72, box.y + box.h * 0.32, box.h * 0.14, 0, 2 * math.pi, '#f2b33d')
        for k, (col, y) in enumerate((('#4d5598', 0.58), ('#3a4074', 0.72), ('#272b4c', 0.86))):
            pts = [(box.x + box.w * i / 16, box.y + box.h * (y + 0.06 * math.sin(i * 0.7 + k * 1.9)))
                   for i in range(17)]
            pts += [(box.x + box.w, box.y + box.h), (box.x, box.y + box.h)]
            vb.paths.draw(cv, pts, col, closed=True, fill=True)


def _screen(cv, t):
    """The screen capture at time `t`: the app window and the pointer on it."""
    cv.fill('#0c0d10')
    cv.rect(*WIN, '#1b1d23', radius=14)
    cv.rect(WIN.x, WIN.y, WIN.w, 40, '#22252c', radius=14)
    demo.word(cv, 'Fieldnotes', WIN.x + 74, WIN.y + 20, size=15, weight=700)
    demo.word(cv, 'Landscape / 08', WIN.x + 300, WIN.y + 20, size=12, color=demo.MUTED, weight=500)
    cv.rect(WIN.x + WIN.w - 84, WIN.y + 8, 68, 24, '#7a83f0', radius=6)
    demo.word(cv, 'Save', WIN.x + WIN.w - 50, WIN.y + 20, size=12, color=demo.BG, weight=700)
    for i in range(5):
        cv.outline(WIN.x + 18, WIN.y + 70 + i * 40, 18, 18, demo.MUTED, width=1.5, radius=4, alpha=0.7)
    _landscape(cv, STAGE)
    picked = t >= CLICKS[0]
    for i, b in enumerate(THUMBS):
        _landscape(cv, b)
        if i == PICK and picked:
            cv.outline(b.x - 3, b.y - 3, b.w + 6, b.h + 6, '#e0b23b', width=2.5, radius=10)
    cv.line(PANEL_X - 20, WIN.y + 40, PANEL_X - 20, WIN.y + WIN.h, demo.LINE, width=1.5)
    demo.word(cv, 'Adjust', PANEL_X + 34, WIN.y + 78, size=15, weight=700)
    for i, (label, y) in enumerate(zip(('Exposure', 'Contrast', 'Warmth'), SLIDERS)):
        v = _knob(t) if i == 1 else 0.45
        demo.word(cv, label, PANEL_X + 20 + len(label) * 3.6, y + 6, size=12, color=demo.MUTED, weight=500)
        demo.word(cv, f'{round((v - 0.45) * 100):+d}' if i == 1 else '0', PANEL_X + 160, y + 6, size=12,
                  weight=600)
        cv.rect(PANEL_X + 20, y + 28, 150, 4, demo.LINE, radius=2)
        cv.rect(PANEL_X + 20, y + 28, 150 * v, 4, '#7a83f0', radius=2)
        demo.dot(cv, PANEL_X + 20 + 150 * v, y + 30, r=7, color=demo.INK)
    x, y = _pointer(t)
    for c in CLICKS:   # a ring spreading from each click
        q = (t - c) / 0.45
        if 0 <= q <= 1:
            cv.arc(x, y, 6 + 22 * vb.ease_out_expo(q), 0, 2 * math.pi, demo.INK, width=2, alpha=1 - q)
    draw_cursor(cv, x, y, 0.0, size=0.8)


def draw(n, cv):
    t = n / demo.FPS
    cursor_follow_auto_zoom(cv, lambda c: _screen(c, t), t, _pointer, CLICKS)


CAPABILITY = Capability(
    id='cursor-follow-auto-zoom',
    name='Cursor-follow auto zoom',
    family='broadcast',
    group='UI walkthroughs',
    aliases=('screen recording zoom', 'auto zoom on click', 'click zoom', 'follow-cursor zoom'),
    definition='A screen capture pushes in close around the mouse pointer as it clicks, drifts along '
               'after it while it moves, then eases back out to show the whole screen.',
    phrasings=('zoom the screen recording in on wherever I click',
               'have the camera follow my mouse and punch in on the clicks',
               'auto-zoom the product demo onto the cursor, then back out'),
    related=('canvas-pan-and-zoom', 'zoom-through', 'cursor-state-change', 'dock-magnification',
             'cursor-particle-trail', 'magnetic-button'),
    api=('videobuilder.capabilities.broadcast.cursor_follow_auto_zoom.cursor_follow_auto_zoom',
         'videobuilder.capabilities.broadcast.cursor_follow_auto_zoom.auto_zoom_camera',
         'videobuilder.capabilities.broadcast.cursor_follow_auto_zoom.zoom_amount',
         'videobuilder.capabilities.broadcast.cursor_follow_auto_zoom.follow'),
    demo=lambda: demo.film(draw, SECONDS),
)
