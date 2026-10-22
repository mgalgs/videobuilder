"""Techniques: named motion-design moves (an easing curve, a transition, a
text reveal, a look), each with its own short demo.

    python -m videobuilder techniques index [--json] [--family F]
    python -m videobuilder techniques build --out DIR [--only ID]... [--family F]

One technique is exactly one module, `<family>/<id with - as _>.py`, which
defines a module-level `TECHNIQUE = Technique(...)` (see `schema.py`). The
families are the subpackages here (`schema.FAMILIES`); `registry.py` finds
the modules by walking them, so adding a technique means adding its file and
nothing else. A module whose name starts with `_` is a helper, not a
technique. The technique's own code lives in its module, above the record;
when videobuilder already does the thing, the module only names and demos
the existing API. `_demo.py` is the shared demo kit; the one test for every
technique is `tests/test_techniques.py`.

Worked examples to copy: `principles/ease_out_back.py` (a thin entry for an
existing API), `principles/bounce_ease_out.py` (a new easing curve),
`transitions/dip_to_black.py` (a transition) and
`typography/scramble_decode.py` (a text reveal).
"""
from .registry import catalog, get, grouped, ids, index_data, index_json, index_markdown, load, modules
from .schema import FAMILIES, Technique

__all__ = ['FAMILIES', 'Technique', 'catalog', 'get', 'grouped', 'ids', 'index_data', 'index_json',
           'index_markdown', 'load', 'modules']
