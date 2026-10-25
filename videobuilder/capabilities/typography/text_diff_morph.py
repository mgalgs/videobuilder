"""Text Diff Morph: a line of text flies apart into its old and new reading,
removed words striking through and fading, kept words sliding to their new
place, new words writing in from the left.

The word-level diff is plain data (`ops`, `pair_rows`, `line_edits`): old and
new lines tokenised into words, whitespace and punctuation, matched with
`difflib`, so a caller can also drive its own drawing. `draw_segment` is a
self-contained renderer for a block of lines, needing nothing else -- no
pane, no buffer, just text, a font and a colour.
"""
import difflib
import re
from collections import Counter

import videobuilder as vb
from videobuilder import text as vbtext

from .. import _demo as demo
from ..schema import Capability

TOKEN = re.compile(r'\w+|\s+|[^\w\s]')
MAX_TOKENS = 4000   # per side; the matcher is quadratic and a screenful never gets near this


def tokens(lines):
    """[(row, col, text)] of `lines` (tabs already expanded), with a newline
    token closing each line so the diff keeps line structure."""
    out = []
    for row, line in enumerate(lines):
        for m in TOKEN.finditer(line):
            out.append((row, m.start(), m.group()))
        out.append((row, len(line), '\n'))
    return out


PAIR_SHARE = 0.4   # an old and a new line sharing this much of their words are one line edited


def _diff(a, b):
    """[[kind, old row, old col, new row, new col, text]] of token lists `a`
    and `b` (see `ops`), whitespace included."""
    sm = difflib.SequenceMatcher(None, [t for _, _, t in a], [t for _, _, t in b], autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            out += [['equal', *a[i][:2], *b[j][:2], a[i][2]] for i, j in zip(range(i1, i2), range(j1, j2))]
            continue
        if tag in ('delete', 'replace'):
            out += [['delete', *a[i][:2], -1, -1, a[i][2]] for i in range(i1, i2)]
        if tag in ('insert', 'replace'):
            out += [['insert', -1, -1, *b[j][:2], b[j][2]] for j in range(j1, j2)]
    return out


def _size(line):
    return sum(1 for m in TOKEN.finditer(line) if m.group().strip())


def _pairs(old_lines, new_lines, raw):
    """[(old row, new row)] in order: the lines that are one line edited (they
    share at least PAIR_SHARE of their words in the diff `raw`), most shared
    words first."""
    shared = Counter((o[1], o[3]) for o in raw if o[0] == 'equal' and o[5].strip())
    pairs = []
    for (i, j), c in sorted(shared.items(), key=lambda kv: (-kv[1], kv[0])):
        if c < max(1.0, PAIR_SHARE * max(_size(old_lines[i]), _size(new_lines[j]))):
            continue
        if all((pi - i) * (pj - j) > 0 for pi, pj in pairs):
            pairs.append((i, j))
    return sorted(pairs)


def pair_rows(old_lines, new_lines):
    """[(old row, new row)]: the lines of a replaced run that are one line edited."""
    a, b = tokens(old_lines), tokens(new_lines)
    if not a or not b or len(a) > MAX_TOKENS or len(b) > MAX_TOKENS:
        return []
    return _pairs(old_lines, new_lines, _diff(a, b))


def ops(old_lines, new_lines):
    """[[kind, old row, old col, new row, new col, text]] with kind `equal`,
    `delete` or `insert`, rows and cols 0-based within the runs, -1 on the side
    a token is not on; in reading order of the new side, deletions of a
    replaced stretch before its insertions. None when a side has more than
    MAX_TOKENS tokens (too much to morph).

    Words are matched only within a line edited (an old and a new line that
    share enough words, `pair_rows`): a line with no such partner is wholly
    removed or wholly new, so a `(` or `self` never flies from one line to
    another."""
    a, b = tokens(old_lines), tokens(new_lines)
    if len(a) > MAX_TOKENS or len(b) > MAX_TOKENS:
        return None
    pairs = _pairs(old_lines, new_lines, _diff(a, b)) if a and b else []
    out = []
    i = j = 0

    def gone(upto):
        nonlocal i
        for r in range(i, upto):
            out.extend(['delete', r, c, -1, -1, t] for _, c, t in tokens([old_lines[r]]) if t != '\n')
        i = max(i, upto)

    def fresh(upto):
        nonlocal j
        for r in range(j, upto):
            out.extend(['insert', -1, -1, r, c, t] for _, c, t in tokens([new_lines[r]]) if t != '\n')
        j = max(j, upto)

    for pi, pj in pairs:
        gone(pi)
        fresh(pj)
        for o in _diff(tokens([old_lines[pi]])[:-1], tokens([new_lines[pj]])[:-1]):
            o[1], o[3] = (pi if o[1] >= 0 else -1), (pj if o[3] >= 0 else -1)
            out.append(o)
        i, j = pi + 1, pj + 1
    gone(len(old_lines))
    fresh(len(new_lines))
    return [o for o in out if o[5].strip()]


def line_edits(old, new):
    """How one line becomes another, word by word: [(col, delete, insert)] left
    to right, `col` in the old line, `delete` the columns removed there and
    `insert` the text put in their place. Whitespace counts here (unlike
    `ops`), so applying the edits gives `new` exactly."""
    a = [t for _, _, t in tokens([old])][:-1]
    b = [t for _, _, t in tokens([new])][:-1]
    cols = [0]
    for t in a:
        cols.append(cols[-1] + len(t))
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return [(cols[i1], cols[i2] - cols[i1], ''.join(b[j1:j2]))
            for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal']


# The morph's phases, as fractions of its one progress: removed words dissolve
# (struck through as they go), kept words glide old -> new, wholly new lines
# wipe in (ARRIVE), the words changed on an edited line decode briefly
# (DECODE), all of them underlined from UNDERLINE_AT.
DISSOLVE = (0.0, 0.4)
GLIDE = (0.15, 0.5)
ARRIVE = (0.45, 0.8)
DECODE = (0.5, 0.78)
UNDERLINE_AT = 0.6
STRIKE_IN = 0.1   # of DISSOLVE's progress: the standalone renderer's strike fades in over this


def morph_phase(p, span):
    """`p` rescaled to 0 -> 1 over `span` (a, b) of the morph's own progress,
    clamped at both ends."""
    a, b = span
    return vb.clamp01((p - a) / (b - a))


def token_spans(items):
    """(row, first col, end col) per run of `items` [(row, col, text)] on a
    row with at most a one-column gap between them: one strike or underline
    per phrase."""
    out = []
    for row, col, text in sorted(items):
        if out and out[-1][0] == row and col - out[-1][2] <= 1:
            out[-1][2] = max(out[-1][2], col + len(text))
        else:
            out.append([row, col, col + len(text)])
    return out


def _offsets(line, font):
    """Pixel width of each prefix of `line`, i.e. the x of each column (one
    more entry than characters, for the line's end). Prefixes, not summed
    per-character widths, so a proportional font's kerning keeps every word
    where a plain draw of the whole line puts it."""
    return [0.0] + [vbtext.measure(line[:i], font) for i in range(1, len(line) + 1)]


def _crossfade(cv, x, y, font, old_lines, new_lines, p, color):
    """The fallback when the texts are too big to diff (`ops` is None): old
    fades out as new fades in."""
    lh = vbtext.line_height(font)
    for lines, a in ((old_lines, 1 - p), (new_lines, p)):
        if a > 0:
            for row, line in enumerate(lines):
                vbtext.draw(cv, [line], font, x, y + row * lh, color, alpha=a)


def draw_segment(cv, x, y, font, old_lines, new_lines, p, color, removed_color=None, added_color=None,
                  underline_color=None, diff_ops=None):
    """Draw `old_lines` (a list of strings) morphing into `new_lines` from
    top-left (x, y) at progress `p` (0 -> 1): exactly `old_lines` at 0,
    exactly `new_lines` at 1. Kept words glide from their old row and column
    to their new one; removed words strike through and fade out; new words
    wipe in from the left and end up underlined. `diff_ops` reuses an
    already-computed `ops(old_lines, new_lines)`, to skip recomputing it
    every frame; the default computes it. Texts too big to diff (`ops`
    returns None) crossfade instead. Returns the Box of the block."""
    p = vb.clamp01(p)
    diff = ops(old_lines, new_lines) if diff_ops is None else diff_ops
    lh = vbtext.line_height(font)
    removed_color = removed_color or color
    added_color = added_color or color
    underline_color = underline_color or color
    old_off = [_offsets(s, font) for s in old_lines]
    new_off = [_offsets(s, font) for s in new_lines]
    ge = vb.ease_in_out_quart(morph_phase(p, GLIDE))
    dq = morph_phase(p, DISSOLVE)
    wq = vb.ease_out_quint(morph_phase(p, ARRIVE))
    rows = max(len(old_lines), len(new_lines), 1)
    w = max([o[-1] for o in old_off] + [o[-1] for o in new_off] + [0.0])
    box = vb.Box(x, y, w, rows * lh)
    if diff is None:
        _crossfade(cv, x, y, font, old_lines, new_lines, p, color)
        return box
    with cv.clip(*box):
        for kind, orow, ocol, nrow, ncol, text in diff:
            if kind != 'equal':
                continue
            ox, nx = old_off[orow][ocol], new_off[nrow][ncol]
            oy, ny = orow * lh, nrow * lh
            vbtext.draw(cv, [text], font, x + ox + (nx - ox) * ge, y + oy + (ny - oy) * ge, color)
        gone = [o for o in diff if o[0] == 'delete']
        if gone and dq < 1:
            for row in sorted({o[1] for o in gone}):
                words = [o for o in gone if o[1] == row]
                ry = y + row * lh
                for _, _, ocol, _, _, text in words:
                    vbtext.draw(cv, [text], font, x + old_off[row][ocol], ry, removed_color, alpha=1 - dq)
                # the strike rises from nothing as the dissolve starts, so p=0 is the
                # plain old text and a film can cut from it to the morph without a pop
                strike = min(1.0, dq / STRIKE_IN) * (1 - dq)
                for r, c0, c1 in token_spans([(row, o[2], o[5]) for o in words]):
                    sy = ry + lh * 0.55
                    cv.line(x + old_off[r][c0] - 1, sy, x + old_off[r][c1] + 1, sy, removed_color,
                            width=2, alpha=strike)
        added = [o for o in diff if o[0] == 'insert']
        if added and wq > 0:
            for row in sorted({o[3] for o in added}):
                words = [o for o in added if o[3] == row]
                ry = y + row * lh
                c0, c1 = min(o[4] for o in words), max(o[4] + len(o[5]) for o in words)
                rx0, rx1 = x + new_off[row][c0], x + new_off[row][c1]
                with cv.clip(rx0, ry, max(0.0, (rx1 - rx0) * wq), lh):
                    for _, _, _, _, ncol, text in words:
                        vbtext.draw(cv, [text], font, x + new_off[row][ncol], ry, added_color)
            if p >= UNDERLINE_AT:
                a = morph_phase(p, (UNDERLINE_AT, 1.0))
                for row, c0, c1 in token_spans([(o[3], o[4], o[5]) for o in added]):
                    uy = y + row * lh + lh * 0.86
                    cv.line(x + new_off[row][c0], uy, x + new_off[row][c1], uy, underline_color,
                            width=2, alpha=a)
    return box


def draw(n, cv):
    f = demo.mono(46, 600)
    old, new = ['    return x + 1'], ['    return x * 2']
    p = demo.phase(n, 0.3, 2.6)
    x, y = demo.W / 2 - 220, demo.H / 2 - vbtext.line_height(f) / 2
    box = draw_segment(cv, x, y, f, old, new, p, demo.INK, removed_color=demo.ACCENT, added_color=demo.TEAL,
                       underline_color=demo.TEAL)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='text-diff-morph',
    name='Text diff morph',
    family='typography',
    group='Code and diffs',
    aliases=('word diff morph', 'diff text animation', 'code edit morph', 'before/after text morph'),
    definition='Old text and new text are compared word by word: removed words strike through and fade, '
               'kept words slide to their new spot and new words write in, underlined once settled.',
    phrasings=('morph this line of code into the edited version, word by word',
               'show the diff by sliding the kept words and fading the removed ones',
               'animate the before and after of this edit instead of just cutting between them'),
    related=('wipe-reveal', 'scramble-decode', 'highlighter-swipe', 'code-pane'),
    api=('videobuilder.capabilities.typography.text_diff_morph.draw_segment',
         'videobuilder.capabilities.typography.text_diff_morph.ops',
         'videobuilder.capabilities.typography.text_diff_morph.pair_rows',
         'videobuilder.capabilities.typography.text_diff_morph.line_edits'),
    demo=lambda: demo.film(draw),
)
