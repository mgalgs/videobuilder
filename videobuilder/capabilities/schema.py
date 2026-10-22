"""The `Capability` record every registry module defines as `CAPABILITY`, and
the families a capability belongs to (one subpackage each).

The record is checked when it is built, so a malformed capability fails at
import with a message naming it. `api` is only format-checked here; whether
each name resolves to a real object is checked by `registry.load`, after the
module defining it has finished importing.
"""
import importlib
import re
from dataclasses import dataclass

FAMILIES = ('principles', 'typography', 'transitions', 'ui', 'shapes', 'particles', 'camera', 'vfx',
            'broadcast', 'sound')

ID_RE = re.compile(r'\A[a-z][a-z0-9]*(-[a-z0-9]+)*\Z')
DOTTED_RE = re.compile(r'\A[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+\Z')
MAX_DEFINITION = 240


def module_name(id):
    """A capability's module name: its id with `-` as `_`."""
    return id.replace('-', '_')


def resolve(dotted):
    """The object a dotted name such as `videobuilder.ease_out_back` names:
    the longest importable module prefix, then attributes from there. Raises
    `LookupError` saying which part is missing."""
    parts = dotted.split('.')
    for i in range(len(parts), 0, -1):
        name = '.'.join(parts[:i])
        try:
            obj = importlib.import_module(name)
        except ModuleNotFoundError as e:
            if e.name and not (name + '.').startswith(e.name + '.'):
                raise  # the module exists but one of its own imports is missing
            continue
        for attr in parts[i:]:
            if not hasattr(obj, attr):
                raise LookupError(f'{dotted}: {".".join(parts[:i])} has no {attr!r}')
            obj = getattr(obj, attr)
        return obj
    raise LookupError(f'{dotted}: no module {parts[0]!r}')


def _strings(owner, field, value, at_least=0):
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ValueError(f'{owner}: {field} must be a tuple of strings, not {type(value).__name__}')
    for v in value:
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f'{owner}: {field} has an empty or non-string entry {v!r}')
    if len(value) < at_least:
        raise ValueError(f'{owner}: {field} needs at least {at_least} entries, has {len(value)}')
    if len(set(value)) != len(value):
        raise ValueError(f'{owner}: {field} has duplicate entries')
    return tuple(value)


@dataclass(frozen=True)
class Capability:
    """One named motion-design capability.

    `id`: kebab-case starting with a letter, the module's filename with `_` as `-`. `family`: the
    subpackage it lives in (one of `FAMILIES`); `group`: a free-text
    sub-heading within the family ("Easing", "Wipes"). `definition`: one
    plain sentence saying what it looks like. `phrasings`: at least two
    everyday ways someone might ask for it. `related`: ids of related
    capabilities, which need not exist yet. `api`: dotted names of what a film
    calls to use it. `demo`: a no-argument callable returning a short 16:9
    `videobuilder.Film` showing the capability alone (see `_demo.py`).
    """
    id: str
    name: str
    family: str
    group: str
    definition: str
    phrasings: tuple
    api: tuple
    demo: object  # demo() -> videobuilder.Film
    aliases: tuple = ()
    related: tuple = ()

    def __post_init__(self):
        if not isinstance(self.id, str) or not ID_RE.match(self.id):
            raise ValueError(f'capability id {self.id!r} must be kebab-case starting with a letter: lowercase '
                             'letters and digits, joined by - (spell a leading number out: three-d-flip)')
        who = self.id
        for field in ('name', 'group', 'definition'):
            v = getattr(self, field)
            if not isinstance(v, str) or not v.strip() or v != v.strip():
                raise ValueError(f'{who}: {field} must be non-empty text without surrounding spaces')
        if self.family not in FAMILIES:
            raise ValueError(f'{who}: unknown family {self.family!r}; families are {", ".join(FAMILIES)}')
        if not self.definition.endswith('.') or len(self.definition) > MAX_DEFINITION:
            raise ValueError(f'{who}: definition must be one sentence ending in a full stop, '
                             f'at most {MAX_DEFINITION} characters')
        set_ = lambda k, v: object.__setattr__(self, k, v)  # noqa: E731 -- frozen: normalise lists to tuples
        set_('aliases', _strings(who, 'aliases', self.aliases))
        set_('phrasings', _strings(who, 'phrasings', self.phrasings, at_least=2))
        set_('related', _strings(who, 'related', self.related))
        set_('api', _strings(who, 'api', self.api, at_least=1))
        for r in self.related:
            if not ID_RE.match(r):
                raise ValueError(f'{who}: related id {r!r} is not kebab-case')
            if r == self.id:
                raise ValueError(f'{who}: lists itself as related')
        for a in self.api:
            if not DOTTED_RE.match(a):
                raise ValueError(f'{who}: api entry {a!r} must be a dotted name, e.g. videobuilder.ease_out_back')
        if not callable(self.demo):
            raise ValueError(f'{who}: demo must be a callable returning a videobuilder.Film')

    def resolve_api(self):
        """Every `api` name resolved to its object, in order. Raises
        `LookupError` naming the first that doesn't resolve."""
        out = []
        for a in self.api:
            try:
                out.append(resolve(a))
            except LookupError as e:
                raise LookupError(f'{self.id}: api {e}') from None
        return tuple(out)
