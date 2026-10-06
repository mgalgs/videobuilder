"""videobuilder: a small framework for code-made films (cairo + Pango + ffmpeg)."""
from .canvas import Canvas, Image, View
from .ease import bezier, clamp01, critical, interpolate, linear, log_lerp, spring, spring_at
from .layout import Box, fr, per_format
from .film import FORMATS, Audio, Film, Format, load
from .text import Font
from .timeline import Grid, Segment, Shot, Timeline, round_half_up, sequence
from . import layout, text

__all__ = ['Audio', 'Box', 'Canvas', 'FORMATS', 'Film', 'Font', 'Format', 'Grid', 'Image', 'Segment', 'Shot', 'Timeline', 'View',
           'bezier', 'clamp01', 'critical', 'fr', 'interpolate', 'layout', 'linear', 'load', 'log_lerp', 'per_format',
           'round_half_up', 'sequence', 'spring', 'spring_at', 'text']
