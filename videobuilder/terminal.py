"""A terminal or chat log that keeps appending lines and scrolls once full.

    KINDS = {'think': vb.terminal.Kind(vb.Font('monospace', 26, style='italic'), '#8a8f98'),
             'cmd': vb.terminal.Kind(vb.Font('monospace', 26, weight=600), '#f4f4f2', prefix='$ ',
                                     prefix_color='#4fc3b0', typed=True),
             'out': vb.terminal.Kind(vb.Font('monospace', 26), '#c8b27a')}
    LOG = vb.TerminalLog([(0.5, 'think', 'The tests fail on import.'),
                          (1.6, 'cmd', 'pytest -q'),
                          (2.4, 'out', '3 passed in 0.41s')], KINDS)

    def draw(n, cv):
        LOG.draw(cv, n / FPS, box)                       # the state at t, in box

    FILM = vb.Film(..., sounds=LOG.sounds(at=0, fps=FPS))

An event is `(t, kind, text)`: the line starts at `t` seconds, looks like
its `Kind`, and wraps to the box (continuation rows hang under the text,
past the prefix). A typed kind types on with the typewriter styles' uneven
cadence (`vb.type`); any other appears whole. When the next row doesn't
fit, the log eases up and old rows leave at the top, clipped to the box.
`paced` spaces events so each starts a beat after the last one finished.

Everything drawn is a function of `t` alone (chunks render in parallel).
"""
import bisect
import math
from dataclasses import dataclass

import cairo

from . import text
from .ease import ease_out_quint
from .text import Font

# The terminal type style's key sound; a soft tick for a line that appears.
TICK = (('pro_hover_tick/soft', 'hover_tick/detent'), ('tick', 'click'), -18.0)


@dataclass(frozen=True)
class Kind:
    """How one kind of line looks: its `font` and `color`, a `prefix` (a
    prompt such as '$ ', in `prefix_color`, default `color`), whether it is
    `typed` on (`per_char` seconds a keystroke on average) or appears whole,
    and whether it makes a `sound` (keys when typed, a tick when not)."""
    font: Font
    color: str
    prefix: str = ''
    prefix_color: str | None = None
    typed: bool = False
    per_char: float = 0.055
    sound: bool = True


@dataclass(frozen=True)
class _Row:
    event: int
    y: float          # top, from the top of the log
    h: float
    x: float          # left, from the box's left: past the prefix
    text: str
    first: int        # index of its first character in its event's text


def _kind(k):
    return k if isinstance(k, Kind) else Kind(**k)


def typing_time(kind, text_):
    """Seconds `kind` takes to type `text_` (0 for a kind that appears)."""
    if not _kind(kind).typed:
        return 0.0
    return _keys(_kind(kind), text_)[1]


def _keys(kind, text_):
    # Seeded by the text alone, not its place in a list: `paced` and the log
    # must agree on a line's cadence whatever events surround it.
    from .type.typewriter import schedule
    return schedule(text_, text_, kind.per_char)


def paced(lines, kinds, start=0.0, gap=0.4):
    """Events for `lines`, (kind, text) or (kind, text, pause): each starts
    `pause` (default `gap`) seconds after the one before has finished typing,
    the first at `start`."""
    out, t = [], start
    for i, line in enumerate(lines):
        kind, text_ = line[0], line[1]
        if i:
            t += line[2] if len(line) > 2 else gap
        out.append((t, kind, text_))
        t += typing_time(kinds[kind], text_)
    return out


class TerminalLog:
    """A log of `events` [(t, kind, text)] in the looks of `kinds`
    {name: Kind}. `gap`: space before each event but the first, in ems of
    its font. `scroll`: seconds an eased scroll takes. `cursor`: a block
    cursor on a typed line that is the last one begun, blinking once it's
    typed. `fade`: px at the top of the box over which leaving lines fade
    out once the log has scrolled (0: a hard edge)."""

    def __init__(self, events, kinds, gap=0.35, scroll=0.22, cursor=True, fade=24):
        self.kinds = {name: _kind(k) for name, k in kinds.items()}
        self.events = tuple(sorted(((float(t), k, str(s)) for t, k, s in events), key=lambda e: e[0]))
        self.gap, self.scroll, self.cursor, self.fade = gap, scroll, cursor, fade
        for t, k, s in self.events:
            if k not in self.kinds:
                raise ValueError(f'event at {t:g} s: no kind {k!r}; kinds: {", ".join(self.kinds)}')
        # Absolute keystroke times of each event's characters ([] for a line that appears).
        self.keys = []
        for i, (t, k, s) in enumerate(self.events):
            kind = self.kinds[k]
            self.keys.append([t + x for x in _keys(kind, s)[0]] if kind.typed else [])
        for i in range(len(self.events) - 1):
            done, nxt = self.finish(i), self.events[i + 1][0]
            if done > nxt + 1e-9:
                raise ValueError(f'event {i + 1} starts at {nxt:g} s while event {i} ({self.events[i][2][:30]!r}) '
                                 f'is still typing until {done:.2f} s: start it later, or build the events '
                                 f'with vb.terminal.paced')
        self._layouts = {}

    def finish(self, i):
        """When event `i` is all there: its last keystroke, or its start."""
        t, k, s = self.events[i]
        return t + _keys(self.kinds[k], s)[1] if self.kinds[k].typed else t

    @property
    def end(self):
        """When the last event is all there."""
        return self.finish(len(self.events) - 1) if self.events else 0.0

    def _layout(self, w, h):
        """(rows, scroll steps [(t, offset)]) for a box `w` x `h`."""
        if (w, h) in self._layouts:
            return self._layouts[w, h]
        rows, y, appear = [], 0.0, []
        for i, (t, k, s) in enumerate(self.events):
            kind = self.kinds[k]
            if i:
                y += self.gap * kind.font.size
            px = text.measure(kind.prefix, kind.font) if kind.prefix else 0.0
            lh = text.line_height(kind.font)
            pos = 0
            for r, line in enumerate(text.wrap(s, kind.font, max(1.0, w - px)) or ('',)):
                first = s.find(line, pos) if line else pos
                first = pos if first < 0 else first
                pos = first + len(line)
                rows.append(_Row(i, y, lh, px, line, first))
                # A typed row shows once its first letter is in; the first row with the prompt.
                when = self.keys[i][first] if kind.typed and r and first < len(self.keys[i]) else t
                appear.append((when, y + lh))
                y += lh
        steps, top = [], 0.0
        for when, bottom in sorted(appear):
            want = max(top, bottom - h)
            if want > top:
                steps.append((when, want - top))
                top = want
        self._layouts[w, h] = rows, steps
        return rows, steps

    def offset(self, t, w, h):
        """How far the log has scrolled up at `t`, px, in a box `w` x `h`."""
        _, steps = self._layout(w, h)
        dur = max(self.scroll, 1e-6)
        return sum(d * ease_out_quint(min(1.0, (t - when) / dur)) for when, d in steps if t > when)

    def typed(self, i, t):
        """How many of event `i`'s characters are in at `t`."""
        if not self.kinds[self.events[i][1]].typed:
            return len(self.events[i][2]) if t >= self.events[i][0] else 0
        return bisect.bisect_right(self.keys[i], t + 1e-9)

    def draw(self, cv, t, box):
        """The log as it is at `t` seconds, in `box` (x, y, w, h)."""
        x0, y0, w, h = box
        rows, _ = self._layout(w, h)
        scrolled = self.offset(t, w, h)
        top = y0 - scrolled
        last = bisect.bisect_right([e[0] for e in self.events], t + 1e-9) - 1
        fade = min(self.fade, scrolled, h / 2)
        with cv.clip(x0, y0, w, h):
            if fade < 1:
                self._rows(cv, t, rows, top, last, (x0, y0, w, h))
                return
            ctx = cv.ctx
            ctx.push_group()
            self._rows(cv, t, rows, top, last, (x0, y0, w, h))
            ctx.pop_group_to_source()
            ramp = cairo.LinearGradient(0, y0, 0, y0 + fade)
            ramp.add_color_stop_rgba(0, 0, 0, 0, 0)
            ramp.add_color_stop_rgba(1, 0, 0, 0, 1)
            ctx.mask(ramp)

    def _rows(self, cv, t, rows, top, last, box):
        x0, y0, w, h = box
        cursor = None
        for row in rows:
            i = row.event
            if i > last:
                break
            y = top + row.y
            t0, k, s = self.events[i]
            kind = self.kinds[k]
            n = self.typed(i, t)
            shown = max(0, min(len(row.text), n - row.first))
            if row.first and not shown and kind.typed:
                continue
            if y + row.h < y0 or y > y0 + h:
                continue
            if not row.first and kind.prefix:
                text.draw(cv, [kind.prefix], kind.font, x0, y, kind.prefix_color or kind.color)
            if shown:
                text.draw(cv, [row.text[:shown]], kind.font, x0 + row.x, y, kind.color)
            if i == last and kind.typed:   # after the last letter in, on the last row begun
                cursor = (x0 + row.x + (text.measure(row.text[:shown], kind.font) if shown else 0), y, row.h, kind)
        if cursor is not None and self.cursor:
            cx, cy, lh, kind = cursor
            done = self.finish(last)
            if t < done + 0.35 or (t - done - 0.35) % 1.0 < 0.55:
                cw = text.measure('M', kind.font)
                cv.rect(cx + cw * 0.08, cy + lh * 0.12, cw * 0.62, lh * 0.76, kind.prefix_color or kind.color)

    def sounds(self, at=0, fps=30, keys=True, ticks=True):
        """`vb.sfx` sounds for the log starting on film frame `at`: a key on
        every keystroke (the terminal type style's), each on the first frame
        its letter shows, and a soft tick as each line that appears does.
        () without the sound-effects pack, said once in the log."""
        from . import sfx
        from .type import _note_once, _pick
        from .type.typewriter import TERMINAL
        try:
            bank = sfx.bank()
        except sfx.SfxUnavailable as e:
            _note_once('pack', f'terminal log plays without its sound: {e}')
            return ()
        key_id, key_gain = _pick(bank, *TERMINAL.sound['key'][:2]), TERMINAL.sound['key'][2]
        tick_id, tick_gain = _pick(bank, *TICK[:2]), TICK[2]

        def frame(t):
            return at + math.ceil(t * fps - 1e-9)

        out = []
        for i, (t, k, s) in enumerate(self.events):
            kind = self.kinds[k]
            if not kind.sound:
                continue
            if kind.typed and keys and key_id:
                out += [sfx.sound(key_id, at=frame(x), fps=fps, gain_db=key_gain, align='onset')
                        for x in self.keys[i]]
            elif not kind.typed and ticks and tick_id:
                out.append(sfx.sound(tick_id, at=frame(t), fps=fps, gain_db=tick_gain, align='onset'))
        return tuple(out)
