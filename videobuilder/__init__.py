"""videobuilder: a small framework for code-made films (cairo + Pango + ffmpeg)."""
__version__ = '0.1.8'
from .canvas import Canvas, Image, View, rgba
from .ease import bezier, clamp01, critical, interpolate, linear, log_lerp, spring, spring_at
from .layout import Box, fr, per_format
from .film import FORMATS, Audio, Film, Format, load, load_module
from .cli import film_main as main
from .text import Font
from .timeline import Grid, Segment, Shot, Timeline, round_half_up, sequence
from . import edits, layout, text

__all__ = ['Audio', 'Box', 'Canvas', 'FORMATS', 'Film', 'Font', 'Format', 'Grid', 'Image', 'Segment', 'Shot',
           'Timeline', 'View', 'bezier', 'clamp01', 'critical', 'edits', 'fr', 'interpolate', 'layout', 'linear', 'load',
           'load_module', 'log_lerp', 'main', 'per_format', 'rgba', 'round_half_up', 'sequence', 'spring',
           'spring_at', 'text']
