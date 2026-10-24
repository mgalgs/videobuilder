"""The capability registry: named motion-design moves (an easing curve, a
transition, a text reveal, a look), each with its own short demo.

    python -m videobuilder capabilities index [--json] [--family F]
    python -m videobuilder capabilities gallery --out DIR [--only ID]... [--family F]

One registry capability is exactly one module, `<family>/<id with - as _>.py`,
which defines a module-level `CAPABILITY = Capability(...)` (see `schema.py`).
The families are the subpackages beside this file (`schema.FAMILIES`); this
module finds them by walking the packages, so adding a capability means
adding its file and nothing else. A module whose name starts with `_` is a
helper, not a capability. The capability's own code lives in its module,
above the record; when videobuilder already does the thing, the module only
names and demos the existing API. `_demo.py` is the shared demo kit; the one
test for every registry capability is `tests/test_capabilities_registry.py`.

Worked examples to copy: `principles/ease_out_back.py` (a thin entry for an
existing API), `principles/bounce_ease_out.py` (a new easing curve),
`transitions/dip_to_black.py` (a transition) and
`typography/scramble_decode.py` (a text reveal).

A capability the editor should let the creator tune (a voice, a speed) can
carry `settings` -- see schema.py's `Capability.settings` and settings.py;
`sound/voiceover.py` is the worked example (shared with `sound/narration.py`,
so both offer the same controls). `index_data` includes a capability's
`settings` (as JSON) and its `source` (the post it came from) only when it
has them, so every other capability's index output is unchanged.

Every capability is here, the ones with a card of their own on the
/capabilities page too: those give the record's optional page fields
(`category`, `order`, `description`, `doc`, `members`, ... see schema.py)
and usually demo a worked example film (`demo=Example(path)`), e.g.
`principles/eased_entrances.py`; a capability grouping others (Looks, Type)
lists them in `members`, e.g. `vfx/looks.py`. capabilities/__init__.py reads
them for the page and the sheet.

This finds and checks every capability module; there is no list of them
anywhere else -- a new module is found by its file alone.
"""
import importlib
import json
import pkgutil
from functools import lru_cache

from .schema import FAMILIES, Capability, module_name

PACKAGE = __name__.rpartition('.')[0]


def _family_check(family):
    if family not in FAMILIES:
        raise ValueError(f'unknown family {family!r}; families are {", ".join(FAMILIES)}')


def modules(family=None):
    """`(family, module name)` for every capability module, without importing
    any of them: families in `FAMILIES` order, modules by name. A module
    whose name starts with `_` is a helper, not a capability."""
    if family is not None:
        _family_check(family)
    out = []
    for fam in FAMILIES if family is None else (family,):
        pkg = importlib.import_module(f'{PACKAGE}.{fam}')
        out += [(fam, m.name) for m in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda m: m.name)
                if not m.name.startswith('_') and not m.ispkg]
    return out


def load(family, name):
    """The `CAPABILITY` of `videobuilder.capabilities.<family>.<name>`, checked
    against where it lives: its id must be the module name with `_` as `-`,
    its family the subpackage, and every `api` name must resolve."""
    where = f'{PACKAGE}.{family}.{name}'
    mod = importlib.import_module(where)
    t = getattr(mod, 'CAPABILITY', None)
    if not isinstance(t, Capability):
        raise TypeError(f'{where} must define CAPABILITY = Capability(...)')
    if module_name(t.id) != name:
        raise ValueError(f'{where}: id {t.id!r} does not match its file; '
                         f'call it {name.replace("_", "-")!r} or rename the file to {module_name(t.id)}.py')
    if t.family != family:
        raise ValueError(f'{where}: family {t.family!r} does not match its package {family!r}')
    t.resolve_api()
    return t


@lru_cache(maxsize=None)
def _all():
    return tuple(load(fam, name) for fam, name in modules())


def catalog(family=None):
    """Every capability (or one family's), loaded and checked, in `modules` order."""
    if family is not None:
        _family_check(family)
    return tuple(t for t in _all() if family is None or t.family == family)


def get(id):
    """The capability called `id`, importing only its own module. Raises
    `KeyError` for an unknown id."""
    for fam, name in modules():
        if name == module_name(id):
            return load(fam, name)
    raise KeyError(f'no capability {id!r}')


def ids(family=None):
    """Every capability's id (or one family's), in `modules` order: read
    from the file names alone, so no module is imported (`load` checks each
    id matches its file)."""
    return tuple(name.replace('_', '-') for _, name in modules(family))


def poster_frame(t, film, default):
    """The frame `t`'s poster is taken from: its own `poster`, when the
    record gives one; for a transition, the middle of its demo's move (a
    `film.keyframes` entry labelled 'mid-transition', see
    `_demo.two_scenes`), when the demo marks one; else `default`, unchanged
    for every other capability."""
    if t.poster is not None:
        return t.poster
    if t.family == 'transitions':
        for n, label in film.keyframes:
            if label == 'mid-transition':
                return n
    return default


def grouped(capabilities):
    """`[(family, [(group, [capability, ...]), ...]), ...]`: families in
    `FAMILIES` order, groups and capabilities within them by name."""
    out = []
    for fam in FAMILIES:
        in_fam = [t for t in capabilities if t.family == fam]
        if not in_fam:
            continue
        groups = sorted({t.group for t in in_fam}, key=str.casefold)
        out.append((fam, [(g, sorted((t for t in in_fam if t.group == g), key=lambda t: t.name.casefold()))
                          for g in groups]))
    return out


# ---- the index: the builder-facing sheet, markdown or JSON ----

def _data(t):
    d = {'id': t.id, 'name': t.name, 'family': t.family, 'group': t.group, 'aliases': list(t.aliases),
         'definition': t.definition, 'phrasings': list(t.phrasings), 'related': list(t.related),
         'api': list(t.api)}
    if t.settings:
        from .settings import as_json
        d['settings'] = as_json(t.settings)
    if t.source:
        d['source'] = t.source.as_json()
    return d


def index_data(family=None):
    """The index as JSON-safe lists and dicts, grouped like `index_markdown`."""
    return {'families': [{'family': fam, 'groups': [{'group': g, 'capabilities': [_data(t) for t in ts]}
                                                     for g, ts in groups]}
                         for fam, groups in grouped(catalog(family))]}


def index_json(family=None):
    return json.dumps(index_data(family), indent=2) + '\n'


def index_markdown(family=None):
    """The builder-facing sheet: every capability's id, name, definition,
    phrasings and api, grouped by family, then group."""
    lines = ['# Capability registry', '',
             'Named motion-design capabilities, each with a short demo. Use one by calling what its `api` names; '
             'its module (`videobuilder/capabilities/<family>/<id with - as _>.py`) has a worked demo to copy.', '']
    for fam, groups in grouped(catalog(family)):
        lines += [f'## {fam}', '']
        for g, ts in groups:
            lines += [f'### {g}', '']
            for t in ts:
                aka = f" (also: {', '.join(t.aliases)})" if t.aliases else ''
                lines.append(f'- `{t.id}`: **{t.name}**{aka}. {t.definition}')
                asked = '; '.join('"' + p + '"' for p in t.phrasings)
                lines.append(f'  - asked for as: {asked}')
                lines.append(f"  - api: {', '.join(f'`{a}`' for a in t.api)}")
            lines.append('')
    return '\n'.join(lines).rstrip('\n') + '\n'
