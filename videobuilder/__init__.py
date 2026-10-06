"""videobuilder: a small framework for code-made films (cairo + Pango + ffmpeg)."""
from .canvas import Canvas, Image
from .ease import bezier, critical, interpolate, linear, log_lerp, spring, spring_at
from .film import FORMATS, Audio, Film, Format, load
from .text import Font
from .timeline import Grid, Segment, Timeline, round_half_up
from . import text

__all__ = ['Audio', 'Canvas', 'FORMATS', 'Film', 'Font', 'Format', 'Grid', 'Image', 'Segment', 'Timeline',
           'bezier', 'critical', 'interpolate', 'linear', 'load', 'log_lerp', 'round_half_up', 'spring',
           'spring_at', 'text']
