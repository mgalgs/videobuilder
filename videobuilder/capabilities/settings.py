"""A capability's settings: a short declaration of the controls the editor
shows as a card beside its chip (a voice picker, a speed dial) -- always
plain data, never UI code. A capability (the hand-written catalog's `_entry`
or the registry's `Capability`) carries a `settings` tuple of `Choice`/
`Number` instances; the editor's settings-card component (settings_card.js)
renders whatever it finds there, and `validate` turns a note's raw
`{id: value}` dict into one safe to act on.

Keep the type set small: add a new one only once a capability actually
needs it, not speculatively.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Option:
    """One of a `Choice`'s options: `label` shown in the picker, `value`
    stored and sent to the builder, `preview` an optional URL that plays a
    short sample of it (a voice saying a line, say)."""
    label: str
    value: str
    preview: str = None

    def __post_init__(self):
        if not self.label.strip() or not str(self.value).strip():
            raise ValueError(f'option {self.value!r}: label and value must be non-empty')


@dataclass(frozen=True)
class Choice:
    """A setting picked from a fixed list, e.g. narration's voice."""
    id: str
    label: str
    options: tuple
    default: str

    def __post_init__(self):
        if not self.id.strip() or not self.label.strip():
            raise ValueError('a choice needs a non-empty id and label')
        object.__setattr__(self, 'options', tuple(self.options))
        if not self.options:
            raise ValueError(f'{self.id}: needs at least one option')
        if any(not isinstance(o, Option) for o in self.options):
            raise ValueError(f'{self.id}: options must be Option instances')
        if self.default not in {o.value for o in self.options}:
            raise ValueError(f'{self.id}: default {self.default!r} is not one of its options')

    def clamp(self, value):
        """`value` if it names one of `options`, else the default. A list
        membership check, not a set, so an unhashable `value` (a note's raw
        JSON can carry anything) falls through to the default instead of
        raising."""
        return value if value in [o.value for o in self.options] else self.default


@dataclass(frozen=True)
class Number:
    """A setting dialed within a range, e.g. narration's speed."""
    id: str
    label: str
    min: float
    max: float
    step: float
    default: float

    def __post_init__(self):
        if not self.id.strip() or not self.label.strip():
            raise ValueError('a number needs a non-empty id and label')
        if not self.min < self.max:
            raise ValueError(f'{self.id}: min must be less than max')
        if self.step <= 0:
            raise ValueError(f'{self.id}: step must be positive')
        if not self.min <= self.default <= self.max:
            raise ValueError(f'{self.id}: default {self.default!r} is out of range')

    def clamp(self, value):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return self.default
        return min(self.max, max(self.min, v))


def check(owner, settings):
    """`settings` as a tuple, checked: every entry a `Choice` or `Number`,
    ids unique. Raises `ValueError` naming `owner` otherwise."""
    settings = tuple(settings)
    for s in settings:
        if not isinstance(s, (Choice, Number)):
            raise ValueError(f'{owner}: settings entries must be a Choice or Number, not {type(s).__name__}')
    ids = [s.id for s in settings]
    if len(ids) != len(set(ids)):
        raise ValueError(f'{owner}: settings has duplicate ids')
    return settings


def validate(settings, values):
    """A note's raw `values` ({id: value}, or anything else) narrowed to one
    entry per declared setting: an unknown key dropped, a number clamped
    into range, an unknown choice value replaced by its default, and a
    missing one filled in with its default."""
    values = values if isinstance(values, dict) else {}
    return {s.id: s.clamp(values[s.id]) if s.id in values else s.default for s in settings}


def non_default(settings, values):
    """`values` validated against `settings` (validate), narrowed to the
    entries that actually differ from their own setting's default -- what a
    note should store, so a chip nobody touched looks exactly like one with
    no settings at all."""
    validated = validate(settings, values)
    return {s.id: validated[s.id] for s in settings if validated[s.id] != s.default}


def as_json(settings):
    """`settings` as JSON-safe dicts, in declaration order, for an API
    response (see video_api.py's suggest catalog and the registry index)."""
    out = []
    for s in settings:
        if isinstance(s, Choice):
            options = [{'label': o.label, 'value': o.value, **({'preview': o.preview} if o.preview else {})}
                      for o in s.options]
            out.append({'type': 'choice', 'id': s.id, 'label': s.label, 'default': s.default, 'options': options})
        else:
            out.append({'type': 'number', 'id': s.id, 'label': s.label, 'min': s.min, 'max': s.max,
                       'step': s.step, 'default': s.default})
    return out
