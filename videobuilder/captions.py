"""Captions timed to each word, from a subtitle file.

A `Track` is a list of timed `Word`s, read from WebVTT (YouTube's rolling
auto-captions carry a time for every word) or SRT (line times only: words are
spread across each cue and marked interpolated). `shift` and `slice` line a
track made for a whole source video up with a clip cut from it.

`draw(cv, track, t)` draws the caption for time `t`: one short line at a time
in a dark box at the bottom of the safe area, the word being spoken in one
colour and `keywords` in an accent. Lines are grouped with Pango measuring the
real font, so a line that fits here fits on a machine with wider fonts too.
"""
import bisect
import html
import re
from dataclasses import dataclass, replace
from pathlib import Path

import gi

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo  # noqa: E402

from . import text  # noqa: E402
from .canvas import rgba  # noqa: E402
from .layout import Box  # noqa: E402
from .text import Font  # noqa: E402


@dataclass(frozen=True)
class Word:
    text: str
    start: float  # seconds
    end: float
    exact: bool = True  # False: the time was spread across a cue, not given per word
    turn: bool = False  # a new speaker starts here ('>>' in the source)


class Track:
    """Timed words in spoken order. Immutable: `shift` and `slice` return new tracks."""

    def __init__(self, words=()):
        self.words = tuple(words)
        self._groups = {}

    def __len__(self):
        return len(self.words)

    def __iter__(self):
        return iter(self.words)

    def __getitem__(self, i):
        return self.words[i]

    def __repr__(self):
        span = f' {self.words[0].start:.2f}-{self.words[-1].end:.2f}s' if self.words else ''
        return f'<Track {len(self.words)} words{span}>'

    @property
    def text(self):
        return ' '.join(w.text for w in self.words)

    def shift(self, seconds):
        """Every word `seconds` later (earlier when negative)."""
        return Track(replace(w, start=w.start + seconds, end=w.end + seconds) for w in self.words)

    def slice(self, start, end):
        """The words that start in [start, end), on the same clock; a word
        running past `end` is cut there. A clip from source time `a` to `b`
        placed at film time `at`: `track.slice(a, b).shift(at - a)`."""
        return Track(replace(w, end=min(w.end, end)) for w in self.words if start <= w.start < end)

    def lines(self, font, max_width, pause=0.7, linger=1.0):
        """The words grouped into caption `Line`s at most `max_width` px wide
        in `font`, measured with Pango. Lines break after a sentence end, at a
        pause of `pause` s or more, at a new speaker, and otherwise wherever
        the width forces, balanced so a phrase's lines come out even. A word
        counts as spoken for at most `linger` s past its start, which is how a
        pause shows in captions whose words run into the next one."""
        key = (font, round(max_width, 3), pause, linger)
        if key not in self._groups:
            self._groups[key] = _group(self.words, font, max_width, pause, linger)
        return self._groups[key]

    def line_at(self, t, font, max_width, pause=0.7, linger=1.0):
        """The `Line` on screen at `t`, or None between lines."""
        lines = self.lines(font, max_width, pause, linger)
        i = bisect.bisect_right([ln.start for ln in lines], t) - 1
        if i >= 0 and t < lines[i].end:
            return lines[i]
        return None


@dataclass(frozen=True)
class Line:
    words: tuple
    start: float  # first word starts
    end: float  # shown until here, then the next line replaces it

    @property
    def text(self):
        return ' '.join(w.text for w in self.words)


# ---- parsing ----
_TIME = r'(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})'
_TIMING = re.compile(rf'^\s*{_TIME}\s*-->\s*{_TIME}(?:\s+.*)?$')
_INLINE = re.compile(r'<(\d+:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})>')
_TAG = re.compile(r'</?[^<>\s][^<>]*>')
_SOUND = re.compile(r'\[[^\]]*\]|[♪♫]+')
_SPEAKER = re.compile(r'(^|\s)(>>+|&gt;&gt;)\s*')


def _seconds(h, m, s, ms):
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, '0')) / 1000


def _inline_seconds(s):
    parts = s.replace(',', '.').split(':')
    return sum(float(p) * 60 ** i for i, p in enumerate(reversed(parts)))


def _timing(line, n):
    m = _TIMING.match(line)
    if not m:
        raise ValueError(f'line {n}: bad cue timing {line.strip()!r}: expected "00:00:01.000 --> 00:00:02.500"')
    a, b = _seconds(*m.groups()[:4]), _seconds(*m.groups()[4:])
    if b < a:
        raise ValueError(f'line {n}: cue ends before it starts: {line.strip()!r}')
    return a, b


def _clean(s):
    """Markup, entities, sound labels and speaker marks out -> (plain text, new speaker?)."""
    s = _TAG.sub('', s)
    turn = bool(_SPEAKER.search(s))
    s = _SPEAKER.sub(' ', s)
    s = html.unescape(s)
    turn = turn or bool(_SPEAKER.search(s))
    s = _SPEAKER.sub(' ', s)
    s = _SOUND.sub(' ', s)
    return ' '.join(s.split()), turn


def _spread(words, start, end, turn=False, exact=False):
    """Words over [start, end) in proportion to their length, marked interpolated."""
    if not words:
        return []
    total = sum(len(w) for w in words)
    out, at = [], start
    for i, w in enumerate(words):
        d = (end - start) * len(w) / total
        out.append(Word(w, at, at + d, exact=exact and i == 0, turn=turn and i == 0))
        at += d
    return out


def _cues(lines, first_line, vtt):
    """[(start, end, [text lines], line number)] from the lines after a header."""
    cues, block = [], []
    for i, raw in enumerate(lines + [''], start=first_line):
        line = raw.rstrip('\r\n')
        if line.strip() == '' and (not vtt or line == '' or not block):
            if block:
                cues.append(_cue(block, vtt))
            block = []
            continue
        block.append((i, line))
    return [c for c in cues if c is not None]


def _cue(block, vtt):
    (n, first), rest = block[0], block[1:]
    if vtt and re.match(r'^(NOTE|STYLE|REGION)(\s|$)', first):
        return None
    if '-->' not in first:
        if not rest or '-->' not in rest[0][1]:
            if rest:  # an id, then not a timing
                bad, got = rest[0]
                raise ValueError(f'line {bad}: expected a cue timing line after {first.strip()!r}, got {got.strip()!r}')
            raise ValueError(f'line {n}: expected a cue timing line, got {first.strip()!r}')
        (n, first), rest = rest[0], rest[1:]
    a, b = _timing(first, n)
    return a, b, [ln for _, ln in rest], n


def parse_vtt(source):
    """A Track from WebVTT text. YouTube's rolling auto-captions (a time tag
    before every word, each line repeated in the next cue) give every word
    once, with its own time; plain VTT is spread like SRT."""
    lines = source.lstrip('﻿').replace('\r\n', '\n').split('\n')
    if not lines or not lines[0].startswith('WEBVTT'):
        raise ValueError(f'line 1: a WebVTT file starts with "WEBVTT", got {lines[0][:40]!r}' if lines
                         else 'line 1: empty file')
    i = 1  # header: everything up to the first empty line
    while i < len(lines) and lines[i].strip() != '':
        if '-->' in lines[i]:
            raise ValueError(f'line {i + 1}: a cue needs an empty line between it and the header')
        i += 1
    cues = _cues(lines[i:], i + 1, vtt=True)
    if not cues:
        raise ValueError('no cues: the file has a WEBVTT header but no timed text')
    rolling = any(_INLINE.search(ln) for c in cues for ln in c[2])
    return Track(_rolling(cues) if rolling else _plain(cues))


def parse_srt(source):
    """A Track from SRT text. SRT times lines, not words: each cue's words are
    spread across it by length and marked `exact=False`."""
    lines = source.lstrip('﻿').replace('\r\n', '\n').split('\n')
    cues = _cues(lines, 1, vtt=False)
    if not cues:
        raise ValueError('no cues: the file has no timed text')
    return Track(_plain(cues))


def _plain(cues):
    words = []
    for a, b, body, _ in cues:
        plain, turn = _clean(' '.join(body))
        words += _spread(plain.split(), a, b, turn)
    return words


def _rolling(cues):
    words, prev = [], set()
    for a, b, body, n in cues:
        shown = set()
        for line in body:
            plain, _ = _clean(_INLINE.sub('', line))
            if not plain:
                continue
            shown.add(plain)
            if _INLINE.search(line):
                words += _timed_line(line, a, b, n)
            elif plain not in prev:  # a new line too short for time tags ("add.")
                p, turn = _clean(line)
                words += _spread(p.split(), a, b, turn, exact=len(p.split()) == 1)
        prev = shown
    return words


def _timed_line(line, a, b, n):
    parts = _INLINE.split(line)  # text, time, text, time, ..., text
    pieces, at = [], a
    for k in range(0, len(parts), 2):
        if k:
            t = _inline_seconds(parts[k - 1])
            if t < at - 1e-6:
                raise ValueError(f'line {n}: word time {parts[k - 1]} goes back before {at:.3f}s')
            at = t
        pieces.append((at, parts[k]))
    out = []
    for k, (t, piece) in enumerate(pieces):
        nxt = pieces[k + 1][0] if k + 1 < len(pieces) else max(b, t)
        plain, turn = _clean(piece)
        out += _spread(plain.split(), t, nxt, turn, exact=True)
    return out


def parse(source):
    """A Track from subtitle text, VTT or SRT by its content."""
    return parse_vtt(source) if source.lstrip('﻿').startswith('WEBVTT') else parse_srt(source)


def load(path):
    """A Track from a .vtt or .srt file."""
    return parse(Path(path).read_text(encoding='utf-8-sig'))


# ---- grouping ----
_SENTENCE_END = re.compile(r'[.?!…]["\'”’)\]]*$')


def _group(words, font, max_width, pause, linger):
    phrases, cur = [], []
    for i, w in enumerate(words):
        if cur:
            p = cur[-1]
            if (_SENTENCE_END.search(p.text) or w.turn
                    or w.start - min(p.end, p.start + linger) >= pause):
                phrases.append(cur)
                cur = []
        cur.append(w)
    if cur:
        phrases.append(cur)
    out = []
    for ph in phrases:
        for ws in _balanced(ph, font, max_width):
            last = ws[-1]
            out.append(Line(tuple(ws), ws[0].start, max(ws[0].start, min(last.end, last.start + linger))))
    # a line never outlasts the next one's start
    return tuple(replace(ln, end=min(ln.end, nxt.start)) if nxt.start < ln.end else ln
                 for ln, nxt in zip(out, out[1:] + [Line((), float('inf'), float('inf'))]))


def _greedy(ws, font, width):
    lines, cur = [], []
    for w in ws:
        if cur and text.measure(' '.join(x.text for x in cur + [w]), font) > width:
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def _balanced(ws, font, max_width):
    """Greedy lines at the narrowest width that needs no more of them."""
    lines = _greedy(ws, font, max_width)
    if len(lines) < 2:
        return lines
    lo, hi = 0.0, float(max_width)
    while hi - lo > 1.0:
        mid = (lo + hi) / 2
        if len(_greedy(ws, font, mid)) > len(lines):
            lo = mid
        else:
            hi = mid
    return _greedy(ws, font, hi)


# ---- drawing ----
def safe_area(cv):
    """A placeholder safe area for `cv`'s shape, the template's margins as
    fractions of the frame: vertical video loses more at the bottom to
    platform UI. Pass the platform's own numbers as `safe=` when you know them."""
    w, h = cv.width, cv.height
    frame = Box(0, 0, w, h)
    if h > w:
        return frame.pad(h * 0.115, w * 0.065, h * 0.198, w * 0.065)
    if w > h:
        return frame.pad(h * 0.074, w * 0.0625)
    return frame.pad(h * 0.074, w * 0.065, h * 0.11, w * 0.065)


def default_font(cv, family='sans-serif', weight=700):
    """The caption font for `cv`: 5.8% of the frame's short side (63 px in
    1080x1920), a size that reads on a phone."""
    return Font(family, round(min(cv.width, cv.height) * 0.058, 1), weight=weight)


def _norm(s):
    return re.sub(r'[^\w]+', '', s.casefold())


def _attr(make, start, end, *args):
    a = make(*args)
    a.start_index, a.end_index = start, end
    return a


@dataclass(frozen=True)
class Drawn:
    """What `draw` put on the canvas: the box, the line, and each word's
    (word, Box, colour)."""
    box: Box
    line: Line
    words: tuple


def draw(cv, track, t, keywords=(), font=None, safe=None, position='bottom', max_width=None,
         color='#ffffff', spoken='#ffd23f', accent='#3ddc97', box='#000000', box_alpha=0.72,
         pause=0.7, linger=1.0, mark='caption'):
    """Draw the caption line on screen at `t` (seconds, the track's clock) and
    return a `Drawn`, or draw nothing and return None between lines.

    The line sits in a rounded `box` at the bottom (or 'top', 'middle') of
    `safe` (default `safe_area(cv)`), at most `max_width` px of text (default
    the safe width less the box padding). The word being spoken takes
    `spoken`; words in `keywords` (case and punctuation ignored) take `accent`
    whenever they show; the rest `color`. Only colours change, never layout.
    `box_alpha` 1 gives a solid box. The box is marked `mark` (None: no mark).
    """
    font = font or default_font(cv)
    safe = safe or safe_area(cv)
    pad_v, pad_h = font.size * 0.32, font.size * 0.5
    max_width = max_width if max_width is not None else safe.w - 2 * pad_h
    line = track.line_at(t, font, max_width, pause, linger)
    if line is None:
        return None
    keys = {_norm(k) for k in keywords}
    s = line.text
    tw = text.measure(s, font)
    while tw > max_width:  # one word wider than the line: smaller, for this line only
        font = replace(font, size=font.size * max_width / tw * 0.99)
        tw = text.measure(s, font)
    lh = text.line_height(font)
    bw, bh = tw + 2 * pad_h, lh + 2 * pad_v
    by = {'bottom': safe.bottom - bh, 'top': safe.y, 'middle': safe.cy - bh / 2}[position]
    b = Box(safe.cx - bw / 2, by, bw, bh)
    if box is not None:
        cv.rect(*b, box, radius=font.size * 0.22, alpha=box_alpha)

    ctx = cv.ctx
    L = text._layout(ctx, s, font)
    attrs = L.get_attributes() or Pango.AttrList()
    raw = s.encode()
    at = 0
    colours = []
    x0, y0 = b.x + pad_h, b.y + pad_v + (lh - text._content(font)[0]) / 2
    for w in line.words:
        n = len(w.text.encode())
        at = raw.index(w.text.encode(), at)
        c = (accent if _norm(w.text) in keys
             else spoken if w.start <= t < min(w.end, w.start + linger) else color)
        r, g, bl, _ = rgba(c)
        attrs.insert(_attr(Pango.attr_foreground_new, at, at + n,
                           int(r * 65535), int(g * 65535), int(bl * 65535)))
        pos = L.index_to_pos(at).x / text.S
        end = L.index_to_pos(at + n).x / text.S if at + n < len(raw) else tw
        colours.append((w, Box(x0 + pos, b.y + pad_v, end - pos, lh), c))
        at += n
    L.set_attributes(attrs)
    ctx.move_to(x0, y0)
    PangoCairo.show_layout(ctx, L)
    if mark:
        cv.mark(mark, *b)
    return Drawn(b, line, tuple(colours))
