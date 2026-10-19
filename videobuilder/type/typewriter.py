"""Typewriter and terminal: letters strike in one at a time with a human,
uneven cadence (the compendium terminal title's keystroke schedule) and a cursor riding
the end of the line.

- **typewriter**: monospace on the paper, each letter struck a touch off
  its line and a touch light or heavy, the way a typebar lands, with a
  margin rule in the accent. Through the hold the caret blinks and the
  sheet drifts in; on the exit the sheet feeds up out of the frame.
- **terminal**: a prompt in the accent before each line, a block cursor,
  and over the paper faint scanlines with a slow rolling band. Through the
  hold the cursor blinks on the beat and the screen pushes in; on the exit
  every line is deleted back to the prompt.

The block of lines is set as big as the frame allows, left-aligned and
centred as a block, per frame shape.
"""
import math
from functools import lru_cache

import cairo

from .. import text
from ..ease import ease_in_expo
from ..layout import Box
from ..text import Font
from . import kit
from .style import Clock, Style

PROMPT = '> '


def _schedule(chars, seed, per_char):
    """Seeded keystroke times from the start of a line, and its span: a
    little uneven, a longer reach after a space or a comma. The compendium's
    terminal title's cadence (title_terminal._schedule), carried over so
    this package needn't import the compendium."""
    rnd = kit.rng(seed)
    t, out = 0.0, []
    for ch in chars:
        out.append(t)
        t += per_char * rnd.uniform(0.55, 1.45) * (1.8 if ch in ' ,.' else 1.0)
    return out, t


def _clock(p):
    n = sum(len(ln) for ln in p.lines)
    return Clock(p.length, enter=min(0.6 * p.length, max(1.2, 0.35 + n * 0.07)))


@lru_cache(maxsize=64)
def _keys(lines, hold):
    """The keystroke times of every character, line by line: [[t, ...], ...],
    each line starting after a short reach for the return."""
    times, t = [], 0.15
    for i, line in enumerate(lines):
        ts, span = _schedule(line, f'{i}:{line}', 1.0)
        times.append([t + x for x in ts])
        t += span + 2.2
    end = t - 2.2
    k = (hold - 0.3) / end if end > 0 else 1.0
    return tuple(tuple(0.15 + (x - 0.15) * k for x in ts) for ts in times)


@lru_cache(maxsize=64)
def _layout(lines, box, family, prompt):
    inner, w, h, k = kit.room(box, tall=(0.94, 0.5), wide=(0.8, 0.62), square=(0.88, 0.6))
    pre = len(PROMPT) if prompt else 0
    font = kit.fit([PROMPT * bool(prompt) + ln for ln in lines], lambda s: Font(family, s, weight=600 if prompt else 500,
                                                                                line_height=1.3), w, h)
    lh = text.line_height(font)
    widths = [text.measure((PROMPT if prompt else '') + ln, font) for ln in lines]
    bw = max(widths)
    x = inner.cx - bw / 2
    y = inner.cy - lh * len(lines) / 2
    return font, x, y, lh, text.measure(PROMPT, font) if pre else 0.0


def _draw(cv, p, t, box, clock, terminal):
    lines = p.lines
    keys = _keys(lines, clock.hold)
    font, x0, y0, lh, pre = _layout(lines, Box(*box), STYLE.font_family(p), terminal)
    g = kit.ground(p)
    ctx = cv.ctx
    content, _ = text._content(font)
    out = clock.leaving(t)
    cam = kit.camera(t, clock.hold, box.cx, box.cy, box, k=0.06)
    feed = -ease_in_expo(out) * box.h * 0.7 if not terminal else 0.0
    # The terminal deletes every line, last letter first, through the exit.
    total = sum(len(ln) for ln in lines)
    kept = total - round(total * min(1.0, out * 1.15)) if terminal else total
    cursor = None
    cam['dy'] += feed
    with cv.layer(**cam, opacity=1 - out if not terminal else 1):
        if not terminal:
            mx = x0 - font.size * 0.9
            cv.rect(mx, y0 - lh * 0.4, max(1.5, font.size * 0.05), lh * (len(lines) + 0.8), p.accent, alpha=0.8)
        shown_before = 0
        for i, line in enumerate(lines):
            y = y0 + i * lh
            ts = keys[i]
            typed = sum(1 for k in ts if k <= t)
            typed = max(0, min(typed, kept - shown_before))
            shown_before += len(line)
            started = t >= ts[0] - 0.12 if ts else True
            if terminal and started and (typed or i == 0 or t < clock.exit):
                text.draw(cv, [PROMPT.strip()], font, x0, y, p.accent)
            xs, width = kit.advances(line, font)
            tx = x0 + pre
            rnd = kit.rng('typewriter', i, line)
            for j in range(typed):
                ch = line[j]
                jitter = (rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0.78, 1.0))
                if ch == ' ':
                    continue
                age = t - ts[j]
                pop = 1 + 0.14 * max(0.0, 1 - age / 0.07) if not terminal else 1.0
                gx = tx + xs[j]
                gw = text.measure(ch, font)
                if terminal:
                    text.draw(cv, [ch], font, gx, y, p.ink)
                    continue
                ctx.save()
                ctx.translate(gx + gw / 2, y + lh / 2 + jitter[1] * font.size * 0.03)
                ctx.rotate(math.radians(jitter[0] * 1.2))
                ctx.scale(pop, pop)
                kit.glyphs(cv, ch, font, -gw / 2, -lh / 2, p.ink, jitter[2])
                ctx.restore()
            # The cursor sits after the last letter in: on the last line begun (while
            # deleting, the last line with a letter left, or the first).
            if started and (typed or i == 0 or not (terminal and out > 0)):
                cursor = (tx + (xs[typed] if typed < len(line) else width), y)
            if typed == len(line) and out == 0:
                cv.mark(f'line-{i}', x0, y, pre + width, lh)
        if cursor is not None:
            typing = clock.hold - 0.2 > t or out > 0
            blink = (t - clock.hold) % (0.5 if terminal else 1.0) < (0.25 if terminal else 0.55)
            if typing or blink:
                cxp, cyp = cursor
                cw = text.measure('M', font)
                if terminal:
                    cv.rect(cxp + 2, cyp + lh * 0.14, cw * 0.62, lh * 0.72, p.accent)
                else:
                    cv.rect(cxp + 1, cyp + lh * 0.5 + content * 0.42, cw * 0.9, max(2, font.size * 0.07), p.accent)
    if terminal and p.paper is not None:
        _glass(cv, box, t)
    elif p.paper is not None:
        from ..canvas import paper_grain
        ctx.save()
        ctx.rectangle(*box)
        ctx.clip()
        ctx.set_source(paper_grain(cv.width, cv.height, seed=7))
        ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
        ctx.paint_with_alpha(0.3)
        ctx.restore()


def _glass(cv, box, t):
    """Scanlines and a slow rolling band over the screen."""
    ctx = cv.ctx
    ctx.set_source_rgba(0, 0, 0, 0.2)
    step = max(3.0, box.h / 360)
    y = box.y
    while y < box.bottom:
        ctx.rectangle(box.x, y, box.w, step * 0.35)
        y += step
    ctx.fill()
    bh = box.h * 0.12
    band = box.y + (t * box.h * 0.3) % (box.h + 2 * bh) - bh
    g = cairo.LinearGradient(0, band - bh, 0, band + bh)
    g.add_color_stop_rgba(0, 1, 1, 1, 0)
    g.add_color_stop_rgba(0.5, 1, 1, 1, 0.09)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    ctx.set_source(g)
    ctx.rectangle(box.x, band - bh, box.w, 2 * bh)
    ctx.fill()


def draw_typewriter(cv, p, t, box, clock):
    _draw(cv, p, t, box, clock, False)


def draw_terminal(cv, p, t, box, clock):
    _draw(cv, p, t, box, clock, True)


def events(p, clock):
    """A key at every keystroke; the typewriter's bell when the last line is in."""
    keys = _keys(p.lines, clock.hold)
    out = [(k, 'key') for ts in keys for k in ts]
    return out


def bell_events(p, clock):
    keys = _keys(p.lines, clock.hold)
    return events(p, clock) + [(keys[-1][-1] + 0.12, 'bell')]


STYLE = Style('typewriter', 'Typewriter', 'letters strike in one by one, a little uneven, the caret riding the line',
              draw_typewriter, aliases=('typed', 'typing', 'type on', 'typewriter text'), events=bell_events,
              sound={'key': (('fit/key/medium', 'typing_key/clicky'), ('key', 'click'), -8.0),
                     'bell': (('fit/bell/small_bell',), ('ding',), -16.0)},
              clock=_clock, family='monospace')

TERMINAL = Style('terminal', 'Terminal', 'a prompt, a block cursor, each line typed in and deleted at the end',
                 draw_terminal, aliases=('command line', 'console', 'code', 'shell'), events=events,
                 sound={'key': (('pro_typing_key/tick', 'typing_key/crisp'), ('key', 'click'), -10.0)},
                 clock=_clock, family='monospace')
