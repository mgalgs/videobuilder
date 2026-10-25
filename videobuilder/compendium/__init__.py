"""The compendium: a curated library of pre-built, good-looking components a
cheap model can glue into a film without reading their code -- the format
every component follows, the seed components themselves, and a couple of
reference recipes built only from them.

    python -m videobuilder compendium index [--json]
    python -m videobuilder compendium build --out DIR [--only ID ...]

A component is one module under `components/`; see `schema.py` for the
format (`Component`, `Slot`) and `catalog.py` for the registry, the index,
and rendering previews.
"""
from .schema import Component, Recipe, RecipeStep, Slot, SlotError

_CATALOG_NAMES = ('CATALOG', 'RECIPES', 'build', 'build_recipe_film', 'component_film', 'fingerprint', 'get',
                  'get_recipe', 'ids', 'index_data', 'index_json', 'index_markdown', 'kinds', 'recipe_ids')
__all__ = ['Component', 'Recipe', 'RecipeStep', 'Slot', 'SlotError', *_CATALOG_NAMES]


def __getattr__(name):
    # The catalog imports every component, and their samples render images (text
    # and all), so it loads on first use: `compendium.kit` alone (every
    # capability demo imports it) must stay cheap.
    if name in _CATALOG_NAMES:
        from . import catalog
        return getattr(catalog, name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
