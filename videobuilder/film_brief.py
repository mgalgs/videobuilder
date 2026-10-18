"""What a builder is told about a film made of clips (see `timeline_file`).

A note on a film of clips targets one clip (`note['clip']`, an id in the
video's timeline file) or the whole video (no `clip`). Either way the builder
gets the clips in order and the video's bible, if it has one; a clip note also
gets the clip's place in the film -- its number, act, what it is for (its film
file's docstring), the cuts either side -- and, staged under /attachments,
the last frame of the clip before it and the first frame of the clip after
it, when their renders are cached (a footage clip's frame comes from its
source). A neighbour whose render isn't cached yet is skipped quietly: the
prompt then says nothing of its frame.

`brief()` reads all of it at the commit the builder starts from and returns
(brief, grabs): `brief`, plain data for `prompt.render(film=...)`, and
`grabs`, [(side, name, grab)] for each neighbour frame that can be staged,
`grab(dest)` writing that frame's PNG to `dest` and saying whether it did.
`NoteStore._submit` stages them and records each staged one in
`brief[side]['frame']`. A video with no timeline file has no brief at all,
so its prompt is exactly what it was before films.

The bible is the optional `bible/` directory at the video's root:
`bible.md` (the film's look, world, tone and outline) and
`characters/<name>.md`, each optionally with pictures beside it. Builders
read it; nothing renders it.
"""
import ast
import posixpath
import subprocess
from pathlib import Path

from . import timeline_file
from .clip_cache import GitTree, clip_key

BIBLE = 'bible'
SHARED = 'shared'
PREVIOUS_FRAME = 'previous-clip-last-frame.png'
NEXT_FRAME = 'next-clip-first-frame.png'
BIBLE_LIST_MAX = 40
ABOUT_MAX = 400


def _rel(directory, path):
    """`path` (relative to the video's directory) relative to the repo root."""
    return posixpath.normpath(posixpath.join(directory, path)) if directory not in ('', '.') else path


def _about(tree, clip):
    """The first paragraph of a clip directory's film file's docstring: what
    the clip is for. None for footage, or a film without one."""
    if clip.is_footage:
        return None
    data = tree.read(clip.film_path)
    try:
        doc = ast.get_docstring(ast.parse(data or b''))
    except (SyntaxError, ValueError):
        return None
    if not doc:
        return None
    first = ' '.join(doc.strip().split('\n\n')[0].split())
    return first if len(first) <= ABOUT_MAX else first[:ABOUT_MAX - 1].rstrip() + '…'


def describe_cut(cut):
    """A cut in plain words: 'a hard cut', 'a dissolve over 12 frames'."""
    if cut.transition == 'cut':
        return 'a hard cut'
    if cut.transition == 'wipe':
        return f'a wipe to the {cut.direction} over {cut.frames} frames'
    return f'a {cut.transition} over {cut.frames} frames'


def _clip_info(timeline, clip, directory, tree):
    number = timeline.clips.index(clip) + 1
    act = next((a.title for a in timeline.acts if clip.id in a.clips), None)
    info = {'id': clip.id, 'number': number, 'act': act, 'about': _about(tree, clip)}
    if clip.is_footage:
        info.update(footage=_rel(directory, clip.footage), dir=None, film=None,
                    **{'in': clip.in_frame, 'out': clip.out_frame})
    else:
        info.update(footage=None, dir=_rel(directory, clip.dir), film=_rel(directory, clip.film_path))
    return info


def _ffmpeg_frame(source, index, fps, dest):
    """Write frame `index` (counted at `fps` from the start) of `source` to the
    PNG `dest`; whether it did. Seeks a quarter frame early, so float rounding
    never lands on the frame after: the accurate seek keeps the first frame at
    or after it. Plain options, the same on ffmpeg 7 and later."""
    t = max(0.0, (index - 0.25) / fps)
    try:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.6f}', '-i', str(source),
                        '-frames:v', '1', str(dest)], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return Path(dest).is_file() and Path(dest).stat().st_size > 0


def _frames(path, fps):
    from .assembly import probe
    _, duration, _ = probe(path)
    return round(duration * fps)


def _grab(timeline, clip, edge, video_root, render):
    """grab(dest) for the `edge` ('first' or 'last') frame `clip` shows in the
    film, or None when there is nothing to grab it from: a clip directory's
    cached render `render` (a Path, or None), or a footage clip's source."""
    fps = timeline.fps
    if clip.is_footage:
        source = Path(video_root) / clip.footage
        if not source.is_file():
            return None
        index = clip.in_frame + clip.head if edge == 'first' else clip.out_frame - clip.tail - 1

        def grab(dest):
            return _ffmpeg_frame(source, index, fps, dest)
        return grab
    if render is None or not render.is_file():
        return None

    def grab(dest):
        try:
            index = clip.head if edge == 'first' else _frames(render, fps) - clip.tail - 1
        except ValueError:
            return False
        # A render a hair shorter than its rounded length has no frame at the
        # last index: the one before it is the last there is.
        return _ffmpeg_frame(render, index, fps, dest) or (
            edge == 'last' and index > 0 and _ffmpeg_frame(render, index - 1, fps, dest))
    return grab


def brief(repo, sha, directory, clip_id, fmt, video_root, cache=None):
    """(brief, grabs) for a note on the video in `directory` of `repo` at
    commit `sha`, about clip `clip_id` (None: the whole video), in format
    `fmt`; or None when the video has no timeline file there. `video_root`
    is where its uploaded sources are on disk (the editor's checkout);
    `cache`, a `clip_cache.ClipCache`, is where its clip renders are, or None
    for no neighbour frames from clip directories."""
    tree = GitTree(repo, sha, directory)
    data = tree.read(timeline_file.NAME)
    if data is None:
        return None
    bible = tree.files(BIBLE)
    out = {'directory': directory, 'timeline': _rel(directory, timeline_file.NAME),
           'bible_dir': _rel(directory, BIBLE), 'bible': [_rel(directory, p) for p in bible[:BIBLE_LIST_MAX]],
           'bible_more': max(0, len(bible) - BIBLE_LIST_MAX), 'shared': _rel(directory, SHARED),
           'clips': [], 'clip': None, 'missing': None, 'before': None, 'after': None, 'error': None,
           'named': clip_id}
    try:
        timeline = timeline_file.loads(data.decode('utf-8', errors='replace'), timeline_file.NAME)
    except timeline_file.TimelineError as e:
        out['error'] = str(e)
        return out, []
    out['clips'] = [_clip_info(timeline, c, directory, tree) for c in timeline.clips]
    if clip_id is None:
        return out, []
    try:
        clip = timeline.clip(clip_id)
    except KeyError:
        out['missing'] = clip_id
        return out, []
    i = timeline.clips.index(clip)
    out['clip'] = out['clips'][i]
    fmt = fmt if fmt in timeline.formats else timeline.formats[0]
    grabs = []
    for side, j, edge, name in (('before', i - 1, 'last', PREVIOUS_FRAME), ('after', i + 1, 'first', NEXT_FRAME)):
        if not 0 <= j < len(timeline.clips):
            continue
        neighbour = timeline.clips[j]
        out[side] = {**out['clips'][j], 'frame': None,
                     'cut': describe_cut(clip.cut if side == 'before' else neighbour.cut)}
        render = None
        if not neighbour.is_footage and cache is not None:
            try:
                render = cache.path(clip_key(tree, neighbour, fmt), fmt)
            except ValueError:
                render = None
        grab = _grab(timeline, neighbour, edge, video_root, render)
        if grab:
            grabs.append((side, name, grab))
    return out, grabs


class FilmBrief:
    """The editor's `NoteStore.film`: `brief()` for a note's video at the commit
    its builder starts from (its draft, else main)."""

    def __init__(self, editor):
        self.editor = editor

    def __call__(self, video, note, state):
        from .drafts import git
        e = self.editor
        sha = None
        for ref in ([state['draft']] if state.get('draft') else []) + ['main']:
            try:
                sha = git(e.root, 'rev-parse', '--verify', ref + '^{commit}')
                break
            except ValueError:
                continue
        if sha is None:
            return None
        directory = e.drafts.context(video)['directory']
        return brief(e.root, sha, directory, note.get('clip'), note.get('format'),
                     Path(e.root) / directory, e.renders.clip_cache(video))
