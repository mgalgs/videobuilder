"""The editor's Film details sheet and a blank video's first clip (see
`film_setup` for what they write).

    GET  /api/film?video=V
         {commit, unbuilt, film, details}: `details` is {look, length, world,
         characters: [{slug, name, description, pictures: [file name...]}]},
         read from the bible at main; `film` whether the video is a film of
         clips (has a timeline file); `unbuilt` whether it is not built yet
    GET  /api/film/picture?video=V&name=N
         a character's picture, from beside its file in the bible
    POST /api/film {video, base, look, length, world, characters}
         save the sheet, the whole of it: a missing field is an empty one,
         so leaving `characters` out removes every character. Writes the
         bible's sections and characters that differ from main's, as one
         `Version-kind: edit` (see film_setup.
         parse_details for a character); a character's new pictures are
         already-uploaded attachments. 409 when main's bible changed since
         `base`; 200 the GET body with `changed` and the version number `n`
    POST /api/film/start {video, footage: source name | plan: {title, line}}
         make a video that isn't built yet a film of clips with this first
         clip (film_setup.start_files), as one `Version-kind: edit`; 409 for a
         video that is already built or already a film of clips; 200 the
         GET body with `n`

After the first clip the timeline adds more (POST /api/timeline, with `plans`
for a planned clip's directory).
"""
from pathlib import Path

from . import assembly, film_setup
from .editor import HTTPError, _need
from .gitutil import git


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


def read(editor, video):
    directory = _directory(editor, video)
    sha = git(editor.root, 'rev-parse', 'main')
    d = film_setup.read_details(directory)
    commits = git(editor.root, 'rev-list', '--first-parent', '--reverse', 'main').splitlines()
    return {'commit': sha, 'unbuilt': len(commits) <= editor.versions.unbuilt_until(video),
            'film': (directory / 'timeline.json').is_file(),
            'details': {'look': d.look, 'length': d.length, 'world': d.world, 'characters': d.characters}}


def _title(editor):
    return editor._title()


def save(editor, video, body, author):
    directory = _directory(editor, video)
    base = body.get('base')
    if not isinstance(base, str) or not base:
        raise HTTPError(400, 'missing base: the commit the sheet was opened at')
    with editor.lock:
        current = film_setup.read_details(directory)
        try:
            new, added = film_setup.parse_details(body, current)
        except ValueError as exc:
            raise HTTPError(400, str(exc)) from None
        pictures = {}
        for slug, ident in added:
            try:
                meta, path = editor.attachments.get(ident, video)
            except (KeyError, ValueError):
                raise HTTPError(400, f'no attachment {ident!r}; upload the picture again') from None
            if not meta['type'].startswith('image/') or meta['type'] == 'image/svg+xml':
                raise HTTPError(400, f'{meta["name"]} is not a picture: use a PNG, JPEG, WebP or GIF')
            pictures.setdefault(slug, []).append((meta['name'], path.read_bytes()))
        try:
            md = (directory / film_setup.BIBLE).read_text(errors='replace')
        except OSError:
            md = ''
        files = film_setup.bible_files(_title(editor), md, current, new, pictures)
        commit = editor.commit_files(video, files, _summary(current, new), author, base=base, watch=('bible',)) \
            if files else None
    out = read(editor, video)
    return {**out, 'changed': commit is not None, 'n': editor.versions.number(out['commit'])}


def _summary(current, new):
    parts = [name for name, a, b in (('look', current.look, new.look), ('length', current.length, new.length),
                                     ('world', current.world, new.world)) if a != b]
    before = {c['slug']: c for c in current.characters}
    after = {c['slug'] for c in new.characters}
    for c in new.characters:
        if c['slug'] not in before:
            parts.append(f'add {c["name"]}')
        elif any(before[c['slug']][k] != c[k] for k in ('name', 'description', 'pictures')):
            parts.append(c['name'])
    parts += [f'remove {c["name"]}' for slug, c in before.items() if slug not in after]
    return 'Film details: ' + (', '.join(parts) or 'characters')[:60]


def start(editor, video, body, author):
    """A blank video's first clip: footage or a planned clip."""
    _directory(editor, video)
    with editor.lock:
        state = read(editor, video)
        if state['film']:
            raise HTTPError(409, 'this video is already a film of clips: add clips on its timeline')
        if not state['unbuilt']:
            raise HTTPError(409, 'this video is already built as one film; ask the builder in a note to use '
                                 'footage or add clips')
        footage, plan = body.get('footage'), body.get('plan')
        if (footage is None) == (plan is None):
            raise HTTPError(400, 'give either footage (a source name) or plan ({title, line})')
        try:
            if footage is not None:
                if not isinstance(footage, str):
                    raise ValueError('footage must be a source name')
                try:
                    meta, path = editor.sources.file_path(video, footage)
                except KeyError:
                    raise ValueError(f'no source called {footage!r}; upload it first') from None
                seconds = assembly.probe(path)[1] if meta.get('width') is not None else None
                clip, extra = film_setup.footage_clip(meta, seconds), {}
                summary = f'Start the film: footage {meta["name"]}'
            else:
                if not isinstance(plan, dict):
                    raise ValueError('plan must be {title, line}')
                clip, extra = film_setup.planned_clip(plan.get('title'), plan.get('line'))
                summary = f'Start the film: plan {clip["id"]}'
            files = film_setup.start_files(_title(editor), clip, extra)
        except ValueError as exc:
            raise HTTPError(400, str(exc)) from None
        commit = editor.commit_files(video, files, summary, author, base=state['commit'], watch=('film.py',))
    out = read(editor, video)
    return {**out, 'n': editor.versions.number(commit or out['commit'])}


# ---- routes (registered in video_api) ----

def get_film(self, route, q, editor, user):
    return self._json(200, read(editor, _need(q, 'video')))


def get_picture(self, route, q, editor, user):
    from .attachments import TYPES
    video, name = _need(q, 'video'), _need(q, 'name')
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    path = _directory(editor, video) / film_setup.CHARACTERS / name
    if '/' in name or '\\' in name or name.startswith('.') or ext not in film_setup.PICTURE_EXTS \
            or not path.is_file():
        raise HTTPError(404, 'no such picture')
    return self._send(200, path.read_bytes(), TYPES.get(ext, 'application/octet-stream'),
                      {'Cache-Control': 'private, max-age=60'})


def post_film(self, route, body, identity, editor, user):
    return self._json(200, save(editor, _video(body), body, identity))


def post_start(self, route, body, identity, editor, user):
    return self._json(200, start(editor, _video(body), body, identity))
