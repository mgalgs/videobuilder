"""Logo bug: a small, see-through channel logo parked in a corner of the
frame for the whole programme, which flares up to full strength on a cue
and then sinks back to its quiet resting level."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def corner_box(width, height, w, h, corner='top-right', margin=48):
    """The (x, y, w, h) of a `w` x `h` bug tucked into `corner` of a
    `width` x `height` frame, `margin` px in from both edges. `corner` is
    'top-left', 'top-right', 'bottom-left' or 'bottom-right'."""
    vert, horiz = corner.split('-')
    x = margin if horiz == 'left' else width - margin - w
    y = margin if vert == 'top' else height - margin - h
    return x, y, w, h


def bug_pulse(t, cues=(), rise=0.18, fall=0.7):
    """How strongly the bug is flaring at time `t` (seconds): 0 at rest, 1 at
    the top of a pulse. Each time in `cues` ramps it up over `rise` seconds,
    then lets it ease back down over `fall`. Overlapping cues take the larger."""
    k = 0.0
    for c in cues:
        d = t - c
        if 0 <= d < rise:
            k = max(k, vb.ease_out_quint(d / rise))
        elif rise <= d < rise + fall:
            k = max(k, 1 - vb.ease_in_out_quart((d - rise) / fall))
    return k


def station_bug(cv, draw_logo, box, t, cues=(), start=None, rest=0.45, peak=1.0, pop=0.12, fade=0.5, **kw):
    """Draw a corner bug at time `t` (seconds). `draw_logo(cv, x, y, w, h)`
    draws the logo filling the box; `box` is (x, y, w, h), e.g. from
    `corner_box`. The bug sits at opacity `rest`; on each time in `cues` it
    flares to `peak` and grows by `pop` about its centre (`kw` goes to
    `bug_pulse`). With `start` set it fades in over `fade` seconds from then;
    otherwise it is already on screen."""
    x, y, w, h = box
    shown = 1.0 if start is None else vb.clamp01((t - start) / fade)
    k = bug_pulse(t, cues, **kw)
    alpha = shown * (rest + (peak - rest) * k)
    s = 1 + pop * k
    cx, cy = x + w / 2, y + h / 2
    with cv.layer(opacity=alpha, dx=cx * (1 - s), dy=cy * (1 - s), scale=s):
        draw_logo(cv, x, y, w, h)
    cv.mark('bug', x, y, w, h)


# ---- demo ----

def _logo(cv, x, y, w, h):
    """The demo's bug: a ring-and-dot mark with a short wordmark (plain shapes, not a real logo)."""
    r = h / 2
    cv.arc(x + r, y + r, r * 0.78, 0, math.tau, demo.INK, width=r * 0.3)
    demo.dot(cv, x + r, y + r, r * 0.28, color=demo.INK)
    f = demo.font(round(h * 0.62), 900)
    th = vb.text.block_size(['NOVA'], f)[1]
    vb.text.draw(cv, ['NOVA'], f, x + h * 1.25, y + (h - th) / 2, demo.INK)


def _programme(cv, t):
    """The show under the bug: the kit photo drifting slowly, so it reads as footage."""
    img = demo.photo()
    x, y, w, h = vb.Box.of(cv).cover(img.w, img.h)
    z = 1.12 + 0.04 * t
    cv.image(img, x - w * (z - 1) / 2 - 30 * t, y - h * (z - 1) / 2, w * z, h * z)


def draw(n, cv):
    t = n / demo.FPS
    _programme(cv, t)
    box = corner_box(demo.W, demo.H, 230, 64, 'bottom-right', margin=56)
    station_bug(cv, _logo, box, t, start=0.2, cues=(1.3,))


CAPABILITY = Capability(
    id='station-id-bug',
    name='Logo bug',
    family='broadcast',
    group='Bumpers & idents',
    aliases=('channel bug', 'network bug', 'corner bug', 'watermark logo', 'digital on-screen graphic',
             'DOG', 'station ID bug'),
    definition='A small, faint channel logo stays parked in one corner over the footage, '
               'briefly brightening and swelling on a cue before settling back.',
    phrasings=('put our logo small and see-through in the corner like a TV channel',
               'add a watermark logo in the corner that pulses now and then',
               'a channel bug over the video that lights up when something happens'),
    related=('logo-glitch-reveal', 'score-bug', 'glitch-text', 'glitch-transition', 'data-bending',
             'shrinking-sticky-header'),
    api=('videobuilder.capabilities.broadcast.station_id_bug.station_bug',
         'videobuilder.capabilities.broadcast.station_id_bug.corner_box',
         'videobuilder.capabilities.broadcast.station_id_bug.bug_pulse'),
    demo=lambda: demo.film(draw),
)
