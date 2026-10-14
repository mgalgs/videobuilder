"""Shared look for the capabilities catalog's demo films. See STYLE.md."""
from pathlib import Path

import videobuilder as vb
from videobuilder import Box, text

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / 'assets'

for _f in sorted(ASSETS.glob('*.[ot]tf')):
    text.register(_f)

FAMILY = 'Inter'
MONO = 'SourceCodeVF'

FORMAT = vb.Format('cap', 720, 720)

BG = '#14151a'
INK = '#f4f4f2'
MUTED = '#9397a1'
ACCENT = '#ef5b4c'
TEAL = '#4fc3b0'
LINE = '#2a2c33'


def font(size, weight=400, family=None, **kw):
    return vb.Font(family or FAMILY, size, weight=weight, **kw)


def grid(bpm=120, head_trim=0):
    return vb.Grid(fps=30, bpm=bpm, head_trim=head_trim)


def safe(cv, pad=56):
    return Box.of(cv).pad(pad)


def text_marked(cv, name, lines, f, x, y, color, align='left', width=None, alpha=1.0):
    """`text.draw`, then `cv.mark` the box it drew."""
    box = text.draw(cv, lines, f, x, y, color, align=align, width=width, alpha=alpha)
    cv.mark(name, *box)
    return box


def rect_marked(cv, name, x, y, w, h, color, radius=0, alpha=1.0):
    """`cv.rect`, then `cv.mark` the same box."""
    cv.rect(x, y, w, h, color, radius=radius, alpha=alpha)
    cv.mark(name, x, y, w, h)


def label(cv, name, word, x, y, color=MUTED, size=22, weight=600, align='left', width=None):
    """A small caption line, marked."""
    f = font(size, weight)
    return text_marked(cv, name, text.wrap(word, f, width or 640), f, x, y, color, align=align, width=width)
