"""videobuilder: a small framework for code-made films (cairo + Pango + ffmpeg)."""
__version__ = '0.1.17'
from .canvas import Canvas, Image, View, rgba
from .ease import (bezier, clamp01, critical, damped, ease_in_expo, ease_in_out_quart, ease_out_back,
                   ease_out_expo, ease_out_quint, interpolate, linear, log_lerp, spring, spring_at)
from .layout import Box, fr, per_format
from .expect import seg, visible, hidden, touches, apart, still, at_rest_by
from .film import FORMATS, Audio, Film, Format, load, load_module
from .cli import film_main as main
from .text import Font
from .timeline import Grid, Segment, Shot, Timeline, round_half_up, sequence
from . import edits, layout, text

__all__ = ['Audio', 'Box', 'Canvas', 'FORMATS', 'Film', 'Font', 'Format', 'Grid', 'Image', 'Segment', 'Shot',
           'Timeline', 'View', 'apart', 'at_rest_by', 'bezier', 'clamp01', 'critical', 'damped', 'ease_in_expo',
           'ease_in_out_quart', 'ease_out_back', 'ease_out_expo', 'ease_out_quint', 'edits', 'fr', 'hidden',
           'interpolate', 'layout', 'linear', 'load', 'load_module', 'log_lerp', 'main', 'per_format', 'rgba',
           'round_half_up', 'seg', 'sequence', 'spring', 'spring_at', 'still', 'text', 'touches', 'visible']
