"""The components: one module per component, each exporting `COMPONENT`.
Add a component by adding a module here; it is found by name, so no list
needs editing. `CATALOG` is ordered by kind (`schema.KINDS`), then id."""
import importlib
import pkgutil

from ..schema import KINDS

_MODULES = sorted(m.name for m in pkgutil.iter_modules(__path__) if not m.name.startswith('_'))

CATALOG = tuple(sorted((importlib.import_module(f'.{name}', __name__).COMPONENT for name in _MODULES),
                       key=lambda c: (KINDS.index(c.kind), c.id)))
