"""Assemble a film made of clips (see `timeline_file`) into one MP4.

1. Each clip directory is rendered on its own, or fetched from the
   `clip_cache.ClipCache` when its render key (its inputs, not the commit) has
   been rendered before. Footage clips are never rendered.
2. The picture is joined. When every cut is a hard cut, no clip is trimmed,
   none is footage and every clip is a whole number of microseconds long (the
   concat demuxer keeps time in them; see `render.check_chunk`), the clip
   renders are joined with the concat demuxer, no re-encode. Otherwise the
   picture is encoded once through one filter graph: each clip trimmed (and
   footage scaled to cover and centre-cropped), hard cuts `concat`ed and
   dissolves and wipes `xfade`d over their overlap.
3. The sound is mixed with the same code as one film's (`render.sound_chain`,
   `render.duck_filter`, `render.join_mix`, the loudness gain and limiter):
   each clip's own sound under its picture, extended by its J/L overlap, plus
   every Audio lane item, ducked lanes dipping under clip sound that is speech
   (see `speech_spans`).

So a change to a transition, a trim, a J/L cut, clip order or a lane only
re-assembles: no clip renders again. A change inside one clip's directory
re-renders that clip alone.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from . import captions
from . import render as _render
from .clip_cache import ClipCache, FileTree, clip_key, spans_path
from .film import DEFAULT_LOUDNESS, Sound, as_format
from .timeline_file import DEFAULT_FADE, load as load_timeline, place

XFADE = {'dissolve': 'fade', 'wipe': 'wipe{direction}'}
SEEK_MARGIN = 1   # seconds a footage input is seeked short of its first frame
CAPTION_EXTS = ('vtt', 'srt')
CAPTION_GAP = 1.0   # seconds of silence between caption words that lets a ducked lane back up
# `videobuilder render` writes the film's Sound spans to the file this names
# (`write_spans`). An environment variable, not a flag, so a clip pinned to a
# videobuilder from before it renders all the same, only without spans.
SPANS_ENV = 'VIDEOBUILDER_SOUND_SPANS'


@dataclass
class Result:
    out: str
    frames: int
    rendered: list = field(default_factory=list)   # clip ids rendered this time
    reused: list = field(default_factory=list)     # clip ids whose cached render was used
    copied: bool = False                           # picture joined with no re-encode


def resolve(root, rel):
    """`rel` (a timeline path) under the checkout `root`, refusing anything that
    resolves outside it (a committed symlink, say)."""
    root = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root, rel))
    if os.path.commonpath([root, path]) != root:
        raise ValueError(f'{rel} resolves outside the video')
    if not os.path.isfile(path):
        raise ValueError(f'{rel}: no such file (footage and lane sounds go in the video\'s sources/)')
    return path


def probe(path):
    """(frame rate or None, duration in seconds, has_audio) of a media file."""
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
                            capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f'{path}: not a media file ffmpeg can read')
    data = json.loads(result.stdout)
    streams = data.get('streams') or []
    video = next((s for s in streams if s.get('codec_type') == 'video'), None)
    rate = Fraction(video['r_frame_rate']) if video and video.get('r_frame_rate', '0/0') != '0/0' else None
    duration = float((video or {}).get('duration') or (data.get('format') or {}).get('duration') or 0)
    return rate, duration, any(s.get('codec_type') == 'audio' for s in streams)


def write_spans(film, path, frames=None):
    """Write the spans of `film`'s Sounds over frames a..z (default the whole
    film), in frames from `a`, to the JSON file `path`: what a clip's render
    leaves for the assembly to duck its lanes under."""
    a, z = frames or (0, film.frames)
    spans = []
    for s in film.sounds:
        lo, hi = max(s.at, a), min(s.at + s.frames, z)
        if hi > lo:
            spans.append({'at': lo - a, 'frames': hi - lo, 'fade_in': s.fade_in_frames,
                          'fade_out': s.fade_out_frames})
    Path(path).write_text(json.dumps(spans))


def read_spans(path):
    """[(at, frames, fade_in, fade_out)] from a spans sidecar; None when there
    is none (a clip rendered by a videobuilder that doesn't write them)."""
    try:
        data = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return None
    return [(int(d['at']), int(d['frames']), int(d['fade_in']), int(d['fade_out'])) for d in data]


def caption_spans(path, fps):
    """[(at, frames, fade_in, fade_out)] in frames of the caption file `path`'s
    speech: its words, joined where less than `CAPTION_GAP` apart."""
    runs = []
    for w in captions.load(path).words:
        if runs and w.start - runs[-1][1] < CAPTION_GAP:
            runs[-1][1] = max(runs[-1][1], w.end)
        else:
            runs.append([w.start, w.end])
    spans = []
    for t0, t1 in runs:
        at = int(t0 * fps)
        spans.append((at, max(1, -int(-t1 * fps) - at), DEFAULT_FADE, DEFAULT_FADE))
    return spans


def render_clip_local(root, clip, fmt, out, jobs=None, log=sys.stderr):
    """Render clip directory `clip` of the video at `root` to `out`, and its
    Sound spans to `spans_path(out)`, in a child Python running this
    videobuilder with the video's root on the import path (so the clip can
    import `shared`). Not sandboxed: for local use."""
    env = dict(os.environ)
    env[SPANS_ENV] = str(spans_path(out))
    here = str(Path(__file__).resolve().parent.parent)  # this videobuilder, installed or not
    env['PYTHONPATH'] = os.pathsep.join(p for p in (str(root), here, env.get('PYTHONPATH')) if p)
    cmd = [sys.executable, '-m', 'videobuilder', 'render', str(Path(root) / clip.film_path),
           '--format', fmt, '--out', str(out)]
    if jobs:
        cmd += ['--jobs', str(jobs)]
    result = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f'clip "{clip.id}" failed to render:\n{result.stderr[-3000:]}')
    print(f'clip "{clip.id}": rendered', file=log)


def clip_renders(timeline, fmt, tree, cache, render_clip):
    """{clip id: MP4 path} for every clip directory, rendering only the ones
    whose key isn't in `cache`, with `render_clip(clip, fmt, out)`; plus the ids
    rendered and reused."""
    paths, rendered, reused = {}, [], []
    for c in timeline.clips:
        if c.is_footage:
            continue
        key = clip_key(tree, c, fmt)
        path, fresh = cache.get(key, fmt, lambda out, c=c: render_clip(c, fmt, out))
        paths[c.id] = str(path)
        (rendered if fresh else reused).append(c.id)
    return paths, rendered, reused


def speech_spans(clip, path, frames, fps):
    """[(at, frames, fade_in, fade_out)]: where in its media (`path`, `frames`
    long) a clip's sound is speech, in its media's frames, for ducked lanes to
    dip under. All of it when marked `dialogue`; for footage, its caption
    file's cue times (`sources/boat.vtt` beside `sources/boat.mp4`); for a
    clip directory, the spans of its film's Sounds, as one film's music ducks
    under them (the sidecar its render wrote; none from a videobuilder too old
    to write one)."""
    if clip.sound.dialogue:
        return [(0, frames, DEFAULT_FADE, DEFAULT_FADE)]
    if clip.is_footage:
        stem = os.path.splitext(path)[0]
        found = next((f'{stem}.{e}' for e in CAPTION_EXTS if os.path.isfile(f'{stem}.{e}')), None)
        return caption_spans(found, fps) if found else []
    return read_spans(spans_path(path)) or []


def _placed_speech(spans, p, sound, early, late):
    """`spans` (in clip media frames) as Sounds on the timeline, cut to the
    part of the media placement `p` plays: its picture, `early`/`late` wider."""
    lo, hi = p.source - early, p.source + p.frames + late
    out = []
    for at, frames, fade_in, fade_out in spans:
        a, z = max(at, lo), min(at + frames, hi)
        if z <= a:
            continue
        out.append(Sound('', at=p.start + a - p.source, start=0.0, frames=z - a,
                         fade_in_frames=fade_in if a == at else sound.fade_in_frames,
                         fade_out_frames=fade_out if z == at + frames else sound.fade_out_frames))
    return out


def clip_sounds(timeline, placements, media):
    """[(Sound, [speech Sound])]: each clip's own sound placed under its
    picture, `early`/`late` frames wider for a J/L cut where the clip's media
    has sound there, with the spans of it that are speech placed with it.
    `media` is {clip id: (path, has_audio, speech spans)}, the spans in the
    clip media's frames (`speech_spans`)."""
    out = []
    for i, p in enumerate(placements):
        c = p.clip
        path, has_audio, spans = media[c.id]
        if not has_audio:
            continue
        early = min(c.sound.early, p.source)
        late = min(c.sound.late, max(0, p.media_frames - p.source - p.frames))
        d_in = c.cut.frames if i else 0
        d_out = placements[i + 1].clip.cut.frames if i + 1 < len(placements) else 0
        sound = Sound(path, at=p.start - early, start=(p.source - early) / timeline.fps,
                      frames=p.frames + early + late, gain_db=c.sound.gain_db,
                      fade_in_frames=d_in if d_in and not early else DEFAULT_FADE,
                      fade_out_frames=d_out if d_out and not late else DEFAULT_FADE)
        out.append((sound, _placed_speech(spans, p, sound, early, late)))
    return out


def lane_sounds(timeline, root):
    """[(lane, [Sound])] for every Audio lane, its items as Sounds."""
    out = []
    for lane in timeline.lanes:
        out.append((lane, [Sound(resolve(root, it.sound), at=it.at, start=it.offset / timeline.fps,
                                 frames=it.frames, gain_db=it.gain_db, fade_in_frames=it.fade_in,
                                 fade_out_frames=it.fade_out) for it in lane.items]))
    return out


def mix_graph(clips, lanes, frames, fps, start_idx=0):
    """(inputs, filter_complex graph, output label) mixing `clips`
    [(Sound, [speech Sound])] and `lanes` [(Lane, [Sound])] over `frames`,
    before the final gain and limiter. A ducked lane dips by its `duck_db`
    under the clips' speech (the `duck_envelope_expr` of its spans)."""
    speech = [x for _, spans in clips for x in spans]
    branches = [(s, '') for s, _ in clips]
    for lane, sounds in lanes:
        after = _render.duck_filter(lane.duck_db, speech, fps, 0) if lane.duck and speech else ''
        branches += [(s, after) for s in sounds]
    inputs, chains, labels = [], [], []
    idx = start_idx
    for s, after in branches:
        branch = _render.sound_chain(s, 0, frames, fps, idx, after)
        if branch is None:
            continue
        chains.append(branch[0]), labels.append(branch[1]), inputs.append(s.path)
        idx += 1
    graph, label = _render.join_mix(chains, labels, frames / fps)
    return inputs, graph, label


def picture_graph(timeline, placements, fmt, inputs, seeks=None):
    """(filter_complex graph, output label) cutting the clips together: each
    input trimmed to what it shows, footage scaled to cover the frame, then
    hard cuts concatenated and transitions crossed with `xfade`. `seeks[k]` is
    how many frames placement k's input was seeked past (`footage_seek`)."""
    fps, w, h = timeline.fps, fmt.width, fmt.height
    chains = []
    for k, p in enumerate(placements):
        start = p.source - (seeks[k] if seeks else 0)
        trim = f'trim=start_frame={start}:end_frame={start + p.frames},setpts=PTS-STARTPTS'
        if p.clip.is_footage:
            f = (f'fps={fps},{trim},scale={w}:{h}:force_original_aspect_ratio=increase,'
                 f'crop={w}:{h}')
        else:
            f = trim
        chains.append(f'[{inputs[k]}:v]{f},fps={fps},setsar=1,format=yuv420p,settb=AVTB[c{k}]')
    acc = 'c0'
    for k, p in enumerate(placements[1:], start=1):
        cut, nxt = p.clip.cut, f'j{k}'
        if cut.transition == 'cut':
            # ffmpeg 7's concat leaves the frame rate unset (1/0), which a later xfade refuses.
            chains.append(f'[{acc}][c{k}]concat=n=2:v=1:a=0,fps={fps},settb=AVTB[{nxt}]')
        else:
            kind = XFADE[cut.transition].format(direction=cut.direction)
            chains.append(f'[{acc}][c{k}]xfade=transition={kind}:duration={cut.frames / fps:.6f}:'
                          f'offset={p.start / fps:.6f}[{nxt}]')
        acc = nxt
    return ';'.join(chains), acc


def footage_seek(source, fps):
    """Frames to seek a footage input past before decoding (`-ss`), so a cut
    from late in a long file isn't decoded from its start: a margin short of
    `source`, so the accurate seek's rounding never loses the first frame."""
    return max(0, source - SEEK_MARGIN * fps)


def _run(cmd, what):
    """Run ffmpeg `cmd`, raising ValueError with the tail of its errors."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f'{what} failed:\n{result.stderr[-3000:]}')


def _concat_line(path):
    """One concat demuxer list line naming `path`, quotes escaped."""
    return "file '" + str(path).replace("'", "'\\''") + "'\n"


def copyable(timeline, placements):
    """Whether the clip renders can be joined as they are (see the module doc)."""
    return all(not p.clip.is_footage and p.clip.cut.transition == 'cut' and p.source == 0
               and p.frames == p.media_frames and p.frames * 1_000_000 % timeline.fps == 0
               for p in placements)


def assemble(timeline, fmt, out, root, renders, crf=18, log=sys.stderr):
    """Join `timeline`'s clips into the MP4 `out` in format `fmt`. `root` is the
    checkout timeline paths resolve in; `renders` is {clip id: MP4} for every
    clip directory (`clip_renders`). Returns (frames, copied)."""
    fmt = as_format(fmt)
    fps = timeline.fps
    lengths, media = {}, {}
    for c in timeline.clips:
        path = renders[c.id] if not c.is_footage else resolve(root, c.footage)
        rate, duration, has_audio = probe(path)
        if rate is None:
            raise ValueError(f'clip "{c.id}": {path} has no picture')
        if not c.is_footage and rate != fps:
            raise ValueError(f'clip "{c.id}" renders at {rate} fps; the timeline is {fps} fps')
        lengths[c.id] = round(duration * fps)
        media[c.id] = (path, has_audio, speech_spans(c, path, lengths[c.id], fps))
    placements, total = place(timeline, lengths)
    clips = clip_sounds(timeline, placements, media)
    lanes = lane_sounds(timeline, root)
    _render.ensure_has_audio(s.path for _, sounds in lanes for s in sounds)
    copied = copyable(timeline, placements)
    with tempfile.TemporaryDirectory() as tmp:
        picture = os.path.join(tmp, 'picture.mp4')
        if copied:
            listing = os.path.join(tmp, 'list.txt')
            with open(listing, 'w') as fh:
                fh.writelines(_concat_line(media[p.clip.id][0]) for p in placements)
            _run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', listing,
                  '-map', '0:v', '-c:v', 'copy', picture], 'joining the clips')
        else:
            # One input per clip render file; one per footage placement, seeked near its cut.
            seeks = [footage_seek(p.source, fps) if p.clip.is_footage else 0 for p in placements]
            files = list(dict.fromkeys((media[p.clip.id][0], seek) for p, seek in zip(placements, seeks)))
            graph, label = picture_graph(timeline, placements, fmt,
                                         [files.index((media[p.clip.id][0], seek))
                                          for p, seek in zip(placements, seeks)], seeks)
            cmd = ['ffmpeg', '-v', 'error', '-y']
            for f, seek in files:
                cmd += (['-ss', f'{seek / fps:.6f}'] if seek else []) + ['-i', f]
            cmd += ['-filter_complex', graph, '-map', f'[{label}]', '-frames:v', str(total), '-r', str(fps),
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-pix_fmt', 'yuv420p',
                    '-video_track_timescale', str(fps * 512), picture]
            _run(cmd, 'encoding the picture')
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', picture]
        if clips or any(sounds for _, sounds in lanes):
            whole = mix_graph(clips, lanes, total, fps)
            gain = _render.loudness_gain_graph(*whole, DEFAULT_LOUDNESS)
            inputs, graph, label = mix_graph(clips, lanes, total, fps, start_idx=1)
            cmd += [f for p in inputs for f in ('-i', p)]
            cmd += ['-filter_complex', f'{graph};[{label}]{_render.limiter_suffix(gain)}[a]',
                    '-map', '0:v', '-map', '[a]', '-c:a', 'aac', '-b:a', '320k', '-ar', '48000']
        cmd += ['-c:v', 'copy', '-movflags', '+faststart', str(out)]
        _run(cmd, 'mixing the sound')
    return total, copied


def build(timeline, fmt, out, root, tree, cache, render_clip, log=sys.stderr):
    """Render what's missing, then assemble: the whole of an assembly render.
    Returns a `Result` naming the clips rendered and reused."""
    t0 = time.time()
    renders, rendered, reused = clip_renders(timeline, fmt, tree, cache, render_clip)
    t1 = time.time()
    frames, copied = assemble(timeline, fmt, out, root, renders, log=log)
    print(f'{out}: {len(timeline.clips)} clips, {frames} frames; rendered {len(rendered)}, '
          f'reused {len(reused)}; clips {t1 - t0:.1f}s, assembly {time.time() - t1:.1f}s'
          f'{" (no re-encode)" if copied else ""}', file=log)
    return Result(str(out), frames, rendered, reused, copied)


def assemble_dir(root, fmt=None, out=None, cache_dir=None, render_clip=None, jobs=None, log=sys.stderr):
    """`python -m videobuilder assemble`: the timeline at `root`, as the files
    are on disk, to `out` (default `<root>/<root name>-<fmt>.mp4`), keeping
    clip renders in `cache_dir` (default `<root>/.vb-cache/clips`)."""
    root = Path(root).resolve()
    timeline = load_timeline(root / 'timeline.json')
    fmt = fmt or timeline.formats[0]
    if fmt not in timeline.formats:
        raise ValueError(f'the timeline has no {fmt} format; it has {", ".join(timeline.formats)}')
    out = Path(out) if out else root / f'{root.name}-{fmt}.mp4'
    cache = ClipCache(cache_dir or root / '.vb-cache' / 'clips')
    if render_clip is None:
        def render_clip(clip, f, dest):
            render_clip_local(root, clip, f, dest, jobs=jobs, log=log)
    return build(timeline, fmt, out, root, FileTree(root), cache, render_clip, log=log)
