"""Text on a path: each letter sits on a curve, turned to follow it, and the
line slides along the curve so the words flow round its bends."""
import bisect
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def walker(points, closed=False):
    """A function `at(s) -> (x, y, angle)` giving the point `s` px along
    `points` by arc length and the direction of travel there (radians). A
    closed path wraps `s`; an open one clamps it to its ends. Also returns
    the path's total length: `(at, total)`."""
    pts = list(points) + ([points[0]] if closed else [])
    acc = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        acc.append(acc[-1] + math.hypot(x1 - x0, y1 - y0))
    total = acc[-1]

    def at(s):
        s = s % total if closed and total else min(max(s, 0.0), total)
        i = min(max(bisect.bisect_right(acc, s) - 1, 0), len(pts) - 2)
        hop = acc[i + 1] - acc[i]
        t = (s - acc[i]) / hop if hop else 0.0
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, math.atan2(y1 - y0, x1 - x0)

    return at, total


def draw_on_path(cv, text, font, points, offset, color, closed=False, rise=None, tracking=0, fade=60,
                 alpha=1.0):
    """Draw `text` along `points`, its first letter starting `offset` px along
    the path, each letter standing on the curve at its place and turned to the
    tangent there. `rise` lifts the letters' centres off the curve (default:
    about a third of a line, so they sit on it; 0 centres them on it);
    `tracking` adds px between letters, which keeps them apart on tight bends. Animate `offset` to make the line travel. On an open path
    letters past either end are hidden, fading over the last `fade` px; a
    closed path wraps them round. Returns the Box the drawn letters cover."""
    at, total = walker(points, closed)
    lh = vb.text.line_height(font)
    rise = lh * 0.32 if rise is None else rise
    ctx = cv.ctx
    xs, ys = [], []
    s = offset
    for ch in text:
        cw = vb.text.measure(ch, font)
        mid = s + cw / 2
        s += cw + tracking
        if ch.isspace():
            continue
        a = alpha
        if not closed:
            edge = min(mid, total - mid)
            if edge < 0:
                continue
            if fade:
                a *= vb.clamp01(edge / fade)
        x, y, ang = at(mid)
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(ang)
        vb.text.draw(cv, [ch], font, -cw / 2, -lh / 2 - rise, color, alpha=a)
        ctx.restore()
        xs.append(x)
        ys.append(y)
    if not xs:
        return vb.Box(0, 0, 0, 0)
    pad = lh / 2 + abs(rise)
    return vb.Box(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)


def _wave(n=240):
    """The demo's curve: one gentle S-shaped swell across the frame."""
    out = []
    for k in range(n):
        u = k / (n - 1)
        x = 140 + (demo.W - 280) * u
        y = demo.H / 2 + 40 + 125 * math.sin(u * 2 * math.pi)
        out.append((x, y))
    return out


WAVE = _wave()


def draw(n, cv):
    vb.paths.draw(cv, WAVE, demo.LINE, width=3)
    f = demo.font(60, 800)
    text = 'FOLLOW THE CURVE'
    span = vb.text.measure(text, f) + 6 * len(text)
    total = vb.paths.length(WAVE)
    p = demo.phase(n, 0.1, 2.9)
    p = p * p * (3 - 2 * p)  # smoothstep: drifts off, cruises, drifts in
    offset = -span * 0.6 + (total - span * 0.4) * p
    box = draw_on_path(cv, text, f, WAVE, offset, demo.INK, tracking=6)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='text-on-a-path',
    name='Text on a path',
    family='typography',
    group='Path and orbit',
    aliases=('path text', 'curved text', 'text along a curve', 'path text travel'),
    definition='Letters are laid along a curved line, each tilted to follow it, and the words glide '
               'along that line so they bend through every turn.',
    phrasings=('make the words travel along a wavy line',
               'the title rides round the curve like a train on a track',
               'curved text that slides along a path'),
    related=('twirl-warp-text', 'echo-trail-type', 'stroke-draw-on', 'sine-wave-text', 'text-to-shape-morph',
             'per-character-fade-in'),
    api=('videobuilder.capabilities.typography.text_on_a_path.draw_on_path',
         'videobuilder.capabilities.typography.text_on_a_path.walker'),
    demo=lambda: demo.film(draw),
)
