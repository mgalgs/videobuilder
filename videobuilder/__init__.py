"""videobuilder: a small framework for code-made films (cairo + Pango + ffmpeg)."""
__version__ = '0.1.76'
from .canvas import Canvas, Image, View, halftone_pattern, paper_grain, rgba
from .clip import Clip, Footage, footage
from .puppet import Puppet
from .ease import (bezier, clamp01, critical, damped, ease_in_expo, ease_in_out_quart, ease_out_back,
                   ease_out_expo, ease_out_quint, interpolate, linear, log_lerp, spring, spring_at)
from .layout import Box, fr, per_format
from .expect import seg, visible, hidden, touches, apart, still, at_rest_by
from .film import FORMATS, Audio, Film, Format, Sound, load, load_module
from .cli import film_main as main
from .text import Font
from .timeline import Grid, Segment, Shot, Timeline, round_half_up, sequence
from . import edits, layout, paths, text
from . import captions, speech

__all__ = ['Audio', 'Box', 'Canvas', 'Clip', 'FORMATS', 'Film', 'Font', 'Footage', 'Format', 'Grid', 'Image', 'Puppet',
           'Segment', 'Shot', 'Sound', 'Timeline', 'View', 'apart', 'at_rest_by', 'bezier', 'clamp01', 'critical',
           'damped', 'ease_in_expo', 'ease_in_out_quart', 'ease_out_back', 'ease_out_expo', 'ease_out_quint',
           'edits', 'footage', 'fr', 'halftone_pattern', 'hidden', 'interpolate', 'layout', 'linear', 'load',
           'load_module', 'log_lerp', 'main', 'paper_grain', 'paths', 'per_format', 'rgba', 'round_half_up', 'seg',
           'sequence', 'speech', 'spring', 'spring_at', 'still', 'text', 'touches', 'visible']
