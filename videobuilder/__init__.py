"""videobuilder: a small framework for code-made films (cairo + Pango + ffmpeg)."""
__version__ = '0.1.96'
from .canvas import Canvas, Image, View, halftone_pattern, paper_grain, rgba
from .clip import Clip, Footage, footage
from .puppet import Puppet
from .stick import Stick
from .ease import (bezier, clamp01, critical, damped, ease_in_expo, ease_in_out_quart, ease_out_back,
                   ease_out_expo, ease_out_quint, interpolate, linear, log_lerp, spring, spring_at)
from .layout import Box, fr, per_format
from .expect import seg, visible, hidden, touches, apart, still, at_rest_by
from .film import FORMATS, Audio, Film, Format, Sound, load, load_module
from .cli import film_main as main
from .text import Font
from .timeline import Grid, Segment, Shot, Timeline, round_half_up, sequence
from . import edits, impact, layout, parallax, paths, text
from . import captions, sfx, speech, stick

__all__ = ['Audio', 'Box', 'Canvas', 'Clip', 'FORMATS', 'Film', 'Font', 'Footage', 'Format', 'Grid', 'Image', 'Puppet',
           'Segment', 'Shot', 'Sound', 'Stick', 'Timeline', 'View', 'apart', 'at_rest_by', 'bezier', 'clamp01', 'critical',
           'damped', 'ease_in_expo', 'ease_in_out_quart', 'ease_out_back', 'ease_out_expo', 'ease_out_quint',
           'edits', 'footage', 'fr', 'halftone_pattern', 'hidden', 'impact', 'interpolate', 'layout', 'linear', 'load',
           'load_module', 'log_lerp', 'main', 'paper_grain', 'parallax', 'paths', 'per_format', 'rgba', 'round_half_up', 'seg',
           'sequence', 'sfx', 'speech', 'spring', 'stick', 'spring_at', 'still', 'text', 'touches', 'visible']


def __getattr__(name):
    # `vb.type` (the Type family) loads on first use, so a film that never
    # asks for a type style doesn't pay for it. Not in __all__: `import *`
    # must not shadow the builtin `type`.
    if name == 'type':
        import importlib
        return importlib.import_module('.type', __name__)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
