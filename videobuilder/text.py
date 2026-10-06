"""Text with real fonts: Pango (HarfBuzz shaping, variable axes) on cairo.

Lines follow the CSS line-box model, so a block laid out here lands where a
browser would put it: each line is `line_height` tall and the glyphs' content
area (ascent + descent) is centred in it.
"""
from dataclasses import dataclass
from functools import lru_cache

import cairo
import gi

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo  # noqa: E402

from .canvas import rgba  # noqa: E402
from .layout import Box, _edges  # noqa: E402

S = Pango.SCALE


def register(path):
    """Make a font file available by its family name (no system install)."""
    if not PangoCairo.FontMap.get_default().add_font_file(str(path)):
        raise RuntimeError(f'could not load font {path}')


_WEIGHTS = sorted(int(w) for w in Pango.Weight.__enum_values__.values())


def _nearest_weight(w):
    return Pango.Weight(min(_WEIGHTS, key=lambda k: abs(k - w)))


@dataclass(frozen=True)
class Font:
    family: str
    size: float  # px
    weight: int = 400  # any value on the font's wght axis
    tracking: float = 0.0  # letter-spacing, em
    line_height: float | None = None  # multiple of size; None = the font's normal
    # CSS adds letter-spacing after the last letter too; Pango doesn't. True
    # counts it in a line's width, as a browser does, so aligned and centred
    # tracked text lands where a browser puts it. Glyphs don't move.
    css_tracking: bool = False

    def description(self):
        d = Pango.FontDescription.from_string(f'{self.family} @wght={self.weight}')
        d.set_weight(_nearest_weight(self.weight))  # picks a static family's face; the axis drives variable ones
        d.set_absolute_size(self.size * S)
        return d


def _font_options():
    # Unhinted outlines and metrics: glyphs keep their true shapes and advances,
    # and text moving by fractions of a pixel moves smoothly instead of snapping.
    o = cairo.FontOptions()
    o.set_hint_metrics(cairo.HINT_METRICS_OFF)
    o.set_hint_style(cairo.HINT_STYLE_NONE)
    o.set_antialias(cairo.ANTIALIAS_GRAY)
    return o


_OPTIONS = _font_options()
_scratch = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))


def _layout(ctx, text, font):
    ctx.set_font_options(_OPTIONS)
    L = PangoCairo.create_layout(ctx)
    PangoCairo.context_set_font_options(L.get_context(), _OPTIONS)
    L.set_font_description(font.description())
    if font.tracking:
        attrs = Pango.AttrList()
        attrs.insert(Pango.attr_letter_spacing_new(int(round(font.tracking * font.size * S))))
        L.set_attributes(attrs)
    L.set_text(text, -1)
    return L


@lru_cache(maxsize=4096)
def measure(text, font):
    """Advance width of one line, px (with `css_tracking`, plus one trailing letter-spacing)."""
    w = _layout(_scratch, text, font).get_extents()[1].width / S
    if font.css_tracking and text:
        w += font.tracking * font.size
    return w


@lru_cache(maxsize=64)
def _content(font):
    """(content height, baseline) of one line: the font's ascent + descent."""
    L = _layout(_scratch, 'Hg', font)
    return L.get_extents()[1].height / S, L.get_baseline() / S


def line_height(font):
    if font.line_height is not None:
        return font.line_height * font.size
    return _content(font)[0]  # Mulish has no line gap, so normal == ascent + descent


def _break(text, font, width):
    L = _layout(_scratch, text, font)
    L.set_width(int(width * S))
    L.set_wrap(Pango.WrapMode.WORD)
    raw = text.encode()
    return [raw[ln.start_index:ln.start_index + ln.length].decode().strip() for ln in L.get_lines_readonly()]


@lru_cache(maxsize=1024)
def wrap(text, font, max_width, balance=False):
    """Lines of `text` within `max_width`. `balance`: CSS text-wrap: balance,
    i.e. the same number of lines as greedy wrapping, at the narrowest width."""
    lines = _break(text, font, max_width)
    if not balance or len(lines) < 2:
        return tuple(lines)
    lo, hi = 0.0, float(max_width)
    while hi - lo > 0.5:
        mid = (lo + hi) / 2
        if len(_break(text, font, mid)) > len(lines):
            lo = mid
        else:
            hi = mid
    return tuple(_break(text, font, hi))


def block_size(lines, font):
    return max(measure(t, font) for t in lines), line_height(font) * len(lines)


def draw(cv, lines, font, x, y, color, align='left', width=None, alpha=1.0):
    """Draw lines top-down from (x, y). `align` within `width` (default: the block's).
    Returns the Box the lines take up (widest line by the line boxes' height), for
    layout that follows the text or for `Canvas.mark`."""
    if isinstance(lines, str):
        lines = [lines]
    ctx = cv.ctx
    lh = line_height(font)
    content, _ = _content(font)
    width = width if width is not None else block_size(lines, font)[0]
    ctx.set_source_rgba(*rgba(color, alpha))
    left, right = float('inf'), float('-inf')
    for i, t in enumerate(lines):
        w = measure(t, font)
        dx = {'left': 0, 'center': (width - w) / 2, 'right': width - w}[align]
        left, right = min(left, x + dx), max(right, x + dx + w)
        ctx.move_to(x + dx, y + i * lh + (lh - content) / 2)
        PangoCairo.show_layout(ctx, _layout(ctx, t, font))
    if not lines:
        return Box(x, y, 0, 0)
    return Box(left, y, right - left, lh * len(lines))


def _lines(text):
    return [text] if isinstance(text, str) else list(text)


def box(text, font, padding=0, x=0, y=0):
    """The Box of `text` (a line, or lines) with CSS-style `padding` around it
    (px: a, (v, h), (t, h, b) or (t, r, b, l)), at (x, y): the border box of a
    label, chip or button. Its height is the line boxes plus padding, so it is
    known before anything is drawn. Draw the text in it with `draw_in`."""
    t, r, b, l = _edges(padding)
    lines = _lines(text)
    w, h = block_size(lines, font) if lines else (0.0, 0.0)
    return Box(x, y, w + (l + r), h + (t + b))


def draw_in(cv, box, text, font, color, padding=0, align='left', alpha=1.0):
    """Draw `text` inside `box` at its `padding` (as given to `text.box`),
    aligned within the padded width. Returns the Box the text took up."""
    t, r, b, l = _edges(padding)
    return draw(cv, _lines(text), font, box.x + l, box.y + t, color, align=align,
                width=box.w - l - r, alpha=alpha)
