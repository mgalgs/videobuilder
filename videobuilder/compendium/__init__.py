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
from .catalog import (CATALOG, RECIPES, build, build_recipe_film, component_film, get, get_recipe, ids,
                      index_data, index_json, index_markdown, kinds, recipe_ids)
from .schema import Component, Recipe, RecipeStep, Slot, SlotError

__all__ = ['CATALOG', 'Component', 'Recipe', 'RECIPES', 'RecipeStep', 'Slot', 'SlotError', 'build',
           'build_recipe_film', 'component_film', 'get', 'get_recipe', 'ids', 'index_data', 'index_json',
           'index_markdown', 'kinds', 'recipe_ids']
