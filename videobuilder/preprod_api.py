"""Pre-production's per-video routes: the board, the script and option-set
images, and the edits that commit into the bible (see preprod.py for the
file formats, docs/preproduction.md for the full API reference).

    GET  /api/preprod?video=V
         {commit, phase, logline, look: {text, set}, script: {exists, draft,
         title, scenes}, characters: [{...character, set}], sets: [...],
         scenes: {songs, scenes: [{...scene, number, length, from_clock,
         to_clock, set}], seconds, length}, checklist, problems}
    GET  /api/preprod/script?video=V[&draft=N]
         {commit, text, title, draft, scenes: [{number,heading,line}],
         elements: [{type,text,line,scene}], drafts: [{n,commit,time}]}
    GET  /api/preprod/image?video=V&path=P
         the bytes of a picture under this video's bible/
    POST /api/preprod/script {video, base, text}
         commit bible/script.fountain; 200 the script GET body plus
         `changed`, `n`; 409 when the script changed since `base`
    POST /api/preprod/scenes {video, base, songs, scenes}
         replace bible/scenes.json whole; 200 the board body plus
         `changed`, `n`
    POST /api/preprod/sets {video, base, set}
         create or replace one option set; an option may carry
         `upload: <attachment id>` instead of `image`/`kind`, copied in as
         kind "yours"; 200 the board body plus `changed`, `n`
    POST /api/preprod/sets/delete {video, base, id}
         remove a set and its images; 404 for no such set
    POST /api/preprod/pick {video, set, key|null}
         record (or clear) a set's pick; 404 for no such set, 400 for an
         unknown key
"""
from pathlib import Path
import time

from . import film_setup, fountain, preprod
from .clip_cache import GitTree
from .editor import HTTPError, _need
from .gitutil import git
from .notes import valid_choice_image

SCRIPT_MAX = 200_000
SCRIPT_LOG_LIMIT = 50
RENDER_REFUSED = 'This video is in pre-production: nothing renders until production starts.'


def refuse_if_preproduction(editor, video):
    """Raise HTTPError(409) for a render request (GET /api/video, GET
    /api/clip, POST /api/video/retry) against a video still in
    pre-production -- stills (/api/frame and friends) aren't renders and
    don't call this."""
    if preprod.read_phase(_directory(editor, video)) == 'pre-production':
        raise HTTPError(409, RENDER_REFUSED)


def _directory(editor, video):
    try:
        return Path(editor.project.video(video).path).parent
    except KeyError:
        raise HTTPError(404, f'no video {video!r} in this project') from None


def _video(body):
    video = body.get('video')
    if not isinstance(video, str) or not video:
        raise HTTPError(400, 'missing video')
    return video


def _base(body):
    base = body.get('base')
    if not isinstance(base, str) or not base:
        raise HTTPError(400, 'missing base: the commit this was opened at')
    return base


def _safe(problems, path, fn, *args):
    try:
        return fn(*args)
    except ValueError as exc:
        problems.append({'file': path, 'error': str(exc)})
        return None


# ---- the board ----

def read_board(editor, video):
    directory = _directory(editor, video)
    sha = git(editor.root, 'rev-parse', 'main')
    problems = []
    details = film_setup.read_details(directory)
    sets = [s for sid in preprod.list_set_ids(directory)
           for s in [_safe(problems, preprod.set_path(sid), preprod.read_set, directory, sid)] if s]
    by_id = {s['id']: s for s in sets}

    characters = [{**c, 'set': sid if sid in by_id else None}
                 for c in details.characters for sid in [preprod.set_id_for_character(c['slug'])]]

    scene_plan = _safe(problems, preprod.SCENES_FILE, preprod.read_scenes, directory)
    songs = scene_plan['songs'] if scene_plan else []
    songs_by_id = {s['id']: s for s in songs}
    raw_scenes = scene_plan['scenes'] if scene_plan else []
    total_seconds = sum(s['seconds'] for s in raw_scenes)
    scenes_out = []
    for i, s in enumerate(raw_scenes):
        sid = preprod.set_id_for_scene(s['id'])
        scenes_out.append({**s, 'number': i + 1, 'length': preprod.clock(s['seconds']),
                           'from_clock': preprod.clock(s['from']) if s['from'] is not None else None,
                           'to_clock': preprod.clock(s['to']) if s['to'] is not None else None,
                           'set': sid if sid in by_id else None})

    try:
        script_text = (directory / preprod.SCRIPT_FILE).read_text()
    except OSError:
        script_text = None
    if script_text is not None:
        parsed = fountain.parse(script_text)
        script = {'exists': True, 'draft': parsed['draft'], 'title': parsed['title'],
                  'scenes': len(parsed['scenes'])}
    else:
        script = {'exists': False, 'draft': None, 'title': None, 'scenes': 0}

    return {
        'commit': sha,
        'phase': preprod.read_phase(directory),
        'logline': preprod.read_logline(directory),
        'look': {'text': preprod.read_bible_section(directory, 'Look'), 'set': 'look' if 'look' in by_id else None},
        'script': script,
        'characters': characters,
        'sets': sets,
        'scenes': {'songs': songs, 'scenes': scenes_out, 'seconds': total_seconds,
                   'length': preprod.clock(total_seconds)},
        'checklist': preprod.checklist(directory),
        'problems': problems,
    }


def get_preprod(self, route, q, editor, user):
    return self._json(200, read_board(editor, _need(q, 'video')))


def get_image(self, route, q, editor, user):
    from .attachments import TYPES
    video, path = _need(q, 'video'), _need(q, 'path')
    directory = _directory(editor, video)
    full = directory / path
    if not valid_choice_image(path) or not full.is_file():
        raise HTTPError(404, 'no such picture')
    ext = path.rsplit('.', 1)[-1].lower()
    return self._send(200, full.read_bytes(), TYPES.get(ext, 'application/octet-stream'),
                      {'Cache-Control': 'private, max-age=60'})


# ---- the script ----

def _rel(editor, directory, path):
    root = Path(editor.root).resolve()
    return str((directory / path).resolve().relative_to(root))


def _prefix(editor, directory):
    return str(Path(directory).resolve().relative_to(Path(editor.root).resolve()))


def script_drafts(editor, directory, video):
    """[{n, commit, time}], newest draft first: the newest commit (within
    the last SCRIPT_LOG_LIMIT that touched the file) for each distinct
    title-page Draft number."""
    try:
        out = git(editor.root, 'log', '--first-parent', '--format=%H %ct', 'main', '--',
                  _rel(editor, directory, preprod.SCRIPT_FILE))
    except ValueError:
        return []
    drafts = {}
    for line in out.splitlines()[:SCRIPT_LOG_LIMIT]:
        sha, _, ts = line.partition(' ')
        data = GitTree(editor.root, sha, _prefix(editor, directory)).read(preprod.SCRIPT_FILE)
        if data is None:
            continue
        _, draft, _ = fountain.parse_title_page(data.decode('utf-8', 'replace'))
        if draft is not None and draft not in drafts:
            drafts[draft] = {'n': draft, 'commit': sha, 'time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(ts)))}
    return [drafts[n] for n in sorted(drafts, reverse=True)]


def _script_body(editor, directory, video, draft_q=None):
    drafts = script_drafts(editor, directory, video)
    if draft_q is not None:
        try:
            draft_n = int(draft_q)
        except (TypeError, ValueError):
            raise HTTPError(400, 'draft must be a number') from None
        entry = next((d for d in drafts if d['n'] == draft_n), None)
        if entry is None:
            raise HTTPError(404, f'no draft {draft_n}')
        text = GitTree(editor.root, entry['commit'], _prefix(editor, directory)).read(preprod.SCRIPT_FILE)
        commit = entry['commit']
        if text is None:
            raise HTTPError(404, f'no draft {draft_n}')
        text = text.decode('utf-8', 'replace')
    else:
        try:
            text = (directory / preprod.SCRIPT_FILE).read_text()
        except OSError:
            raise HTTPError(404, 'this video has no script yet') from None
        commit = git(editor.root, 'rev-parse', 'main')
    parsed = fountain.parse(text)
    return {'commit': commit, 'text': text, 'title': parsed['title'], 'draft': parsed['draft'],
            'scenes': parsed['scenes'], 'elements': parsed['elements'], 'drafts': drafts}


def get_script(self, route, q, editor, user):
    video = _need(q, 'video')
    directory = _directory(editor, video)
    return self._json(200, _script_body(editor, directory, video, q.get('draft')))


def _script_summary(text):
    _, draft, _ = fountain.parse_title_page(text)
    return f'Script, draft {draft}' if draft else 'Script'


def post_script(self, route, body, identity, editor, user):
    video = _video(body)
    directory = _directory(editor, video)
    base = _base(body)
    text = body.get('text')
    if not isinstance(text, str) or len(text) > SCRIPT_MAX:
        raise HTTPError(400, f'text must be a string of at most {SCRIPT_MAX} characters')
    with editor.lock:
        commit = editor.commit_files(video, {preprod.SCRIPT_FILE: text.encode()}, _script_summary(text), identity,
                                     base=base, watch=(preprod.SCRIPT_FILE,))
    out = _script_body(editor, directory, video)
    return self._json(200, {**out, 'changed': commit is not None, 'n': editor.versions.number(out['commit'])})


# ---- scenes ----

def post_scenes(self, route, body, identity, editor, user):
    video = _video(body)
    base = _base(body)
    try:
        data = preprod.parse_scenes(body)
    except ValueError as exc:
        raise HTTPError(400, str(exc)) from None
    with editor.lock:
        commit = editor.commit_files(video, {preprod.SCENES_FILE: preprod.scenes_bytes(data)}, 'Scene plan',
                                     identity, base=base, watch=(preprod.SCENES_FILE,))
    out = read_board(editor, video)
    return self._json(200, {**out, 'changed': commit is not None, 'n': editor.versions.number(out['commit'])})


# ---- option sets ----

def post_sets(self, route, body, identity, editor, user):
    video = _video(body)
    base = _base(body)
    raw_set = body.get('set')
    if not isinstance(raw_set, dict):
        raise HTTPError(400, 'missing set')
    try:
        data = preprod.parse_option_set(raw_set)
    except ValueError as exc:
        raise HTTPError(400, str(exc)) from None
    files = {}
    with editor.lock:
        for i, raw in enumerate(raw_set.get('options') or []):
            upload = raw.get('upload') if isinstance(raw, dict) else None
            if not upload:
                continue
            try:
                meta, path = editor.attachments.get(upload, video)
            except (KeyError, ValueError):
                raise HTTPError(400, f'no attachment {upload!r}; upload the picture again') from None
            if not meta['type'].startswith('image/') or meta['type'] == 'image/svg+xml':
                raise HTTPError(400, f'{meta["name"]} is not a picture: use a PNG, JPEG, WebP or GIF')
            ext = meta['name'].rsplit('.', 1)[-1].lower()
            if ext not in film_setup.PICTURE_EXTS:
                ext = 'png'
            img_path = f'{preprod.set_image_dir(data["id"])}/{data["options"][i]["key"]}.{ext}'
            files[img_path] = path.read_bytes()
            data['options'][i] = {**data['options'][i], 'image': img_path, 'kind': 'yours'}
        files[preprod.set_path(data['id'])] = preprod.set_bytes(data)
        commit = editor.commit_files(video, files, f'Options: {data["id"]}', identity, base=base,
                                     watch=(preprod.set_path(data['id']),))
    out = read_board(editor, video)
    return self._json(200, {**out, 'changed': commit is not None, 'n': editor.versions.number(out['commit'])})


def post_sets_delete(self, route, body, identity, editor, user):
    video = _video(body)
    directory = _directory(editor, video)
    set_id = body.get('id')
    if not isinstance(set_id, str):
        raise HTTPError(400, 'missing id')
    with editor.lock:
        if not (directory / preprod.set_path(set_id)).is_file():
            raise HTTPError(404, f'no such option set {set_id!r}')
        commit = editor.commit_files(video, preprod.delete_set_files(directory, set_id),
                                     f'Remove options: {set_id}', identity)
    out = read_board(editor, video)
    return self._json(200, {**out, 'changed': commit is not None, 'n': editor.versions.number(out['commit'])})


def post_phase(self, route, body, identity, editor, user, is_admin):
    video = _video(body)
    phase = body.get('phase')
    if phase not in preprod.PHASES:
        raise HTTPError(400, f'phase must be one of {", ".join(preprod.PHASES)}')
    return self._json(200, editor.set_phase(video, phase, identity, is_admin))


def post_pick(self, route, body, identity, editor, user):
    video = _video(body)
    directory = _directory(editor, video)
    set_id = body.get('set')
    if not isinstance(set_id, str):
        raise HTTPError(400, 'missing set')
    key = body.get('key')
    if key is not None and not isinstance(key, str):
        raise HTTPError(400, 'key must be a string or null')
    with editor.lock:
        try:
            data = preprod.read_set(directory, set_id)
        except ValueError as exc:
            raise HTTPError(400, str(exc)) from None
        if data is None:
            raise HTTPError(404, f'no such option set {set_id!r}')
        if key is not None and key not in [o['key'] for o in data['options']]:
            raise HTTPError(400, f'no option {key!r} in {set_id!r}')
        commit = editor.commit_files(video, {preprod.set_path(set_id): preprod.set_bytes({**data, 'pick': key})},
                                     f'Pick: {set_id} {key or "cleared"}', identity)
    out = read_board(editor, video)
    return self._json(200, {**out, 'changed': commit is not None, 'n': editor.versions.number(out['commit'])})
