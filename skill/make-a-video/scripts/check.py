#!/usr/bin/env python3
"""Review checks for a videobuilder film, and for the MP4s rendered from it.

    python check.py film.py                      # storyboard, read times, marks
    python check.py film.py --video              # ...and the rendered <film>-<format>.mp4s
    python check.py film.py --video out/a.mp4    # ...or the MP4s named

What it checks:
  storyboard  each leaf segment's beats, frames, seconds and copy (from
              `segment.data['copy']`, or with no `copy` key, all of its
              `data` strings), and its read time: a segment must last at
              least `--lead` s plus its words at `--wps` words a second.
  marks       on held frames (the middle and three-quarter frame of each
              segment, plus FILM.keyframes), every `canvas.mark` box lies in
              the format's safe area (`LAYOUTS[fmt]['safe']` if the film has
              one, else the frame), and no two marks overlap, unless the film
              lists the pair in `OVERLAP_OK = {('a', 'b'), ...}`. Frames in an
              overlap transition are skipped. Held frames assume a segment's
              motion has settled by its middle; set FILM.keyframes to the
              settled frames when it hasn't.
  cut frames  each hard cut's first frame shows some marked content: a cut
              onto an empty frame doesn't read as landing on the beat.
  video       ffprobe: H.264, yuv420p, the format's size, the film's fps, exact
              frame count and duration, an AAC stream as long as the picture
              when the film has audio.
  cuts        the picture's hard changes, found by decoding the MP4, against
              `TIMELINE.cut_frames()`: a jump off the grid is a warning.
  beats       when the film has audio: where the music's onsets fall against
              the beat grid, and the head_trim that would line them up.
  loudness    decoded MP4 LUFS, true peak, sub-60 Hz energy and phone-band LUFS.
  flashes     opposing large luminance changes over >=25% of decoded pixels;
              WARN if >3 in any one-second window.
  motion      opt-in --motion: marked-box constant-speed runs and abrupt starts/stops.
  loop seam   with LOOP = True, compare the last-to-first picture change to
              adjacent changes; duplicate terminal frames FAIL.

Exit status 1 if any check FAILs. WARN lines are for a human to judge.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _import_videobuilder(film_path):
    try:
        import videobuilder  # noqa: F401
    except ImportError:
        here = Path(__file__).resolve().parent
        repo = here.parent.parent.parent  # skill/make-a-video/scripts -> repo root
        if (repo / 'videobuilder' / '__init__.py').exists():
            sys.path.insert(0, str(repo))
    import videobuilder
    return videobuilder


class Report:
    def __init__(self):
        self.failed = 0
        self.warned = 0

    def ok(self, msg):
        print(f'  ok    {msg}')

    def warn(self, msg):
        self.warned += 1
        print(f'  WARN  {msg}')

    def fail(self, msg):
        self.failed += 1
        print(f'  FAIL  {msg}')


# ---- storyboard and read times ----
def copy_of(seg):
    """The words a segment shows: `data['copy']`, or all its data strings."""
    data = seg.data or {}
    if 'copy' in data:
        copy = data['copy']
        if isinstance(copy, str):
            return copy
        if isinstance(copy, list) and all(isinstance(v, str) for v in copy):
            return '\n'.join(copy)
        raise ValueError('copy must be a string or a list of strings')
    return '\n'.join(v for v in data.values() if isinstance(v, str))


def storyboard(film, r, wps, lead):
    tl = film.timeline
    if tl is None:
        r.warn('no timeline: nothing to check against')
        return
    g = tl.grid
    print(f'storyboard: {g.bpm:g} bpm at {g.fps} fps, {g.frames_per_beat:g} frames a beat, '
          f'{tl.end:g} beats = {tl.frames} frames = {tl.frames / g.fps:.3f} s, head_trim {g.head_trim}')
    print(f'  {"segment":28} {"beats":>11} {"frames":>11} {"secs":>6}  words  copy')
    for seg, parents in tl.walk():
        a, z = tl.span(seg)
        name = ' / '.join([p.name for p in parents] + [seg.name])
        data = seg.data or {}
        if 'copy' in data:
            keys = [str(k) for k, v in data.items() if k != 'copy' and isinstance(v, str)]
            if keys:
                r.warn(f'{name!r}: uncounted string keys beside copy: {", ".join(keys)}')
        try:
            copy = copy_of(seg)
            offset = data.get('copy_at', 0)
            if isinstance(offset, bool) or not isinstance(offset, (int, float)) or not math.isfinite(offset) or offset < 0:
                raise ValueError('copy_at must be finite, nonnegative beats after segment start')
        except ValueError as e:
            r.fail(f'{name!r}: {e}')
            continue
        words = len(copy.split())
        copy = copy.replace('\n', ' / ')
        flag = f' (overlaps {seg.overlap:g})' if seg.overlap else ''
        print(f'  {name:28} {seg.at:5g}-{seg.until:<5g} {a:5d}-{z:<5d} {(z - a) / g.fps:6.2f}  {words:5d}  '
              f'{copy[:60]}{flag}')
        if seg.children or not copy:
            continue
        secs = max(0, z - g.b(seg.at + offset)) / g.fps
        need = lead + words / wps
        msg = f'read time {seg.name!r}: {words} words in {secs:.2f} s (needs {need:.2f} s at {wps:g} w/s + {lead:g} s)'
        (r.ok if secs + 1e-9 >= need else r.fail)(msg)


# ---- marks: safe area and overlaps ----
def held_frames(film):
    tl = film.timeline
    picks = {}
    if tl is not None:
        for seg in tl.leaves():
            a, z = tl.span(seg)
            for n in ((a + z) // 2, a + 3 * (z - a) // 4):
                picks.setdefault(n, seg.name)
    for n, label in film.keyframes:
        picks[n] = label or picks.get(n, '')
    return sorted(picks.items())


def marks(mod, film, fmts, r, every=None):
    from videobuilder import Box
    tl = film.timeline
    ok_pairs = {frozenset(p) for p in getattr(mod, 'OVERLAP_OK', ())}
    frames = [(n, '') for n in range(0, film.frames, every)] if every else held_frames(film)
    for fmt in fmts:
        layouts = getattr(mod, 'LAYOUTS', {}) or {}
        entry = layouts.get(fmt.name, layouts.get('*')) if isinstance(layouts, dict) else None
        safe = entry.get('safe') if isinstance(entry, dict) else None
        safe = Box(*safe) if safe is not None else Box(0, 0, fmt.width, fmt.height)
        where = 'safe area' if isinstance(entry, dict) and entry.get('safe') is not None else 'frame'
        seen, count, checked = set(), 0, 0
        for n, label in frames:
            if tl is not None and len(tl.live(n)) > 1:
                continue  # mid-transition: two shots on screen by design
            cv = film.frame(n, fmt, scale=0.05)
            checked += 1
            label = label or (tl.label(n) if tl is not None else '')
            for name, box in cv.marks:
                count += 1
                if not safe.contains(box, tolerance=1):
                    key = ('out', name, label)
                    if key not in seen:
                        seen.add(key)
                        r.fail(f'{fmt.name} f{n} ({label}): mark {name!r} {_box(box)} leaves the {where} {_box(safe)}')
            ms = cv.marks
            for i in range(len(ms)):
                for j in range(i + 1, len(ms)):
                    (na, ba), (nb, bb) = ms[i], ms[j]
                    if frozenset((na, nb)) in ok_pairs or not ba.intersects(bb, tolerance=1):
                        continue
                    key = ('overlap', na, nb, label)
                    if key not in seen:
                        seen.add(key)
                        r.fail(f'{fmt.name} f{n} ({label}): marks {na!r} {_box(ba)} and {nb!r} {_box(bb)} overlap')
        empty = []
        for c in (tl.cut_frames() if tl is not None else []):
            if c and not film.frame(c, fmt, scale=0.05).marks:
                empty.append(c)
        for c in empty:
            r.warn(f'{fmt.name} f{c} ({tl.label(c)}): the cut lands on a frame with no visible marked content, so '
                   f'it won\'t read on the beat; have something on screen on the cut frame (start the entrance '
                   f'a few frames early, e.g. a spring at f + 3)')
        if count == 0:
            r.warn(f'{fmt.name}: no marks on {checked} held frames; mark content boxes with canvas.mark(name, *box)')
        elif not any(k[0] in ('out', 'overlap') for k in seen):
            r.ok(f'{fmt.name}: {count} marks on {checked} held frames, all inside the {where}, none overlapping')


def _box(b):
    return f'({b.x:.0f},{b.y:.0f} {b.w:.0f}x{b.h:.0f})'


def motion_events(samples, min_speed=1.0):
    """Conservative mark motion: >=6 steady steps within 5%, or a full-speed one-frame edge."""
    events = []
    for name in {k for frame in samples for k in frame}:
        steps = []
        for prev, cur in zip(samples, samples[1:]):
            if name not in prev or name not in cur:
                steps.append(None)
            else:
                a, b = prev[name], cur[name]
                steps.append(tuple(y - x for x, y in zip(a, b)))
        speeds = [math.hypot(*v[:2]) + math.hypot(*v[2:]) if v is not None else 0 for v in steps]
        start = 0
        while start < len(steps):
            if speeds[start] < min_speed:
                start += 1
                continue
            end = start + 1
            while end < len(steps) and steps[end] is not None and speeds[end] >= min_speed:
                end += 1
            run = speeds[start:end]
            if len(run) >= 6 and max(run) - min(run) <= 0.05 * max(run):
                events.append((name, 'constant rate', start, end))
            peak = max(run)
            if start and speeds[start - 1] <= 0.2 * peak and run[0] >= 0.8 * peak:
                events.append((name, 'full-speed start', start, start + 1))
            if end < len(speeds) and speeds[end] <= 0.2 * peak and run[-1] >= 0.8 * peak:
                events.append((name, 'full-speed stop', end, end + 1))
            start = end
    return events


def check_motion(film, fmts, r):
    for fmt in fmts:
        samples = []
        for n in range(film.frames):
            samples.append({name: (box.x, box.y, box.w, box.h)
                            for name, box in film.frame(n, fmt, scale=0.05).marks})
        for name, kind, a, z in motion_events(samples):
            r.warn(f'{fmt.name}: mark {name!r} {kind} at frames f{a}–f{z}')


# ---- the rendered video ----
def probe(path, film, fmt, r, loop=False):
    out = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json',
                          str(path)], capture_output=True, text=True)
    if out.returncode:
        r.fail(f'{path}: ffprobe failed: {out.stderr.strip()}')
        return
    info = json.loads(out.stdout)
    v = [s for s in info['streams'] if s['codec_type'] == 'video']
    a = [s for s in info['streams'] if s['codec_type'] == 'audio']
    if len(v) != 1:
        r.fail(f'{path}: {len(v)} video streams')
        return
    v = v[0]
    num, den = (int(x) for x in v['r_frame_rate'].split('/'))
    frames = int(v.get('nb_read_frames') or v.get('nb_frames') or 0)
    want = film.frames / film.fps
    vdur = float(v.get('duration', 0))
    problems = []
    if v['codec_name'] != 'h264':
        problems.append(f"codec {v['codec_name']}")
    if v.get('pix_fmt') != 'yuv420p':
        problems.append(f"pix_fmt {v.get('pix_fmt')}")
    if (v['width'], v['height']) != (fmt.width, fmt.height):
        problems.append(f"size {v['width']}x{v['height']}, not {fmt.width}x{fmt.height}")
    if num != film.fps * den:
        problems.append(f"fps {num}/{den}, not {film.fps}")
    if frames != film.frames:
        problems.append(f'{frames} frames, not {film.frames}')
        if loop and frames == film.frames + 1:
            r.fail(f'{path}: loop rendered frame {film.frames} as well as frame 0')
    if abs(vdur - want) > 0.5 / film.fps:
        problems.append(f'video lasts {vdur:.3f} s, not {want:.3f} s')
    if film.audio is not None:
        if len(a) != 1:
            problems.append(f'{len(a)} audio streams, film has audio')
        else:
            adur = float(a[0].get('duration', 0))
            if a[0]['codec_name'] != 'aac':
                problems.append(f"audio codec {a[0]['codec_name']}")
            if abs(adur - want) > 0.05:
                problems.append(f'audio lasts {adur:.3f} s, picture {want:.3f} s')
    elif a:
        problems.append('an audio stream, but the film has no audio')
    desc = (f"{path}: {v['codec_name']} {v.get('pix_fmt')} {v['width']}x{v['height']} {num}/{den} fps, "
            f"{frames} frames, {vdur:.3f} s" + (f", {a[0]['codec_name']} {float(a[0].get('duration', 0)):.3f} s"
                                                  if a else ', no audio'))
    if problems:
        r.fail(desc + ': ' + '; '.join(problems))
    else:
        r.ok(desc)


def picture_diffs(path, width=96, frames=None):
    """Mean absolute change, 0-255, between each frame and the one before it
    (index 0 is 0), from a small grey decode of the video."""
    frames = frames if frames is not None else decoded_gray(path, width)
    size = len(frames[0]) if frames else 1
    diffs = [0.0]
    for prev, cur in zip(frames, frames[1:]):
        diffs.append(sum(abs(x - y) for x, y in zip(prev, cur)) / size)
    return diffs


def decoded_gray(path, width=96):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                          '-of', 'csv=p=0', str(path)], capture_output=True, text=True, check=True)
    w0, h0 = (int(x) for x in out.stdout.strip().split(','))
    h = max(2, round(h0 * width / w0 / 2) * 2)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-vf', f'scale={width}:{h},format=gray',
                          '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
    size = width * h
    return [raw[i:i + size] for i in range(0, len(raw) - size + 1, size)]


def flash_frames(frames, fps, threshold=0.25):
    """A flash is a bright/dark reversal of >=25% pixels with >=32/255 change each way."""
    changes = []
    for a, b in zip(frames, frames[1:]):
        size = len(a)
        changes.append((sum(y - x >= 32 for x, y in zip(a, b)) / size,
                        sum(x - y >= 32 for x, y in zip(a, b)) / size))
    events = [n + 2 for n, (up, down) in enumerate(changes[1:])
              if (up >= threshold and changes[n][1] >= threshold) or
              (down >= threshold and changes[n][0] >= threshold)]
    return [n for n in events if sum(n - fps < k <= n for k in events) > 3]


def seam_ratio(frames):
    if len(frames) < 4:
        return 0.0
    change = lambda a, b: sum(abs(x - y) for x, y in zip(a, b)) / len(a)
    seam = change(frames[-1], frames[0])
    neighbours = [change(frames[i], frames[i + 1]) for i in (0, 1, -3, -2)]
    return seam / max(1, sorted(neighbours)[len(neighbours) // 2])


def picture_safety(path, film, r, loop=False, frames=None):
    frames = frames if frames is not None else decoded_gray(path)
    flashes = flash_frames(frames, film.fps)
    if flashes:
        r.warn(f'{path}: >3 large opposing luminance flashes in one second at frames {flashes}')
    if loop and seam_ratio(frames) > 3:
        r.warn(f'{path}: loop seam f{len(frames)-1}->f0 jumps {seam_ratio(frames):.1f}x neighbouring changes')


def _ebur(path, filters=''):
    af = f'{filters},ebur128=peak=true' if filters else 'ebur128=peak=true'
    result = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-map', '0:a:0', '-af', af,
                             '-f', 'null', '-'], capture_output=True, text=True, check=True)
    summary = result.stderr.rsplit('Summary:', 1)[-1]
    loud = float(re.search(r'Integrated loudness:\s*I:\s*([-\d.]+)', summary).group(1))
    peak = float(re.search(r'True peak:\s*Peak:\s*([-\d.]+)', summary).group(1))
    return loud, peak


def _mean_volume(path, filters=''):
    af = f'{filters},volumedetect' if filters else 'volumedetect'
    result = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-map', '0:a:0', '-af', af,
                             '-f', 'null', '-'], capture_output=True, text=True, check=True)
    return float(re.search(r'mean_volume:\s*([-\d.]+) dB', result.stderr).group(1))


def loudness(path, audio, r):
    full, peak = _ebur(path)
    sub = _mean_volume(path, 'lowpass=f=60')
    overall = _mean_volume(path)
    share = 100 * 10 ** ((sub - overall) / 10)
    band, _ = _ebur(path, 'highpass=f=200,lowpass=f=6000')
    r.ok(f'{path}: decoded audio {full:.1f} LUFS, true peak {peak:.1f} dBTP; '
         f'below 60 Hz {share:.1f}% energy, 200 Hz–6 kHz {band:.1f} LUFS ({band - full:+.1f} LU)')
    if audio.loudness is not None and abs(full - audio.loudness) > 1:
        r.warn(f'{path}: loudness {full:.1f} LUFS is >1 LU from target {audio.loudness:g}')
    if peak > -1:
        r.warn(f'{path}: decoded true peak {peak:.1f} dBTP exceeds -1 dBTP')
    if share > 50:
        r.warn(f'{path}: {share:.1f}% of energy is below 60 Hz; check on phone speakers')
    if band - full < -6:
        r.warn(f'{path}: phone band is {full - band:.1f} LU below full mix')


def cuts(path, film, r, min_jump=6.0, frames=None):
    tl = film.timeline
    if tl is None:
        return
    d = picture_diffs(path, frames=frames)
    grid = set(tl.cut_frames())
    jumps = []
    for n in range(1, len(d)):
        around = [d[k] for k in (n - 2, n - 1, n + 1, n + 2) if 0 < k < len(d)]
        if d[n] >= min_jump and d[n] >= 3 * max(around or [0]):
            jumps.append(n)
    off = [n for n in jumps if n not in grid]
    quiet = sorted(n for n in grid if n and n not in jumps)
    on = len(jumps) - len(off)
    msg = f'{path}: {len(jumps)} hard picture changes, {on} on the {len(grid - {0})} cuts of cut_frames()'
    r.ok(msg)
    for n in off:
        near = min(grid, key=lambda c: abs(c - n)) if grid else None
        r.warn(f'{path}: the picture jumps at f{n} ({tl.label(n)}), off the cut grid'
               + (f' (nearest cut f{near}, {n - near:+d} frames)' if near is not None else ''))
    if quiet:
        print(f'  note  cuts with no hard change in the picture (from or to an empty frame, or a matched cut): '
              + ', '.join(f'f{n}' for n in quiet))


def beats(path, film, r, rate=8000):
    """Where the music's onsets fall against the beat grid, from the MP4's audio."""
    if film.audio is None or film.timeline is None:
        return
    g = film.timeline.grid
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0', '-ac', '1', '-ar', str(rate),
                          '-f', 's16le', '-'], capture_output=True).stdout
    import array
    s = array.array('h')
    s.frombytes(raw[:len(raw) // 2 * 2])
    hop = rate // 200  # 5 ms
    energy = [math.log(1e-3 + sum(x * x for x in s[i:i + hop]) / hop) for i in range(0, len(s) - hop, hop)]
    onset = [0.0] + [max(0.0, b - a) for a, b in zip(energy, energy[1:])]
    if not any(onset):
        r.warn(f'{path}: the audio is silent')
        return
    spb = 60 / g.bpm
    nbeats = int(len(onset) * hop / rate / spb)

    def score(shift):  # mean onset strength within 10 ms of each beat + shift seconds
        tot = 0.0
        for k in range(nbeats):
            i = round((k * spb + shift) * rate / hop)
            tot += max(onset[max(0, i - 2):i + 3] or [0])
        return tot / max(1, nbeats)

    shifts = [ms / 1000 for ms in range(-int(spb * 500), int(spb * 500) + 1, 5)]
    scores = [score(x) for x in shifts]
    best = max(range(len(shifts)), key=scores.__getitem__)
    mean = sum(scores) / len(scores)
    contrast = scores[best] / mean if mean else 0
    off_ms = shifts[best] * 1000
    frame_ms = 1000 / g.fps
    if contrast < 1.5:
        r.warn(f'{path}: no clear beat in the audio (peak/mean onset {contrast:.1f}); check alignment by ear '
               f'with `still --overlay` frames on the cuts')
    elif abs(off_ms) <= frame_ms / 2:
        r.ok(f'{path}: music onsets land {off_ms:+.0f} ms from the grid (within half a frame); peak/mean {contrast:.1f}')
    else:
        trim = g.head_trim + round(off_ms / frame_ms)
        r.warn(f'{path}: music onsets land {off_ms:+.0f} ms from the beat grid; try Grid(head_trim={trim}) '
               f'(now {g.head_trim}), or check the BPM')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('film')
    p.add_argument('--format', default='all', help="a format name, or 'all' (default)")
    p.add_argument('--video', nargs='*', help='check rendered MP4s: the ones named, or <film>-<format>.mp4')
    p.add_argument('--wps', type=float, default=3.0, help='reading speed, words a second (default 3)')
    p.add_argument('--lead', type=float, default=1.0, help='seconds added to every read time (default 1)')
    p.add_argument('--every', type=int, help='check marks on every Nth frame, not just held frames')
    p.add_argument('--motion', action='store_true', help='draw every frame to check marked-box motion')
    a = p.parse_args(argv)

    vb = _import_videobuilder(a.film)
    mod = vb.load_module(a.film)
    film = mod.FILM
    fmts = list(film.formats) if a.format == 'all' else [film.format(a.format)]
    r = Report()
    storyboard(film, r, a.wps, a.lead)
    print('marks:')
    marks(mod, film, fmts, r, a.every)
    if a.motion:
        check_motion(film, fmts, r)
    if a.video is not None:
        if not shutil.which('ffprobe'):
            r.fail('ffprobe not found')
        else:
            stem = Path(a.film).stem
            if a.video:
                pairs = []
                for v in a.video:
                    match = [f for f in film.formats if f'-{f.name}' in Path(v).stem] or [film.formats[0]]
                    pairs.append((Path(v), match[0]))
            else:
                pairs = []
                for f in fmts:
                    for d in (Path.cwd(), Path(a.film).resolve().parent):
                        if (d / f'{stem}-{f.name}.mp4').exists():
                            pairs.append((d / f'{stem}-{f.name}.mp4', f))
                            break
                    else:
                        r.fail(f'no {stem}-{f.name}.mp4 here or beside the film; render it first')
            for path, f in pairs:
                print(f'video {path} ({f.name}):')
                if not path.exists():
                    r.fail(f'{path} does not exist')
                    continue
                probe(path, film, f, r, getattr(mod, 'LOOP', False))
                frames = decoded_gray(path)
                cuts(path, film, r, frames=frames)
                picture_safety(path, film, r, getattr(mod, 'LOOP', False), frames=frames)
                beats(path, film, r)
                if film.audio is not None:
                    loudness(path, film.audio, r)
    print(f'{r.failed} failed, {r.warned} warnings')
    return 1 if r.failed else 0


if __name__ == '__main__':
    sys.exit(main())
