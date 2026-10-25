"""The components: one module per component, each exporting `COMPONENT`.
Add a component by adding a module here; it is found by name, so no list
needs editing. `CATALOG` is ordered by kind (`schema.KINDS`), then id."""
import importlib
import pkgutil

from ..schema import KINDS

_MODULES = sorted(m.name for m in pkgutil.iter_modules(__path__) if not m.name.startswith('_'))



def __getattr__(name):
    # Every component's sample renders images (text and all) when its module
    # loads, so CATALOG is built on first use: importing one component, or a
    # helper such as `_images_util`, loads only that.
    if name == 'CATALOG':
        global CATALOG
        CATALOG = tuple(sorted((importlib.import_module(f'.{n}', __name__).COMPONENT for n in _MODULES),
                               key=lambda c: (KINDS.index(c.kind), c.id)))
        return CATALOG
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
