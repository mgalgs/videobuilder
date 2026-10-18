"""The editor's timeline of a film made of clips (see `timeline_file`).

    GET  /api/timeline?video=V[&format=F]   the timeline file at main, parsed,
         and each clip's render key, state, length and speech, for the strip
    POST /api/timeline {video, timeline, base[, summary]}
         validate with the loader and commit only the timeline file to main,
         as a `Version-kind: edit`; 409 when main's timeline file changed
         since `base`, the commit the edit was made against
    GET  /api/timeline/thumb?video=V&clip=C[&commit=S&format=F]
         a small JPEG of the clip: from its render (once there is one) or its
         footage; 404 until then
    GET  /api/timeline/footage?video=V&clip=C
         a footage clip's file, uploaded or committed, for "This clip" to play

An edit commits only the timeline file, so it re-renders no clip: a clip's
render is keyed by its directory's content (`clip_cache`), and the assembly
at the new commit, queued like any commit's, reuses them.
"""
import hashlib
import json
import os
import subprocess
import threading
from pathlib import Path

from . import assembly, timeline_file as tf
from .clip_cache import GitTree, clip_key
from .editor import HTTPError, _need
from .gitutil import git
from .project import commit_path

# A render's length and sound, by (path, mtime): probed once, not on every poll.
_PROBED = {}
_PROBED_LOCK = threading.Lock()
THUMB_HEIGHT = 180
THUMBS_KEPT = 400
SUMMARY_MAX = 72


def _probe(path):
    """(seconds, has_audio) of a media file, or (None, False) if unreadable."""
    try:
        stamp = os.stat(path).st_mtime_ns
    except OSError:
        return None, False
    with _PROBED_LOCK:
        hit = _PROBED.get(path)
    if hit and hit[0] == stamp:
        return hit[1]
    try:
        _, seconds, audio = assembly.probe(path)
    except ValueError:
        seconds, audio = None, False
    with _PROBED_LOCK:
        if len(_PROBED) > 2000:
            _PROBED.clear()
        _PROBED[path] = (stamp, (seconds, audio))
    return seconds, audio


def _main(editor):
    return git(editor.root, 'rev-parse', 'main')


def _directory(editor, video):
    return editor.drafts.context(video)['directory']


def _relpath(editor, video):
    directory = _directory(editor, video)
    return tf.NAME if directory in ('', '.') else f'{directory}/{tf.NAME}'


def _footage_path(editor, video, clip):
    """The footage file in the main checkout (sources linked in), or None."""
    editor.sources.sync(video)
    try:
        return assembly.resolve(Path(editor.root) / _directory(editor, video), clip.footage)
    except ValueError:
        return None


def _assembly_busy(editor, video, sha, fmt):
    with editor.renders.lock:
        return editor.renders.status.get((video, sha, fmt), {}).get('state') in ('queued', 'rendering')


def _clip_state(editor, video, sha, fmt, timeline, tree, clip, busy):
    """What the strip shows of one clip: its render key and state, the length
    of its media in frames (None until it is known), whether it has sound,
    and where that sound is speech ([at, frames] in its media's frames)."""
    fps = timeline.fps
    out = {'id': clip.id, 'kind': 'footage' if clip.is_footage else 'clip', 'key': None,
           'state': 'ready', 'frames': None, 'audio': False, 'speech': []}
    if clip.is_footage:
        path = _footage_path(editor, video, clip)
        if path is None:
            return {**out, 'state': 'missing', 'error': f'{clip.footage}: no such file in the video\'s sources'}
    else:
        try:
            out['key'] = clip_key(tree, clip, fmt)
        except ValueError as exc:
            return {**out, 'state': 'missing', 'error': str(exc)}
        path = editor.renders.clip_cache(video).path(out['key'], fmt)
        if not path.is_file():
            with editor.renders.lock:
                state = editor.renders.status.get((video, sha, fmt, clip.id), {'state': 'none'})
            out['state'] = 'building' if busy or state['state'] in ('queued', 'rendering') else state['state']
            if state['state'] == 'failed':
                out['error'] = state.get('error')
            return out
    seconds, audio = _probe(str(path))
    if seconds is None:
        return {**out, 'state': 'missing', 'error': 'not a media file ffmpeg can read'}
    frames = round(seconds * fps)
    spans = assembly.speech_spans(clip, str(path), frames, fps) if audio else []
    return {**out, 'frames': frames, 'audio': audio, 'speech': [[at, n] for at, n, _, _ in spans]}


def read(editor, video, fmt=None):
    """The GET body: `commit` (main), `timeline` (the file as written, or None
    when the video has none), `error` (the loader's message when it doesn't
    load), `format`, `fps` and `clips` (see `_clip_state`)."""
    sha = _main(editor)
    raw = GitTree(editor.root, sha, _directory(editor, video)).read(tf.NAME)
    if raw is None:
        return {'commit': sha, 'timeline': None}
    try:
        data = json.loads(raw)
        timeline = tf.parse(data)
    except ValueError as exc:
        return {'commit': sha, 'timeline': None, 'error': str(exc)}
    fmt = fmt if fmt in timeline.formats else timeline.formats[0]
    tree = GitTree(editor.root, sha, _directory(editor, video))
    busy = _assembly_busy(editor, video, sha, fmt)
    clips = [_clip_state(editor, video, sha, fmt, timeline, tree, c, busy) for c in timeline.clips]
    return {'commit': sha, 'timeline': data, 'format': fmt, 'fps': timeline.fps,
            'formats': list(timeline.formats), 'clips': clips}


def _check_lengths(timeline, clips):
    """Refuse trims and transitions a clip is too short for, where every
    clip's length is known (until then the assembly is the judge)."""
    lengths = {c['id']: c['frames'] for c in clips if c['frames'] is not None}
    known = {c.id for c in timeline.clips if not c.is_footage}
    if not known <= set(lengths):
        return
    try:
        tf.place(timeline, lengths)
    except ValueError as exc:
        raise HTTPError(400, str(exc)) from None


def _summary(body):
    text = body.get('summary')
    if text is None:
        return 'edit the timeline'
    if not isinstance(text, str):
        raise HTTPError(400, 'summary must be a string')
    text = ' '.join(text.split())[:SUMMARY_MAX]
    return text or 'edit the timeline'


def write(editor, video, data, base, author, summary='edit the timeline'):
    """Commit `data` as the video's timeline file on main, if it loads and
    main's timeline file hasn't changed since `base`. Returns the new state
    (`read`) with `changed` and the version number `n`."""
    e = editor
    with e.lock, e.notes.video_lock(video):
        if e.sync:
            e.sync.before_commit()
        rel = _relpath(e, video)
        main = _main(e)
        if base not in git(e.root, 'rev-list', '--first-parent', 'main').splitlines():
            raise HTTPError(409, 'this timeline is from a version that is not on main; reload it')
        if base != main and git(e.root, 'diff', '--name-only', base, main, '--', rel):
            raise HTTPError(409, 'the timeline changed since you opened it (another tab, or the builder); '
                                 'reload to see it')
        if GitTree(e.root, main, _directory(e, video)).read(tf.NAME) is None:
            raise HTTPError(400, 'this video is not a film of clips: it has no timeline.json')
        try:
            timeline = tf.parse(data)
        except tf.TimelineError as exc:
            raise HTTPError(400, str(exc)) from None
        current = read(e, video)
        if current['timeline'] == data:
            return {**current, 'changed': False, 'n': e.versions.number(main)}
        _check_lengths(timeline, current.get('clips', []))
        path = os.path.join(e.root, rel)
        if git(e.root, 'status', '--porcelain', '--', rel):
            raise HTTPError(409, f'{rel} has uncommitted changes in the main checkout')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
        message = f'timeline({video}): {summary}\n\nVersion-kind: edit\nDirected-by: {author or "anonymous"}'
        try:
            commit = commit_path(e.root, path, message)
        except RuntimeError as exc:
            git(e.root, 'checkout', '--', rel)
            raise HTTPError(500, f'git would not commit the timeline: {exc}') from None
        e.project.last.pop(video, None)
        if e.sync:
            e.sync.after_commit()
        e.render_first(video, commit)
        return {**read(e, video), 'changed': True, 'n': e.versions.number(commit)}


def _thumb_at(timeline, clip, frames):
    """The media frame a clip's thumbnail shows: a little into what it shows."""
    first = clip.in_frame + clip.head if clip.is_footage else clip.head
    shown = (clip.out_frame - clip.in_frame if clip.is_footage else frames) - clip.head - clip.tail
    return first + max(0, min(timeline.fps // 2, shown // 2))


def thumbnail(editor, video, clip_id, sha, fmt):
    """JPEG bytes of clip `clip_id` at `sha`, or None while it has no render."""
    timeline = editor.renders.timeline(video, sha)
    if timeline is None:
        raise HTTPError(404, 'this video is not a film of clips')
    try:
        clip = timeline.clip(clip_id)
    except KeyError:
        raise HTTPError(404, 'no clip with that id in this video\'s timeline') from None
    fmt = fmt if fmt in timeline.formats else timeline.formats[0]
    if clip.is_footage:
        path = _footage_path(editor, video, clip)
    else:
        try:
            path = editor.renders.clip_cache(video).path(
                clip_key(GitTree(editor.root, sha, _directory(editor, video)), clip, fmt), fmt)
        except ValueError:
            path = None
    if path is None or not os.path.isfile(path):
        return None
    seconds, _ = _probe(str(path))
    if seconds is None:
        return None
    at = _thumb_at(timeline, clip, round(seconds * timeline.fps)) / timeline.fps
    stamp = os.stat(path).st_mtime_ns
    cache = Path(editor.state_dir) / 'timeline-thumbs'
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / (hashlib.sha256(f'{path}\0{stamp}\0{at:.3f}'.encode()).hexdigest()[:32] + '.jpg')
    if not out.is_file():
        partial = out.with_suffix('.partial.jpg')
        # Options ffmpeg 7.1 (the editor's image) and later both take.
        result = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{at:.3f}', '-i', str(path),
                                 '-frames:v', '1', '-vf', f'scale=-2:{THUMB_HEIGHT}', '-q:v', '5',
                                 '-f', 'image2', str(partial)], capture_output=True)
        if result.returncode or not partial.is_file():
            partial.unlink(missing_ok=True)
            return None
        partial.replace(out)
        kept = sorted(cache.glob('*.jpg'), key=lambda p: p.stat().st_mtime)
        for old in kept[:-THUMBS_KEPT]:
            old.unlink(missing_ok=True)
    return out.read_bytes()


# ---- routes (registered in video_api) ----

def _video(editor, video):
    try:
        editor.project.video(video)
    except KeyError:
        raise HTTPError(404, f'no video {video!r} in this project') from None


def get_timeline(self, route, q, editor, user):
    editor.main_moved()
    video = _need(q, 'video')
    _video(editor, video)
    return self._json(200, read(editor, video, q.get('format')))


def get_thumb(self, route, q, editor, user):
    video, clip = _need(q, 'video'), _need(q, 'clip')
    _video(editor, video)
    sha = q.get('commit') or _main(editor)
    if sha not in git(editor.root, 'rev-list', '--first-parent', 'main').splitlines():
        raise HTTPError(400, 'commit is not on main')
    data = thumbnail(editor, video, clip, sha, q.get('format'))
    if data is None:
        raise HTTPError(404, 'no render of this clip yet')
    return self._send(200, data, 'image/jpeg', {'Cache-Control': 'private, max-age=3600'})


def get_footage(self, route, q, editor, user):
    from .attachments import TYPES
    video, clip_id = _need(q, 'video'), _need(q, 'clip')
    _video(editor, video)
    timeline = editor.renders.timeline(video, _main(editor))
    clip = next((c for c in timeline.clips if c.id == clip_id and c.is_footage), None) if timeline else None
    if clip is None:
        raise HTTPError(404, 'no footage clip with that id in this video\'s timeline')
    path = _footage_path(editor, video, clip)
    kind = TYPES.get(os.path.splitext(clip.footage)[1].lstrip('.').lower())
    if path is None or not (kind or '').startswith('video/'):
        raise HTTPError(404, f'{clip.footage}: no such video file in the video\'s sources')
    return self._send_ranged_file(Path(path), kind, {'Accept-Ranges': 'bytes'})


def post_timeline(self, route, body, identity, editor, user):
    video = body.get('video')
    if not isinstance(video, str) or not video:
        raise HTTPError(400, 'missing video')
    _video(editor, video)
    base = body.get('base')
    if not isinstance(base, str) or not base:
        raise HTTPError(400, 'missing base: the commit the edit was made against')
    data = body.get('timeline')
    if not isinstance(data, dict):
        raise HTTPError(400, 'timeline must be the timeline file, as an object')
    return self._json(200, write(editor, video, data, base, identity, _summary(body)))
