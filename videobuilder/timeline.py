"""A beat grid: segments are written in beats, frames are derived.

A timeline is a list of gap-free segments. A segment may be a **group** that
holds child segments (themselves gap-free and filling it), and a segment may
**overlap** the one before it: it starts on its own beat, and the previous
segment keeps drawing under it for `overlap` more beats. Hard cuts are where
a segment, at any level, starts without an overlap.
"""
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
    """`at` to `until`, in beats. `children`: segments that fill this one, gap-free,
    making it a group. `overlap`: beats the previous segment keeps drawing under
    this one after this one starts (a transition, not a cut)."""
    name: str
    at: float  # beat
    until: float  # beat
    data: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    overlap: float = 0

    def __post_init__(self):
        self.children = sorted(self.children, key=lambda s: s.at)


def sequence(at, parts):
    """Segments back to back from beat `at`: `parts` holds (name, beats) or
    (name, beats, data) items. Handy for a group's children."""
    out = []
    for name, beats, *data in parts:
        out.append(Segment(name, at, at + beats, data[0] if data else {}))
        at += beats
    return out


@dataclass(frozen=True)
class Shot:
    """One segment drawing at a frame (see `Timeline.live`).

    `f` counts frames from the segment's start; past its end it keeps counting,
    for a segment still drawing under the next one's overlap. `length` is the
    segment's own length in frames. `parents` holds (group, frames into it) pairs,
    outermost first. `exit` is None, or, in an overlap, frames since the next
    segment started over this one.
    """
    segment: Segment
    f: int
    length: int
    parents: tuple = ()
    exit: int | None = None

    @property
    def name(self):
        return self.segment.name

    @property
    def data(self):
        return self.segment.data

    @property
    def group(self):
        """The innermost group holding this segment, or None."""
        return self.parents[-1][0] if self.parents else None

    @property
    def group_f(self):
        """Frames into `group` (None at the top level)."""
        return self.parents[-1][1] if self.parents else None


def _check(segments, start, end, where):
    for s, nxt in zip(segments, segments[1:] + [None]):
        stop = nxt.at if nxt else end
        if s.until != stop:
            raise ValueError(f'segment {s.name} ends at beat {s.until}, next starts at {stop}{where}')
        if (s.at * 2) % 1:
            raise ValueError(f'segment {s.name} starts off the half-beat grid')
        if s.overlap < 0 or s.overlap > s.until - s.at:
            raise ValueError(f'segment {s.name}: overlap {s.overlap} must be 0 to its length ({s.until - s.at} beats)')
        if s.children:
            _check(s.children, s.at, s.until, f' (in group {s.name})')
    if segments and segments[0].at != start:
        raise ValueError(f'segment {segments[0].name} starts at beat {segments[0].at}, not {start}{where}')
    if segments and segments[0].overlap:
        raise ValueError(f'segment {segments[0].name} overlaps, but nothing comes before it{where}')


class Timeline:
    """Gap-free segments on a grid, optionally grouped and overlapping.
    `at(frame)` finds the frontmost live segment; `live(frame)` all that draw."""

    def __init__(self, grid, segments, end):
        self.grid = grid
        self.segments = sorted(segments, key=lambda s: s.at)
        self.end = end
        if self.segments:
            _check(self.segments, self.segments[0].at, end, '')
        seen = set()
        for s, _ in self.walk():
            if s.name in seen:
                raise ValueError(f'two segments are named {s.name!r}; names must be unique, groups and children included')
            seen.add(s.name)

    @property
    def frames(self):
        return self.grid.b(self.end)

    def span(self, seg):
        """(first frame, end frame) of a segment or segment name; the end is
        exclusive and ignores any overlap."""
        if isinstance(seg, str):
            seg = self.find(seg)
        return self.grid.b(seg.at), self.grid.b(seg.until)

    def start(self, seg):
        """First frame of a segment or segment name."""
        return self.span(seg)[0]

    def find(self, name):
        for s, _ in self.walk():
            if s.name == name:
                return s
        raise KeyError(name)

    def walk(self):
        """(segment, parent groups) for every segment, groups before their children."""
        def go(segs, parents):
            for s in segs:
                yield s, parents
                yield from go(s.children, parents + (s,))
        return go(self.segments, ())

    def leaves(self):
        """The segments that hold no children, in order."""
        return [s for s, _ in self.walk() if not s.children]

    def live(self, frame):
        """Every segment drawing at `frame`, as `Shot`s, back to front: a segment
        still drawing under the next one's overlap comes first. Groups are
        resolved to the child live inside them."""
        if not 0 <= frame < self.frames:
            raise IndexError(frame)
        return self._level(self.segments, frame, (), None)

    def _shots(self, s, n, parents, exit, tail=False):
        b = self.grid.b
        if not s.children:
            return [Shot(s, n - b(s.at), b(s.until) - b(s.at), parents, exit)]
        parents = parents + ((s, n - b(s.at)),)
        if tail:  # past its end, under an overlap: its last child keeps going
            return self._shots(s.children[-1], n, parents, exit, tail=True)
        return self._level(s.children, n, parents, exit)

    def _level(self, segs, n, parents, exit):
        b = self.grid.b
        for i, s in enumerate(segs):
            if b(s.at) <= n < b(s.until):
                break
        else:
            raise IndexError(n)
        shots = []
        if i and s.overlap and n < b(s.at + s.overlap):
            shots += self._shots(segs[i - 1], n, parents, n - b(s.at), tail=True)
        return shots + self._shots(s, n, parents, exit)

    def at(self, frame):
        """(segment, frames into it) of the frontmost live leaf segment."""
        shot = self.live(frame)[-1]
        return shot.segment, shot.f

    def label(self, frame):
        """'group / child' of what's live, with 'a > b' through an overlap."""
        return ' > '.join(' / '.join([g.name for g, _ in s.parents] + [s.name]) for s in self.live(frame))

    def cut_frames(self):
        """Frames where the picture cuts: each segment's start, at any level,
        except where it (or a group starting with it) overlaps the one before."""
        b = self.grid.b
        cuts, soft = set(), set()
        for s, _ in self.walk():
            (soft if s.overlap else cuts).add(b(s.at))
        return sorted(cuts - soft)
