"""A beat grid: segments are written in beats, frames are derived."""
import math
from dataclasses import dataclass, field


def round_half_up(x):
    """JS Math.round. Python's round() is banker's: round(487.5) == 488 but
    round(502.5) == 502, which would move a half-beat cut by a frame."""
    return math.floor(x + 0.5)


@dataclass(frozen=True)
class Grid:
    fps: int = 30
    bpm: float = 120.0
    # Frames of audio skipped at the head, so the track's beats land on the grid.
    head_trim: int = 0

    @property
    def frames_per_beat(self):
        return self.fps * 60 / self.bpm

    def b(self, beat):
        """Frame of a (possibly fractional) beat."""
        return round_half_up(beat * self.frames_per_beat)

    def seconds(self, frames):
        return frames / self.fps


@dataclass
class Segment:
    name: str
    at: float  # beat
    until: float  # beat
    data: dict = field(default_factory=dict)


class Timeline:
    """Ordered, gap-free segments on a grid. `at(frame)` finds the live one."""

    def __init__(self, grid, segments, end):
        self.grid = grid
        self.segments = sorted(segments, key=lambda s: s.at)
        self.end = end
        for s, nxt in zip(self.segments, self.segments[1:] + [None]):
            stop = nxt.at if nxt else end
            if s.until != stop:
                raise ValueError(f'segment {s.name} ends at beat {s.until}, next starts at {stop}')
            if (s.at * 2) % 1:
                raise ValueError(f'segment {s.name} starts off the half-beat grid')

    @property
    def frames(self):
        return self.grid.b(self.end)

    def at(self, frame):
        b = self.grid.b
        for s in self.segments:
            if b(s.at) <= frame < b(s.until):
                return s, frame - b(s.at)
        raise IndexError(frame)

    def cut_frames(self):
        return [self.grid.b(s.at) for s in self.segments]
