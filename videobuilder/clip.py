"""Frame-accurate, bounded-memory video asset reader using system ffmpeg."""
from dataclasses import dataclass
from fractions import Fraction
import json
import math
import os
import queue
import re
import subprocess
import threading

from PIL import Image as PILImage

from .canvas import Image
from .film import Sound


def _rotation_degrees(stream):
    """The rotation (0/90/180/270) ffmpeg will auto-rotate this stream's decoded
    frames by: the display-matrix side data a phone writes (mov/mp4's tkhd
    matrix, surfaced by ffprobe as `side_data_list[].rotation`), falling back
    to the older plain `rotate` tag some files still carry instead."""
    for side_data in stream.get('side_data_list') or ():
        if 'rotation' in side_data:
            return int(side_data['rotation']) % 360
    tag = (stream.get('tags') or {}).get('rotate')
    if tag is not None:
        return int(tag) % 360
    return 0


def _displayed_size(stream):
    """(width, height) of this stream's frames as displayed -- after the
    rotation ffmpeg applies on decode -- swapping the coded dimensions at
    +-90/270."""
    width, height = stream['width'], stream['height']
    if _rotation_degrees(stream) in (90, 270):
        return height, width
    return width, height


_STANDARD_FPS = tuple(Fraction(n) for n in range(1, 121)) + tuple(
    Fraction(n * 1000, 1001) for n in (24, 30, 60, 120))


def round_fps(fps):
    """Snap `fps` to the nearest standard frame rate when it's suspiciously
    close to one -- within 0.05%, tighter than the ~0.1% gap between a whole
    rate and its own NTSC-ish sibling (e.g. 30 and 30000/1001), so a genuinely
    29.97 source stays 29.97 rather than rounding up to 30. `ffprobe`'s
    avg_frame_rate is computed from a stream's own (often coarse, e.g. an
    iPhone's 600) timestamp timescale, so a truly constant-rate source can
    report a rate like 27000/901 instead of the 30000/1001 it was recorded
    at; left unrounded, that odd rate becomes the grid `Clip`'s `fps` filter
    resamples onto, dropping and duplicating frames a CFR source shouldn't
    lose."""
    for candidate in _STANDARD_FPS:
        if abs(fps - candidate) <= candidate / 2000:
            return candidate
    return fps


def _fps_and_cfr(stream):
    """(fps, is_cfr): the rate `Clip` reports (see `round_fps`), and whether
    the stream already sits on that rate's own grid closely enough that
    resampling it through ffmpeg's `fps` filter would be a true no-op.

    `avg_frame_rate` (duration / frame count) is corrupted by a coarse
    container timescale -- an iPhone's mov typically uses 600 ticks/second,
    which can't exactly represent a 30000/1001 frame interval, so a
    genuinely constant-rate stream's own `avg_frame_rate` comes out as some
    nearby-but-wrong ratio (e.g. 27000/901). `r_frame_rate` is derived from
    codec-level frame timing instead and survives that rounding, so when the
    two agree (after both are snapped the same way) the source really is
    constant-rate and the `fps` filter can be skipped outright -- which
    matters, because *applying* the filter to a stream whose own timestamps
    are already coarsely quantized reintroduces exactly the drop/duplicate
    drift it exists to prevent, even when its target rate matches. A
    genuinely variable-rate source has no such agreement: its `r_frame_rate`
    reflects the shortest frame interval or similar, not the average."""
    fps = round_fps(Fraction(stream['avg_frame_rate']))
    return fps, round_fps(Fraction(stream['r_frame_rate'])) == fps


_SHOWINFO_PTS_TIME = re.compile(rb'pts_time:(\S+)')


def _drain_slots(stderr, slots, synced):
    """Feed `slots` the `pts_time` of each frame `showinfo` logs to `stderr`,
    in order, ending with a `None` sentinel at EOF. Runs for the life of a VFR
    decoder, so ffmpeg's write to that pipe never backs up; once the caller
    sets `synced` (past the seek-sync it needs this for) it stops queueing.
    `slots` is unbounded until then: showinfo can run several frames ahead
    of stdout, and a dropped pts would misnumber every later frame."""
    for line in stderr:
        match = _SHOWINFO_PTS_TIME.search(line)
        if match is not None and not synced.is_set():
            slots.put(float(match.group(1)))
    slots.put(None)


class Clip:
    """A video file with random frame access. Keep one decoder open per process."""

    def __init__(self, path):
        self.path = os.fspath(path)
        result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                 '-show_streams', '-of', 'json', self.path],
                                capture_output=True, text=True, check=True)
        streams = json.loads(result.stdout)['streams']
        if not streams:
            raise ValueError(f'no video stream: {self.path}')
        stream = streams[0]
        self.size = _displayed_size(stream)
        self.fps, self._cfr = _fps_and_cfr(stream)
        if self.fps <= 0:
            raise ValueError(f'unknown frame rate: {self.path}')
        if stream.get('nb_frames') not in (None, 'N/A'):
            self.frames = int(stream['nb_frames'])
        else:
            result = subprocess.run(['ffprobe', '-v', 'error', '-count_frames',
                                     '-select_streams', 'v:0', '-show_entries',
                                     'stream=nb_read_frames', '-of', 'default=nw=1:nk=1',
                                     self.path], capture_output=True, text=True, check=True)
            self.frames = int(result.stdout.strip())
        self._decoder = None
        self._next = None
        self._pid = None
        self._pending = None
        self._drain_thread = None

    def close(self):
        process = self._decoder
        self._decoder = None
        self._next = None
        self._pending = None
        thread = self._drain_thread
        self._drain_thread = None
        if process is not None:
            process.stdout.close()
            process.kill()
            process.wait()
            # The decoder's own exit closes its write end of stderr, so this
            # thread (if any -- VFR decoders have one, CFR ones don't) sees EOF
            # and returns right away; joining before closing stderr on our end
            # avoids racing its read against our close of the same file object.
            if thread is not None:
                thread.join()
                process.stderr.close()

    def _start(self, index):
        self.close()
        count = self.size[0] * self.size[1] * 3
        if self._cfr:
            # A genuinely constant-rate source (see _fps_and_cfr) skips the `fps`
            # filter rather than running through it as a "no-op": even a CFR
            # source's own timestamps can be coarsely quantized (an iPhone's mov
            # typically uses a 600-tick/second timescale), and resampling those
            # onto a grid -- even one at the matching rate -- can still drop and
            # duplicate frames the unfiltered decode wouldn't. An input seek's
            # timestamps need no anchoring here either: a CFR source's own frame
            # at i/fps is just the i'th frame, seek or no seek.
            timestamp = f'{float(index / self.fps):.9f}'
            self._decoder = subprocess.Popen(
                ['ffmpeg', '-v', 'error', '-ss', timestamp, '-i', self.path,
                 '-map', '0:v:0', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                 '-fps_mode', 'passthrough', 'pipe:1'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self._next = index
            self._pid = os.getpid()
            return
        # The `fps` filter resamples a variable-rate source onto this clip's own
        # constant grid (frame i at i/self.fps), the same way ffmpeg would if asked
        # to render the source at a fixed rate: it holds the last decoded frame
        # until the next output slot, rather than assuming evenly-spaced input.
        # round=up (not the filter's own default, round=near, nor round=down):
        # frame i must be the source frame already on screen at i/fps, i.e. the
        # last one whose own pts is <= i/fps -- round=up maps an input frame to
        # the *next* output slot at or after its pts, which is exactly that frame
        # held from its pts through the following output slot. round=down maps
        # it one slot earlier instead, showing frame i one source frame ahead of
        # schedule throughout a variable-rate source.
        # Rotation needs no filter of its own either way: ffmpeg auto-rotates on
        # decode from the stream's own display-matrix side data (ahead of any
        # -vf), which is also how `self.size` already accounts for it.
        #
        # A seek complicates this: ffmpeg's default input-seek ("accurate seek")
        # decodes from the keyframe at or before the target but only hands the
        # filter graph frames from the target onward, and (without -copyts)
        # rebases their timestamps near zero. The `fps` filter then grids those
        # against a clock that starts at the seek point, not the source's own
        # clock, so frame i after a seek can land on the wrong source frame --
        # off by whatever the source's own frame interval was right there. This
        # also means the filter has no frame before the seek point to hold from,
        # so the first slot or two after a seek can go missing entirely, which
        # is why a plain "-ss index/fps" can undercount all the way to a missing
        # final frame. `-noaccurate_seek` hands the filter every frame from the
        # keyframe forward and `-copyts` keeps their timestamps absolute, so the
        # grid stays anchored to the source's own clock across the seek, exactly
        # as it would be from a sequential decode; we then discard (via `showinfo`,
        # parsed from stderr) whatever leading output slots land before `index`,
        # retrying with an earlier seek if the keyframe we landed on turns out to
        # already be past it.
        vf = f'fps=fps={self.fps.numerator}/{self.fps.denominator}:round=up,showinfo'
        backoff = 0
        tries = 0
        while True:
            tries += 1
            seek_index = max(0, index - backoff)
            timestamp = f'{float(seek_index / self.fps):.9f}'
            process = subprocess.Popen(
                ['ffmpeg', '-v', 'info', '-noaccurate_seek', '-copyts', '-ss', timestamp,
                 '-i', self.path, '-map', '0:v:0', '-vf', vf, '-f', 'rawvideo',
                 '-pix_fmt', 'rgb24', '-fps_mode', 'passthrough', 'pipe:1'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            slots, synced = queue.Queue(), threading.Event()
            thread = threading.Thread(target=_drain_slots, args=(process.stderr, slots, synced), daemon=True)
            thread.start()
            pending = None
            while True:
                pts_time = slots.get()
                if pts_time is None:
                    break
                data = process.stdout.read(count)
                if len(data) < count:
                    break
                slot = round(pts_time * float(self.fps))
                if slot >= index:
                    if slot == index:
                        pending = data
                    break
            synced.set()
            if pending is not None:
                self._decoder = process
                self._pending = pending
                self._drain_thread = thread
                self._next = index + 1
                self._pid = os.getpid()
                return
            process.stdout.close()
            process.kill()
            process.wait()
            thread.join()
            process.stderr.close()
            if seek_index == 0 and tries > 1:
                raise RuntimeError(f'could not seek to frame {index} of {self.path}')
            backoff = backoff * 2 if backoff else 5

    def frame(self, index):
        if not isinstance(index, int) or not 0 <= index < self.frames:
            raise IndexError(index)
        if self._pid != os.getpid():
            self._decoder = None
            self._next = None
        if self._decoder is None or index != self._next:
            self._start(index)
        if self._pending is not None:
            # `_start` already set `self._next` to `index + 1` for this buffered
            # frame; don't double-advance it here.
            data = self._pending
            self._pending = None
            return Image.from_pil(PILImage.frombytes('RGB', self.size, data))
        count = self.size[0] * self.size[1] * 3
        chunks = []
        remaining = count
        while remaining:
            chunk = self._decoder.stdout.read(remaining)
            if not chunk:
                self.close()
                raise RuntimeError(f'could not decode frame {index} from {self.path}')
            chunks.append(chunk)
            remaining -= len(chunk)
        self._next += 1
        return Image.from_pil(PILImage.frombytes('RGB', self.size, b''.join(chunks)))

    def frame_at(self, seconds):
        """The source frame shown at `seconds` into this clip."""
        # `seconds` is normally the result of float arithmetic meant to land exactly
        # on a frame boundary (e.g. Footage.seconds_at); nudge past the rounding
        # error that would otherwise floor it one frame early.
        return math.floor(seconds * self.fps + 1e-9)

    def __del__(self):
        if getattr(self, '_decoder', None) is not None:
            self.close()


@dataclass
class Footage:
    """Ties a timeline segment to a point `start` into a source clip, so the
    picture and its `Sound` stay in sync without working out the arithmetic
    twice. Build one with `footage`.

    `seconds_at(f)`: the source second to show at film frame `f` (feed it to
    `Clip.frame_at`). `sound(path, **kw)`: the matching `Sound`, starting at
    the same source second this segment does.
    """
    at: int
    frames: int
    start: float
    fps: int

    def seconds_at(self, f):
        return self.start + (f - self.at) / self.fps

    def sound(self, path, **kw):
        return Sound(path, at=self.at, start=self.start, frames=self.frames, **kw)


def footage(timeline, segment, start):
    """`Footage` for `segment` of `timeline` (a Segment or its name), starting
    `start` seconds into a source clip."""
    a, z = timeline.span(segment)
    return Footage(at=a, frames=z - a, start=start, fps=timeline.grid.fps)
