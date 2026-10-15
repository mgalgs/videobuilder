"""The compendium's component format: typed slots, their validation, and the
metadata every component declares.

A component is a module under `videobuilder/compendium/components/` that
builds one `Component`. Its `draw(cv, shot)` is called the way a showcase
scene is: `shot` is a `videobuilder.Shot` (one segment of an ordinary
`Timeline`), `shot.data` holds the slot values already validated and
defaulted by `Component.validate`, and `shot.f` / `shot.length` give its
timing in frames. A `transition` component is the same shape; it happens to
draw a from/to pair of its own, the way `examples/capabilities/
overlap-transitions.py` does, rather than receiving neighbouring shots.
"""
from dataclasses import dataclass, field

KINDS = ('title', 'data', 'images', 'transition', 'ending')
TYPES = ('text', 'image', 'images', 'color', 'palette', 'series', 'number')


class SlotError(ValueError):
    """A slot value, or a set of slot values, that a component rejects. The
    message always names the component and the slot, and says what to do."""


def _is_number(v):
    return not isinstance(v, bool) and isinstance(v, (int, float))


def _is_color(v):
    from ..canvas import rgba
    try:
        rgba(v)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class Slot:
    """One named input a component accepts.

    `max_length` is required for `text`; `min_count`/`max_count` for `images`.
    `hint` is a short plain-language description a cheap model fills the slot
    from, without reading the component's code.
    """
    name: str
    type: str
    required: bool
    hint: str
    max_length: int | None = None
    min_count: int | None = None
    max_count: int | None = None

    def __post_init__(self):
        if self.type not in TYPES:
            raise ValueError(f"slot {self.name!r}: unknown type {self.type!r}; types are {', '.join(TYPES)}")
        if self.type == 'text' and self.max_length is None:
            raise ValueError(f"slot {self.name!r}: a text slot needs max_length")
        if self.type == 'images' and (self.min_count is None or self.max_count is None):
            raise ValueError(f"slot {self.name!r}: an images slot needs min_count and max_count")


def check_value(component_id, slot, value):
    """`value`, checked against `slot`'s type and constraints. Raises
    `SlotError` with a plain message naming the component and the slot."""
    def fail(msg):
        raise SlotError(f'{component_id}: slot {slot.name!r} {msg}')

    if slot.type == 'text':
        if not isinstance(value, str):
            fail(f'must be text, got {type(value).__name__}')
        if len(value) > slot.max_length:
            fail(f'is {len(value)} characters; the limit is {slot.max_length}')
    elif slot.type == 'number':
        if not _is_number(value):
            fail(f'must be a number, got {type(value).__name__}')
    elif slot.type == 'color':
        if not _is_color(value):
            fail(f'must be a colour (e.g. "#rrggbb"), got {value!r}')
    elif slot.type == 'palette':
        if not isinstance(value, (list, tuple)) or not value:
            fail('must be a non-empty list of colours')
        for c in value:
            if not _is_color(c):
                fail(f'has a bad colour {c!r} in its palette')
    elif slot.type == 'series':
        if not isinstance(value, (list, tuple)) or not value:
            fail('must be a non-empty list of numbers, or (label, number) pairs')
        for item in value:
            if isinstance(item, (list, tuple)):
                if len(item) != 2 or not isinstance(item[0], str) or not _is_number(item[1]):
                    fail(f'has a bad series item {item!r}; use (label, number)')
            elif not _is_number(item):
                fail(f'has a bad series item {item!r}; use a number or (label, number)')
    elif slot.type == 'image':
        from ..canvas import Image
        if not isinstance(value, Image):
            fail(f'must be an Image, got {type(value).__name__}')
    elif slot.type == 'images':
        from ..canvas import Image
        if not isinstance(value, (list, tuple)) or not all(isinstance(v, Image) for v in value):
            fail('must be a list of Images')
        if not slot.min_count <= len(value) <= slot.max_count:
            fail(f'has {len(value)} images; needs {slot.min_count} to {slot.max_count}')
    return value


@dataclass(frozen=True)
class Component:
    """A compendium component: metadata, typed slots, a sample filling for
    every slot (licence-clean, so it previews with nothing supplied), and the
    drawing itself."""
    id: str
    kind: str
    description: str
    tags: tuple
    formats: tuple
    beats: tuple
    slots: tuple
    sample: dict
    draw: object  # draw(cv, shot) -> None

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f'{self.id}: unknown kind {self.kind!r}; kinds are {", ".join(KINDS)}')
        lo, hi = self.beats
        if not (isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and 0 < lo <= hi):
            raise ValueError(f'{self.id}: beats must be (min, max) with 0 < min <= max')
        names = [s.name for s in self.slots]
        if len(names) != len(set(names)):
            raise ValueError(f'{self.id}: slot names must be unique')
        if not self.formats:
            raise ValueError(f'{self.id}: needs at least one format')
        self.validate(self.sample)  # the sample must itself be complete and valid

    def validate(self, values):
        """`values`, checked and defaulted: unknown slots and missing required
        slots raise `SlotError`; a slot left out otherwise falls back to the
        component's sample value, so a partially-filled component still
        renders. Returns a new dict naming every slot."""
        known = {s.name for s in self.slots}
        unknown = set(values) - known
        if unknown:
            raise SlotError(f'{self.id}: unknown slot(s): {", ".join(sorted(unknown))}')
        out = {}
        for slot in self.slots:
            if slot.name in values:
                out[slot.name] = check_value(self.id, slot, values[slot.name])
            elif slot.required:
                raise SlotError(f"{self.id}: slot '{slot.name}' is required ({slot.hint})")
            else:
                out[slot.name] = self.sample.get(slot.name)
        return out


@dataclass(frozen=True)
class RecipeStep:
    """One component in a `Recipe`: its slots filled, and its length in beats."""
    component: str
    beats: float
    slots: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Recipe:
    """A short declarative film: the components in order, a tempo and the
    formats it renders in. `build_film` (in `catalog.py`) turns this into an
    ordinary `videobuilder.Film`."""
    id: str
    title: str
    description: str
    bpm: float
    formats: tuple
    steps: tuple
