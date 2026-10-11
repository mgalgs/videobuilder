"""Frame contracts for marked content in a film."""
from dataclasses import dataclass
import math

from .layout import Box
from .motion import sample, speed as box_speed


@dataclass(frozen=True)
class Anchor:
    segment: str
    place: str = 'start'
    offset: int = 0


def seg(name, place='start', offset=0):
    if isinstance(place, int):
        place, offset = 'start', place
    if place not in ('start', 'mid', 'end') or not isinstance(offset, int):
        raise ValueError('anchor place must be start, mid or end, with an integer offset')
    return Anchor(name, place, offset)


def resolve(at, timeline):
    if isinstance(at, int) and not isinstance(at, bool):
        return at
    if not isinstance(at, Anchor) or timeline is None:
        raise ValueError(f'cannot resolve frame {at!r} without a timeline')
    a, z = timeline.span(at.segment)
    return {'start': a, 'mid': (a + z - 1) // 2, 'end': z - 1}[at.place] + at.offset


@dataclass(frozen=True)
class Expectation:
    kind: str
    names: tuple
    at: object
    value: float = 0
    formats: tuple | None = None
    note: str = ''


def _make(kind, names, at, value=0, formats=None, note=''):
    return Expectation(kind, tuple(names), at, value, tuple(formats) if formats is not None else None, note)


def visible(mark, at, *, formats=None, note=''):
    return _make('visible', (mark,), at, formats=formats, note=note)


def hidden(mark, at, *, formats=None, note=''):
    return _make('hidden', (mark,), at, formats=formats, note=note)


def touches(a, b, at, tolerance=2, *, formats=None, note=''):
    return _make('touches', (a, b), at, tolerance, formats, note)


def apart(a, b, at, min_gap, *, formats=None, note=''):
    return _make('apart', (a, b), at, min_gap, formats, note)


def still(mark, frames, *, formats=None, note=''):
    return _make('still', (mark,), frames, formats=formats, note=note)


def at_rest_by(mark, frame, speed=0.5, *, formats=None, note=''):
    return _make('at_rest_by', (mark,), frame, speed, formats, note)


def needed(e, film):
    if e.kind == 'still':
        a, z = (resolve(x, film.timeline) for x in e.at)
        if a > z:
            raise ValueError('still range is reversed')
        return list(range(a, z + 1))
    n = resolve(e.at, film.timeline)
    if e.kind == 'at_rest_by':
        if film.timeline is None:
            z = film.frames
        else:
            segment, _ = film.timeline.at(n)
            z = film.timeline.span(segment)[1]
        return list(range(max(0, n - 1), z))
    return [n]


def _gap(a, b):
    dx = max(b.x - a.right, a.x - b.right, 0)
    dy = max(b.y - a.bottom, a.y - b.bottom, 0)
    overlap_x = min(a.right, b.right) - max(a.x, b.x)
    overlap_y = min(a.bottom, b.bottom) - max(a.y, b.y)
    if overlap_x > 0 and overlap_y > 0:
        return -min(overlap_x, overlap_y)
    return math.hypot(dx, dy)


def evaluate(e, film, fmt, frames, safe):
    """Return (passed, detail); frames maps frame numbers to mark dictionaries."""
    ns = needed(e, film)
    for n in ns:
        if not 0 <= n < film.frames:
            return False, f'f{n} outside film 0..{film.frames - 1}'
    for n in ns:
        missing = [name for name in e.names if name not in frames[n]]
        if missing and e.kind != 'hidden':
            return False, f'f{n} mark(s) {missing!r} absent'
    if e.kind == 'hidden':
        n = ns[0]
        b = frames[n].get(e.names[0])
        return (b is None, f'f{n} mark {e.names[0]!r} ' + ('absent' if b is None else f'box {b} present'))
    if e.kind == 'visible':
        n = ns[0]
        b = frames[n][e.names[0]]
        return safe.contains(b, tolerance=1), f'f{n} mark {e.names[0]!r} box {b}, safe {safe}'
    if e.kind in ('touches', 'apart'):
        n = ns[0]
        a, b = (frames[n][name] for name in e.names)
        gap = _gap(a, b)
        good = -e.value <= gap <= e.value if e.kind == 'touches' else gap >= e.value
        return good, f'f{n} marks {e.names!r} gap {gap:.2f}px, target {e.value:g}px; boxes {a}, {b}'
    speeds = [(n, box_speed(frames[n-1][e.names[0]], frames[n][e.names[0]]))
              for n in ns[1:] if n - 1 in frames and e.names[0] in frames[n-1]]
    if e.kind == 'still':
        start = frames[ns[0]][e.names[0]]
        moved = [(n, frames[n][e.names[0]]) for n in ns if frames[n][e.names[0]] != start]
        return not moved, f'f{ns[0]}..f{ns[-1]} mark {e.names[0]!r} box {start}; ' + (f'f{moved[0][0]} box {moved[0][1]}' if moved else 'unchanged')
    bad = [(n, v) for n, v in speeds if v > e.value]
    peak = max((v for _, v in speeds), default=0)
    return not bad, f'f{ns[0]}..f{ns[-1]} mark {e.names[0]!r} speed peak {peak:.2f}px/frame, limit {e.value:g}px/frame' + (f'; f{bad[0][0]} {bad[0][1]:.2f}px/frame' if bad else '')


def check(expectations, film, fmt, report, layouts=None):
    entry = (layouts or {}).get(fmt.name, (layouts or {}).get('*'))
    raw = entry.get('safe') if isinstance(entry, dict) else None
    safe = Box(*raw) if raw is not None else Box(0, 0, fmt.width, fmt.height)
    selected = [e for e in expectations if e.formats is None or fmt.name in e.formats]
    picks = set()
    for e in selected:
        try:
            picks.update(n for n in needed(e, film) if 0 <= n < film.frames)
        except (ValueError, KeyError, IndexError) as exc:
            report.fail(f'{fmt.name}: {e.kind} {e.names!r}: {exc}; note={e.note!r}')
    frames = sample(film, fmt, picks)
    # A hidden mark still needs to exist somewhere: otherwise a typo passes silently.
    missing_names = {name for e in selected for name in e.names
                     if not any(name in marks for marks in frames.values())}
    if missing_names:
        for n in range(film.frames):
            if not missing_names:
                break
            if n not in frames:
                frames.update(sample(film, fmt, [n]))
            missing_names.difference_update(frames[n])
    for e in selected:
        try:
            absent = set(e.names) & missing_names
            ok, detail = ((False, f'mark {sorted(absent)!r} never appears in any frame')
                          if absent else evaluate(e, film, fmt, frames, safe))
        except (ValueError, KeyError, IndexError) as exc:
            ok, detail = False, str(exc)
        msg = f'{fmt.name}: {e.kind} {e.names!r}: {detail}'
        if not ok and e.note:
            msg += f'; note={e.note!r}'
        (report.ok if ok else report.fail)(msg)
