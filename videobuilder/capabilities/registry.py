"""Finding capabilities: walk each family's subpackage for modules, import one
on demand, and check it sits where its record says it does. There is no list
of capabilities anywhere; a new module is found by its file alone.
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
    return tuple(t.id for t in catalog(family))


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
    return {'id': t.id, 'name': t.name, 'family': t.family, 'group': t.group, 'aliases': list(t.aliases),
            'definition': t.definition, 'phrasings': list(t.phrasings), 'related': list(t.related),
            'api': list(t.api)}


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
