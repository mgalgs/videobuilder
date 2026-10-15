"""Direct edits: a `<film>.edits.toml` beside a film (`film.py` ->
`film.edits.toml`) that moves cuts and replaces on-screen copy without
touching the film's Python. Each film has its own, so films can share a
directory; a plain `edits.toml` means nothing.

    [segments.intro]
    until = 6.5            # a roll edit, in beats
    [segments.intro.data]
    title = "New copy"     # replaces a string in Segment.data

`until` rolls the boundary between a segment and its next sibling: the
segment's `until` and the sibling's `at` both move, so the film's length and
every other cut stay put. A `data` entry replaces an existing string.

Edits apply while the film's `Timeline` is built: `load_module` makes the
file active for the film it imports, and the first `Timeline` built during
that import applies it, so module-level values the film derives from its
timeline (`T.span('x')`) see the edited cuts. A Timeline built outside a film
load sees no edits.

`roll` and `set_copy` write the file, each after loading the film with the
new edits to prove they apply.
"""
import contextlib
import contextvars
import math
import os
import tomllib

from .atomic import write_atomic

SUFFIX = '.edits.toml'

_active = contextvars.ContextVar('videobuilder_edits', default=None)


def path_for(film_path):
    """The edits file of a film: `<stem>.edits.toml` beside it."""
    root, _ = os.path.splitext(os.path.abspath(film_path))
    return root + SUFFIX


class Edits:
    """The edits for one film: `segments` maps a segment name to a dict with
    an `until` (beats) and/or a `data` dict of strings. `used` turns true once
    a Timeline has applied them."""

    def __init__(self, path, segments):
        self.path = path
        self.segments = _validate(segments, path)
        self.used = False

    @classmethod
    def read(cls, path):
        """The edits in the file at `path`, or None when there is no file."""
        try:
            with open(path, 'rb') as fh:
                doc = tomllib.load(fh)
        except FileNotFoundError:
            return None
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f'{path}: {e}') from None
        extra = set(doc) - {'segments'}
        if extra:
            raise ValueError(f'{path}: unknown table {sorted(extra)[0]!r}; only [segments.<name>] tables are allowed')
        return cls(path, doc.get('segments', {}))

    def to_json(self):
        return {'path': self.path, 'segments': self.segments}


def _validate(segments, path):
    if not isinstance(segments, dict):
        raise ValueError(f'{path}: segments must be a table')
    out = {}
    for name, entry in segments.items():
        where = f'{path}: segment {name!r}'
        if not isinstance(entry, dict):
            raise ValueError(f'{where} must be a table')
        extra = set(entry) - {'until', 'data'}
        if extra:
            raise ValueError(f'{where}: unknown key {sorted(extra)[0]!r}; only until and data may be edited')
        clean = {}
        if 'until' in entry:
            v = entry['until']
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f'{where}: until must be a number of beats, not {v!r}')
            clean['until'] = int(v) if v == int(v) else v
        data = entry.get('data', {})
        if not isinstance(data, dict):
            raise ValueError(f'{where}: data must be a table')
        for k, v in data.items():
            if not isinstance(v, str):
                raise ValueError(f'{where}: data.{k} must be a string, not {v!r}')
        if data:
            clean['data'] = dict(data)
        if clean:
            out[name] = clean
    return out


@contextlib.contextmanager
def active(edits):
    """Make `edits` (an `Edits`, or None) the ones the next Timeline applies."""
    token = _active.set(edits)
    try:
        yield
    finally:
        _active.reset(token)


def take():
    """The active edits, if no Timeline has applied them yet; marks them used."""
    edits = _active.get()
    if edits is None or edits.used:
        return None
    edits.used = True
    return edits


# ---- the rules ----

def _siblings(timeline):
    """name -> (segment, its next sibling or None)."""
    out = {}

    def go(segs):
        for s, nxt in zip(segs, segs[1:] + [None]):
            out[s.name] = (s, nxt)
            go(s.children)
    go(timeline.segments)
    return out


def _roll_problem(s, nxt, until):
    """Why `s` can't end at beat `until` (moving `nxt`'s start with it), or None."""
    if nxt is None:
        return f'segment {s.name} has no next segment at its level to roll into'
    if s.children or nxt.children:
        group = s if s.children else nxt
        return f'segment {s.name}: {group.name} is a group; rolling a group boundary is not supported'
    if (until * 2) % 1:
        return f'segment {s.name}: until {until} is off the half-beat grid'
    if not s.at < until < nxt.until:
        return f'segment {s.name}: until {until} must be strictly between {s.at} and {nxt.until} (where {nxt.name} ends)'
    if s.overlap > until - s.at:
        return f'segment {s.name}: its overlap of {s.overlap} beats no longer fits its {until - s.at} beats'
    if nxt.overlap > nxt.until - until:
        return f'segment {s.name}: {nxt.name}\'s overlap of {nxt.overlap} beats no longer fits its {nxt.until - until} beats'
    return None


def rollable(timeline, name):
    """Whether segment `name`'s end can be rolled to some other half-beat."""
    s, nxt = _siblings(timeline)[name]
    if nxt is None or s.children or nxt.children:
        return False
    k = math.floor(s.at * 2) + 1
    while k / 2 < nxt.until:
        if k / 2 != s.until and _roll_problem(s, nxt, k / 2) is None:
            return True
        k += 1
    return False


def apply(timeline, edits):
    """Apply `edits` to `timeline`'s segments in place. Rolls are checked
    against the edited timeline as a whole, so their order doesn't matter."""
    where = f'{edits.path}: '
    sibs = _siblings(timeline)
    for name in edits.segments:
        if name not in sibs:
            raise ValueError(f'{where}no segment named {name!r} in the timeline')
    for name, entry in edits.segments.items():
        s = sibs[name][0]
        for k, v in entry.get('data', {}).items():
            if k not in s.data:
                raise ValueError(f'{where}segment {name}: data has no key {k!r} to override')
            if not isinstance(s.data[k], str):
                raise ValueError(f'{where}segment {name}: data.{k} is {type(s.data[k]).__name__}, not a string; only strings can be overridden')
        if entry.get('data'):
            s.data = {**s.data, **entry['data']}  # a fresh dict: the film's may be shared
    rolls = [(name, entry['until']) for name, entry in edits.segments.items() if 'until' in entry]
    for name, until in rolls:
        s, nxt = sibs[name]
        if nxt is None or s.children or nxt.children:
            raise ValueError(where + _roll_problem(s, nxt, until))
    for name, until in rolls:
        s, nxt = sibs[name]
        s.until = nxt.at = until
    for name, until in rolls:
        problem = _roll_problem(*sibs[name], until)
        if problem:
            raise ValueError(where + problem)


# ---- writing ----

def _key(k):
    if k and all(c.isascii() and (c.isalnum() or c in '-_') for c in k):
        return k
    return _string(k)


_ESCAPES = {'"': '\\"', '\\': '\\\\', '\b': '\\b', '\t': '\\t', '\n': '\\n', '\f': '\\f', '\r': '\\r'}


def _string(s):
    out = []
    for c in s:
        if c in _ESCAPES:
            out.append(_ESCAPES[c])
        elif ord(c) < 0x20 or ord(c) == 0x7f:
            out.append(f'\\u{ord(c):04x}')
        else:
            out.append(c)
    return '"' + ''.join(out) + '"'


def dumps(segments):
    """The TOML text of `segments`, deterministic: segments and keys sorted,
    one table per segment and one for its data."""
    blocks = []
    for name in sorted(segments):
        entry = segments[name]
        head = f'segments.{_key(name)}'
        if 'until' in entry:
            blocks.append(f'[{head}]\nuntil = {entry["until"]!r}\n')
        if entry.get('data'):
            lines = ''.join(f'{_key(k)} = {_string(v)}\n' for k, v in sorted(entry['data'].items()))
            blocks.append(f'[{head}.data]\n{lines}')
    return '\n'.join(blocks)


def _write(path, segments):
    if not segments:
        with contextlib.suppress(FileNotFoundError):
            os.remove(path)
        return
    write_atomic(path, dumps(segments))


def _load(film_path, segments):
    """The film loaded with exactly these edits (none from disk). Its helper
    modules are imported afresh: Segments they hold were edited in place."""
    from .film import forget_neighbours, load_module
    forget_neighbours(film_path)
    return load_module(film_path, edits=Edits(path_for(film_path), segments))


def _timeline(film_path, segments):
    film = getattr(_load(film_path, segments), 'FILM', None)
    tl = getattr(film, 'timeline', None)
    if tl is None:
        raise ValueError(f'{film_path} has no timeline to edit')
    return tl


def _current(film_path):
    edits = Edits.read(path_for(film_path))
    return edits.segments if edits else {}


def timeline(film_path):
    """The film's Timeline with its edits file applied, loaded afresh."""
    return _timeline(film_path, _current(film_path))


def change_text(film_path, segment, field, key, value):
    """Set (or, at the film's own value, remove) one edit, after proving the
    film loads with it. Returns the new edits."""
    segments = _current(film_path)
    entry = segments.setdefault(segment, {})
    if field == 'until':
        entry.pop('until', None)
    else:
        entry.get('data', {}).pop(key, None)
        if not entry.get('data'):
            entry.pop('data', None)
    if not entry:
        del segments[segment]
    # The film's own value, with every other edit in place.
    tl = _timeline(film_path, segments)
    try:
        s = tl.find(segment)
    except KeyError:
        raise ValueError(f'{film_path}: no segment named {segment!r} in the timeline') from None
    original = s.until if field == 'until' else s.data.get(key)
    if value != original:
        entry = segments.setdefault(segment, {})
        if field == 'until':
            entry['until'] = value
        else:
            entry.setdefault('data', {})[key] = value
        segments = Edits(path_for(film_path), segments).segments  # normalised as read back
        _timeline(film_path, segments)
    return dumps(segments)


def _change(film_path, segment, field, key, value):
    content = change_text(film_path, segment, field, key, value)
    _write(path_for(film_path), tomllib.loads(content).get('segments', {}) if content else {})
    return _current(film_path)


def roll(film_path, segment, until):
    """Move the cut at the end of `segment` to beat `until`, moving its next
    sibling's start with it. Setting the film's own value removes the edit.
    Raises ValueError, leaving the edits file unchanged, if the film won't load."""
    if isinstance(until, bool) or not isinstance(until, (int, float)):
        raise ValueError(f'until must be a number of beats, not {until!r}')
    return _change(film_path, segment, 'until', None, until)


def set_copy(film_path, segment, key, value):
    """Replace the string `data[key]` of `segment`. Setting the film's own
    value removes the edit. Raises ValueError, leaving the edits
    file unchanged, if the film won't load."""
    if not isinstance(value, str):
        raise ValueError(f'copy must be a string, not {value!r}')
    return _change(film_path, segment, 'data', key, value)
