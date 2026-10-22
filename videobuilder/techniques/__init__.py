"""Compatibility shim. "Technique" was renamed to "capability" and this
package moved to videobuilder.capabilities; this module stays so a film
written before the rename, which may still import videobuilder.techniques.*
or an old dotted api path, keeps working. It carries no logic of its own.
"""
import importlib
import sys

_SUBMODULES = ('_demo', 'gallery', 'registry', 'schema',
               'broadcast', 'camera', 'particles', 'principles', 'shapes',
               'sound', 'transitions', 'typography', 'ui', 'vfx')

for _name in _SUBMODULES:
    sys.modules[f'{__name__}.{_name}'] = importlib.import_module(f'videobuilder.capabilities.{_name}')

from .schema import FAMILIES, Capability as Technique
from .registry import catalog, get, grouped, ids, index_data, index_json, index_markdown, load, modules

__all__ = ['FAMILIES', 'Technique', 'catalog', 'get', 'grouped', 'ids', 'index_data', 'index_json',
           'index_markdown', 'load', 'modules']
