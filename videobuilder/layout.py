"""Boxes and how to divide them: padding, rows, columns, centring, anchoring,
and fitting content of one aspect into a box of another.

Everything is a pure function of numbers. A `Box` is (x, y, w, h) in film px;
start from `Box.of(canvas)` and carve it up. No styles, no defaults that
encode taste: sizes and gaps are always the film's to choose.

One film, many formats: `per_format` picks a film's layout table entry for the
format being drawn, so 9:16, 16:9 and 1:1 are layouts of the same film, not
crops of one frame.
"""
from dataclasses import dataclass

# anchor name -> (fraction across, fraction down)
ANCHORS = {
    'top-left': (0, 0), 'top': (0.5, 0), 'top-right': (1, 0),
    'left': (0, 0.5), 'center': (0.5, 0.5), 'right': (1, 0.5),
    'bottom-left': (0, 1), 'bottom': (0.5, 1), 'bottom-right': (1, 1),
}


def _edges(p):
    """CSS shorthand: a, (v, h), (t, h, b) or (t, r, b, l) -> (t, r, b, l)."""
    if isinstance(p, (int, float)):
        return p, p, p, p
    p = tuple(p)
    if len(p) == 2:
        return p[0], p[1], p[0], p[1]
    if len(p) == 3:
        return p[0], p[1], p[2], p[1]
    if len(p) == 4:
        return p
    raise ValueError(f'padding takes 1-4 values, got {len(p)}')


@dataclass(frozen=True)
class Fr:
    """A share of the space left after fixed sizes and gaps (CSS `fr`)."""
    n: float = 1.0

    def __rmul__(self, k):
        return Fr(self.n * k)

    __mul__ = __rmul__


fr = Fr(1)


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @classmethod
    def of(cls, canvas):
        """The whole frame of a Canvas (or anything with width and height)."""
        return cls(0, 0, canvas.width, canvas.height)

    # ---- geometry ----
    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    @property
    def aspect(self):
        return self.w / self.h

    def __iter__(self):
        """Unpacks as x, y, w, h, so `canvas.rect(*box, color)` works."""
        return iter((self.x, self.y, self.w, self.h))

    def moved(self, dx=0, dy=0):
        return Box(self.x + dx, self.y + dy, self.w, self.h)

    def scaled(self, s, origin='center'):
        """Scaled by `s` about an anchor point of the box."""
        ax, ay = ANCHORS[origin]
        w, h = self.w * s, self.h * s
        return Box(self.x + (self.w - w) * ax, self.y + (self.h - h) * ay, w, h)

    # ---- carving ----
    def pad(self, *p):
        """Inset by CSS-style padding: pad(a), pad(v, h), pad(t, h, b), pad(t, r, b, l)."""
        t, r, b, l = _edges(p[0] if len(p) == 1 else p)
        return Box(self.x + l, self.y + t, max(0.0, self.w - l - r), max(0.0, self.h - t - b))

    def anchor(self, w, h, at='center', margin=0):
        """A w x h box placed at an anchor of this one, `margin` (CSS shorthand) in from the edges."""
        ax, ay = ANCHORS[at]
        inner = self.pad(margin)
        return Box(inner.x + (inner.w - w) * ax, inner.y + (inner.h - h) * ay, w, h)

    def center(self, w, h):
        return self.anchor(w, h, 'center')

    def row(self, *sizes, gap=0, justify='start'):
        """Split left to right. Sizes are px or `fr` shares; each child is full height."""
        return [Box(self.x + a, self.y, s, self.h) for a, s in _track(sizes, self.w, gap, justify)]

    def column(self, *sizes, gap=0, justify='start'):
        """Split top to bottom. Sizes are px or `fr` shares; each child is full width."""
        return [Box(self.x, self.y + a, self.w, s) for a, s in _track(sizes, self.h, gap, justify)]

    def grid(self, cols, rows, gap=0):
        """cols x rows equal cells, row-major. `gap` is one number or (row gap, column gap)."""
        gy, gx = (gap, gap) if isinstance(gap, (int, float)) else gap
        return [cell for r in self.column(*[fr] * rows, gap=gy) for cell in r.row(*[fr] * cols, gap=gx)]

    def fit(self, w, h, mode='contain', at='center'):
        """Where content of size w x h goes in this box. Modes follow CSS object-fit:
        contain (whole content, letterboxed), cover (fills, overflows), fill (stretched),
        none (natural size), scale-down (contain, but never enlarged)."""
        if mode == 'fill':
            return self
        if mode == 'none':
            s = 1.0
        else:
            sx, sy = self.w / w, self.h / h
            s = {'contain': min, 'cover': max, 'scale-down': lambda a, b: min(a, b, 1.0)}[mode](sx, sy)
        return self.anchor(w * s, h * s, at)

    def contain(self, w, h, at='center'):
        return self.fit(w, h, 'contain', at)

    def cover(self, w, h, at='center'):
        return self.fit(w, h, 'cover', at)


def _track(sizes, total, gap, justify):
    """(offset, size) of each item along one axis."""
    if not sizes:
        return []
    fixed = sum(s for s in sizes if not isinstance(s, Fr))
    shares = sum(s.n for s in sizes if isinstance(s, Fr))
    free = total - fixed - gap * (len(sizes) - 1)
    unit = max(0.0, free) / shares if shares else 0.0
    lengths = [s.n * unit if isinstance(s, Fr) else s for s in sizes]
    used = sum(lengths) + gap * (len(sizes) - 1)
    slack = max(0.0, total - used) if not shares else 0.0
    if justify == 'start':
        start, extra = 0.0, 0.0
    elif justify == 'center':
        start, extra = slack / 2, 0.0
    elif justify == 'end':
        start, extra = slack, 0.0
    elif justify == 'space-between':
        start, extra = 0.0, slack / (len(sizes) - 1) if len(sizes) > 1 else 0.0
    else:
        raise ValueError(f'unknown justify {justify!r}')
    out, a = [], start
    for n in lengths:
        out.append((a, n))
        a += n + gap + extra
    return out


def per_format(table, fmt):
    """The entry of a per-format layout table for `fmt` (a Format, its name, or a
    Canvas). Keys are format names; '*' is the fallback. When both the entry
    and the fallback are dicts they merge, the format's keys winning.

        LAYOUT = {
            '*':    dict(title=96, columns=1),
            '16x9': dict(columns=2),
        }
        L = per_format(LAYOUT, cv)   # {'title': 96, 'columns': 2} in 16:9
    """
    if not isinstance(fmt, str):
        fmt = getattr(fmt, 'format', fmt)  # a Canvas carries its Format
    name = getattr(fmt, 'name', fmt)
    base = table.get('*')
    if name in table:
        entry = table[name]
        if isinstance(entry, dict) and isinstance(base, dict):
            return {**base, **entry}
        return entry
    if base is None:
        raise KeyError(f'layout table has no entry for {name} and no "*" fallback')
    return base
