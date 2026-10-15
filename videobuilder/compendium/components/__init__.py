"""The seed components: one module per component, each exporting `COMPONENT`.
Add a component by adding a module here and listing it in `_MODULES`."""
import importlib

_MODULES = (
    'kinetic_title',
    'beat_pop_title',
    'bar_chart',
    'stat_counter',
    'image_showcase',
    'overlap_slide',
    'end_card',
)

CATALOG = tuple(importlib.import_module(f'.{name}', __name__).COMPONENT for name in _MODULES)
