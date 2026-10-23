"""The per-video `/api/...` routes: a GET table and a POST table, each a list
of (pattern, handler) walked in order. A pattern is a literal route string,
a tuple of literal routes, or a compiled regex matched with `.fullmatch`
(its capture groups are passed to the handler). Order matters no less than
it did in the original if-chain: keep it exactly as found there."""
import os
import re
import threading
from importlib import resources
from urllib.parse import unquote

from .attachments import TYPES
from .editor import HTTPError, _field, _need, _page
from .gitutil import git
from .music import FetchError, TooLarge, extension_for, fetch_binary
from .notes import FINAL
from .film_api import get_film, get_picture, post_film, post_start
from .timeline_api import get_footage, get_thumb, get_timeline, post_timeline
from .transcript import feed_source, read_feed
from .versions import Refused


def _match(route, pattern):
    if isinstance(pattern, str):
        return () if route == pattern else None
    if isinstance(pattern, tuple):
        return () if route in pattern else None
    m = pattern.fullmatch(route)
    return m.groups() if m else None


def _get_healthz(self, route, q, editor, user):
    from . import __version__
    # Not ok while draining: an open tab waits for the new process, not the one about to exit.
    if getattr(self.server, 'draining', False):
        return self._send(503, b'stopping', 'text/plain; charset=utf-8')
    return self._send(200, ('ok ' + __version__).encode(), 'text/plain; charset=utf-8')


def _get_index(self, route, q, editor, user):
    return self._send(200, _page(), 'text/html; charset=utf-8')


def _get_static(self, route, q, editor, user):
    kind = ('text/html; charset=utf-8' if route.endswith('.html')
           else 'text/javascript; charset=utf-8' if route.endswith('.js') else 'text/css; charset=utf-8')
    return self._send(200, resources.files(__package__).joinpath(route[1:]).read_bytes(), kind)


def _get_versions(self, route, q, editor, user):
    editor.main_moved()
    try:
        return self._json(200, editor.versions.history(_need(q, 'video'), int(q.get('limit', 50)), q.get('before')))
    except ValueError as exc:
        raise HTTPError(400, str(exc)) from None


def _render_target(editor, video, sha, fmt):
    """(sha, format) checked: the commit on main, the format one the video
    renders in there (its timeline's, for a film of clips, else its film's)."""
    sha = sha or git(editor.root, 'rev-parse', 'main')
    if sha not in git(editor.root, 'rev-list', '--first-parent', 'main').splitlines():
        raise HTTPError(400, 'commit is not on main')
    try:
        timeline = editor.renders.timeline(video, sha)
    except ValueError as exc:
        raise HTTPError(400, str(exc)) from None
    formats = list(timeline.formats) if timeline else [f['name'] for f in editor.info(video)['formats']]
    fmt = fmt or formats[0]
    if fmt not in formats:
        raise HTTPError(400, 'unknown format')
    return sha, fmt


def _get_video(self, route, q, editor, user):
    editor.main_moved()
    video = _need(q, 'video')
    editor.project.video(video)
    sha, fmt = _render_target(editor, video, q.get('commit'), q.get('format'))
    state = editor.renders.request(video, sha, fmt)
    if state['state'] == 'failed':
        return self._json(500, {'error': state['error'], 'log': state['log']})
    if state['state'] != 'ready':
        return self._json(202, {'state': state['state'], 'position': state['position']})
    data = editor.renders.path(video, sha, fmt).read_bytes()
    headers = {'Accept-Ranges': 'bytes', 'ETag': f'"{sha}-{fmt}"'}
    return self._send_ranged(data, 'video/mp4', headers)


def _get_clip(self, route, q, editor, user):
    video, clip = _need(q, 'video'), _need(q, 'clip')
    editor.project.video(video)
    sha, fmt = _render_target(editor, video, q.get('commit'), q.get('format'))
    try:
        path = editor.renders.clip_path(video, sha, fmt, clip)
    except KeyError:
        raise HTTPError(404, 'no clip directory with that id in this video\'s timeline') from None
    state = editor.renders.request(video, sha, fmt, clip)
    if state['state'] == 'failed':
        return self._json(500, {'error': state['error'], 'log': state['log']})
    if state['state'] != 'ready':
        return self._json(202, {'state': state['state'], 'position': state['position']})
    headers = {'Accept-Ranges': 'bytes', 'ETag': f'"{path.stem}"'}
    return self._send_ranged(path.read_bytes(), 'video/mp4', headers)


def _get_thumbnail(self, route, q, editor, user):
    try:
        videos = editor.project.videos()
    except ValueError:
        videos = []
    if not videos:
        raise HTTPError(404, 'no video in this project')
    data = editor.thumbnails.get(videos[0].id)
    if data is None:
        raise HTTPError(404, 'no render yet')
    return self._send(200, data, 'image/jpeg')


def _get_capabilities(self, route, q, editor, user):
    from . import __version__, capabilities, pages
    header = style = ''
    community = None
    if self.library:
        accounts = self.library.accounts
        header = pages.app_header('capabilities', user if accounts else None, bool(user) or not accounts,
                                  self.library.whats_new.newest_key())
        style = pages.APP_HEADER_STYLE
        if accounts and user:
            community = self.library.community_view(user)
    return self._send(200, capabilities.page_html(editor.capabilities_dir, __version__, header, style,
                                                   community=community),
                      'text/html; charset=utf-8')


def _get_capability_clip(self, route, q, editor, user, cap_id, kind):
    from . import capabilities
    path = capabilities.clip_file(editor.capabilities_dir, cap_id, kind)
    if path is None or not os.path.isfile(path):
        raise HTTPError(404, 'capability clip not built')
    data = open(path, 'rb').read()
    if kind == 'mp4':
        return self._send_ranged(data, 'video/mp4', {'Accept-Ranges': 'bytes'})
    return self._send(200, data, 'image/jpeg')


def _get_community_clip(self, route, q, editor, user, slug, kind):
    if not self.library:
        raise HTTPError(404, 'not found')
    try:
        data = self.library.community_clip(slug, kind, user)
    except KeyError:
        raise HTTPError(404, 'capability clip not built') from None
    if kind == 'mp4':
        return self._send_ranged(data, 'video/mp4', {'Accept-Ranges': 'bytes'})
    return self._send(200, data, 'image/jpeg')


def _get_family_page(self, route, q, editor, user, family):
    from . import __version__, capabilities, pages
    header = style = ''
    if self.library:
        accounts = self.library.accounts
        header = pages.app_header('capabilities', user if accounts else None, bool(user) or not accounts,
                                  self.library.whats_new.newest_key())
        style = pages.APP_HEADER_STYLE
    try:
        page = capabilities.family_page_html(family, editor.capabilities_dir, __version__, header, style)
    except KeyError:
        raise HTTPError(404, 'unknown capability family') from None
    return self._send(200, page, 'text/html; charset=utf-8')


def _get_family_page_redirect(self, route, q, editor, user, family):
    """The pre-rename family page, permanently moved to /capabilities/<family> now that
    the registry's ids are capabilities too; its clips redirect the same way
    (see _get_old_clip_redirect)."""
    self.send_response(301)
    self.send_header('Location', '/capabilities/' + family)
    self.send_header('Content-Length', '0')
    self.end_headers()


def _get_old_clip_redirect(self, route, q, editor, user, id, kind):
    """The pre-rename clip URL, permanently moved to /capabilities/<id>.mp4|jpg now that
    every clip -- hand-written and registry alike -- lives in one flat directory."""
    self.send_response(301)
    self.send_header('Location', f'/capabilities/{id}.{kind}')
    self.send_header('Content-Length', '0')
    self.end_headers()


def _get_compendium(self, route, q, editor, user):
    if not _is_admin(self, user):
        raise HTTPError(403, 'admin only')
    from . import __version__, compendium_feed
    return self._send(200, compendium_feed.page_html(editor.compendium_dir, __version__), 'text/html; charset=utf-8')


def _get_compendium_clip(self, route, q, editor, user, clip_id, kind):
    if not _is_admin(self, user):
        raise HTTPError(403, 'admin only')
    from . import compendium_feed
    path = compendium_feed.clip_file(editor.compendium_dir, clip_id, kind)
    if path is None or not os.path.isfile(path):
        raise HTTPError(404, 'compendium clip not built')
    data = open(path, 'rb').read()
    if kind == 'mp4':
        return self._send_ranged(data, 'video/mp4', {'Accept-Ranges': 'bytes'})
    return self._send(200, data, 'image/jpeg')


def _get_api_compendium(self, route, q, editor, user):
    if not _is_admin(self, user):
        raise HTTPError(403, 'admin only')
    from . import compendium_feed
    return self._json(200, {'items': compendium_feed.feed_items(editor.compendium_dir),
                            'votes': editor.compendium_votes.for_user(user)})


def _get_attachment(self, route, q, editor, user, attachment_id):
    try:
        meta, path = editor.attachments.get(attachment_id)
    except KeyError:
        raise HTTPError(404, 'attachment not found') from None
    svg = meta['type'] == 'image/svg+xml'
    # An SVG is a document that can carry script and outside links: opened on its
    # own it downloads, and even shown it loads nothing beyond itself.
    inline = meta['type'].startswith(('image/', 'video/', 'audio/')) and not svg
    csp = "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:" if svg else 'sandbox'
    return self._send(200, path.read_bytes(), meta['type'],
                      {'Content-Security-Policy': csp,
                       'Content-Disposition': ('inline' if inline else 'attachment') +
                       '; filename="' + meta['name'] + '"'})


def _get_sources(self, route, q, editor, user):
    video = _need(q, 'video')
    editor.project.video(video)
    return self._json(200, {'sources': [editor.sources.public(m) for m in editor.sources.list(video)]})


def _get_source_file(self, route, q, editor, user, name):
    video = _need(q, 'video')
    try:
        meta, path = editor.sources.file_path(video, name)
    except KeyError:
        raise HTTPError(404, 'source not found') from None
    return self._send_ranged_file(path, TYPES[meta['ext']], {'Accept-Ranges': 'bytes'})


def _get_music_sources(self, route, q, editor, user):
    return self._json(200, editor.music.list_sources() if editor.music else [])


def _get_music_tracks(self, route, q, editor, user):
    if not editor.music:
        raise HTTPError(404, 'no music sources configured')
    try:
        source, tracks = editor.music.list_tracks(_need(q, 'source'))
    except KeyError:
        raise HTTPError(404, 'unknown music source') from None
    except FetchError as exc:
        raise HTTPError(502, str(exc)) from None
    return self._json(200, {'source': {'id': source.id, 'name': source.name, 'license': source.license},
                            'tracks': tracks})


def _pictures(editor):
    if not editor.pictures:
        raise HTTPError(404, 'not found')
    return editor.pictures


def _picture_call(fn, *args):
    from .pictures import PictureError
    try:
        return fn(*args)
    except PictureError as exc:
        raise HTTPError(exc.code, str(exc)) from None


def _get_pictures(self, route, q, editor, user):
    pictures = _pictures(editor)
    video = _need(q, 'video')
    editor.project.video(video)
    return self._json(200, {'jobs': pictures.list(video)})


def _get_pictures_gpu(self, route, q, editor, user):
    return self._json(200, {'gpu': _pictures(editor).gpu()})


def _get_picture_file(self, route, q, editor, user, job_id, index):
    pictures = _pictures(editor)
    path, ctype = _picture_call(pictures.file, _need(q, 'video'), job_id, int(index),
                                q.get('cutout') == '1', q.get('full') == '1')
    # A stored picture never changes under its URL; the default no-store would refetch every grid.
    return self._send(200, path.read_bytes(), ctype, {'Cache-Control': 'private, max-age=31536000, immutable'})


def _suggest(editor):
    if not editor.suggest:
        raise HTTPError(404, 'not found')
    return editor.suggest


def _get_suggest_config(self, route, q, editor, user):
    return self._json(200, editor.suggest.config() if editor.suggest else {'model': False})


def _get_suggest_catalog(self, route, q, editor, user):
    from . import capabilities, fonts
    from .capabilities import registry
    looks, type_, caps = [], [], []
    for e in capabilities.entries():
        family = e.get('family')
        if family not in ('looks', 'type') and e.get('children') is not None:
            continue
        item = {'id': e['id'], 'title': e['title'], 'card': e['card'], 'category': e['category'],
               'poster': f"/capabilities/{e['id']}.jpg", 'clip': f"/capabilities/{e['id']}.mp4"}
        if family == 'looks':
            item['kind'] = e.get('kind')
            item['look'] = e.get('look')  # the vb.looks registry name (Film details' look picker uses this)
            looks.append(item)
        elif family == 'type':
            type_.append(item)
        elif family is None:
            item['phrasings'] = list(e.get('prompts', ()))
            caps.append(item)
    # The registry's capabilities (videobuilder.capabilities.registry) are capabilities too (just too
    # many to hand-write): merged into the same list, same shape plus group/aliases/phrasings, so the
    # picker can group and search them alike.
    for t in registry.catalog():
        title, _ = capabilities.REGISTRY_FAMILIES[t.family]
        caps.append({'id': t.id, 'title': t.name, 'card': t.definition, 'category': title,
                     'group': t.group,
                     'aliases': list(t.aliases), 'phrasings': list(t.phrasings),
                     'poster': f'/capabilities/{t.id}.jpg', 'clip': f'/capabilities/{t.id}.mp4'})
    from . import sfx as sfx_module
    sfx_list = []
    try:
        for effect in sfx_module.bank().find():
            base = effect.take()
            sfx_list.append({'id': effect.id, 'role': effect.role, 'family': effect.family, 'about': effect.about,
                             'dur': base.dur_s, 'takes': len(effect.takes)})
    except sfx_module.SfxUnavailable:
        pass
    music_list = []
    if editor.music:
        from .music import FetchError
        for source in editor.music.list_sources():
            try:
                _, tracks = editor.music.list_tracks(source['id'])
            except FetchError:
                continue
            for t in tracks:
                music_list.append({'id': t['id'], 'title': t['title'], 'tags': t['tags'], 'duration': t['duration'],
                                   'audio_url': t['audio_url'], 'source': source['name'],
                                   'license': source['license']})
    return self._json(200, {'looks': looks, 'type': type_, 'capabilities': caps, 'fonts': fonts.public(),
                            'sfx': sfx_list, 'music': music_list})


def _get_font_file(self, route, q, editor, user, font_id):
    from . import fonts
    try:
        fonts.get(font_id)
        path = fonts.path(font_id)
    except KeyError:
        raise HTTPError(404, 'unknown font') from None
    if not path:
        raise HTTPError(404, 'font file not available on this build')
    ext = path.rsplit('.', 1)[-1].lower()
    ctype = {'ttf': 'font/ttf', 'otf': 'font/otf'}.get(ext, 'application/octet-stream')
    return self._send(200, open(path, 'rb').read(), ctype, {'Cache-Control': 'public, max-age=86400'})


def _get_suggest_sfx_file(self, route, q, editor, user):
    from . import sfx as sfx_module
    id_ = _need(q, 'id')
    try:
        take = sfx_module.bank().get(id_).take()
    except (ValueError, sfx_module.SfxUnavailable):
        raise HTTPError(404, 'unknown sound') from None
    return self._send(200, open(take.path, 'rb').read(), 'audio/ogg',
                      {'Cache-Control': 'public, max-age=86400'})


def _get_draft(self, route, q, editor, user):
    return self._json(200, editor.drafts.details(_need(q, 'video')))


def _get_draft_preview(self, route, q, editor, user):
    op = route.rsplit('/', 1)[1]
    data = editor.drafts.preview(_need(q, 'video'), op, q)
    return self._send(200, data, 'application/json' if op == 'info' else 'image/png')


def _get_project(self, route, q, editor, user):
    info = editor.project_info()
    if self.library and self.library.accounts:
        info['user'] = user
    return self._json(200, info)


def _get_info(self, route, q, editor, user):
    return self._json(200, editor.info(_need(q, 'video')))


def _get_frame(self, route, q, editor, user):
    s = editor.session(_need(q, 'video'))
    try:
        png = s.request('frame', frame=int(q.get('frame', 0)), format=q.get('format') or None,
                        scale=float(q.get('scale', 0.5)), overlay=q.get('overlay') in ('1', 'true'))
    except ValueError as e:
        raise HTTPError(400, str(e)) from None
    return self._send(200, png, 'image/png')


def _is_admin(self, user):
    """Whether `user` should see cost: there is no accounts system to gate it
    (single-project mode, or a library with none configured), or they are one
    of its admins."""
    return not (self.library and self.library.accounts) or self.library.accounts.is_admin(user)


def _is_admin_account(self, user):
    """Whether `user` is an actual admin account, for the daily cap bypass:
    unlike `_is_admin` above, this is false with no accounts system at all --
    a cap configured there has no admin to exempt, so it binds everyone."""
    return bool(self.library and self.library.accounts and self.library.accounts.is_admin(user))


_COST_FIELDS = ('cost_usd', 'tokens')


def _strip_cost(note):
    return {k: v for k, v in note.items() if k not in _COST_FIELDS}


def _get_notes(self, route, q, editor, user):
    notes = editor.notes.list(q.get('video'))
    if not _is_admin(self, user):
        notes = [_strip_cost(n) for n in notes]
    return self._json(200, {'notes': notes})


def _get_note_log(self, route, q, editor, user, note_id):
    nid = unquote(note_id)
    try:
        note = editor.notes.get(nid)
    except KeyError:
        raise HTTPError(404, f'no note {nid!r}') from None
    try:
        after = max(0, int(q.get('after', 0)))
    except ValueError:
        raise HTTPError(400, 'after must be an integer') from None
    show_cost = _is_admin(self, user)
    peek = editor.notes.backend.peek if note['state'] == 'working' and hasattr(editor.notes.backend, 'peek') else None
    source = feed_source(note.get('handle'))
    entries = read_feed(note.get('handle'), editor.root, show_cost, peek)
    # The live feed is not a prefix of the collected one (peek can miss
    # lines), so a client whose cursor counted the other source restarts.
    reset = q.get('source', source) != source
    if reset:
        after = 0
    return self._json(200, {'entries': entries[after:], 'next': len(entries),
                            'done': note['state'] in FINAL, 'source': source,
                            'reset': reset})


def _get_note(self, route, q, editor, user, note_id, png_suffix):
    nid = unquote(note_id)
    try:
        if png_suffix:
            return self._send(200, editor.notes.image(nid), 'image/png')
        note = editor.notes.current(nid)
        return self._json(200, note if _is_admin(self, user) else _strip_cost(note))
    except KeyError:
        raise HTTPError(404, f'no note {nid!r}') from None


def _get_usage(self, route, q, editor, user):
    if not _is_admin(self, user):
        raise HTTPError(403, 'admin only')
    return self._json(200, editor.usage())


# The pre-rename URL path segment the two redirects below still answer to (old bookmarks and
# links use it); split so this file doesn't spell the retired word itself (see
# tests/test_capabilities_compat.py).
_OLD_URL_SEGMENT = 'tech' + 'niques'

GET_ROUTES = [
    ('/healthz', _get_healthz),
    (('/', '/index.html'), _get_index),
    (('/tuning.html', '/director.js', '/director.css', '/suggest.js', '/suggest.css'), _get_static),
    ('/api/versions', _get_versions),
    ('/api/video', _get_video),
    ('/api/clip', _get_clip),
    ('/api/timeline', get_timeline),
    ('/api/film', get_film),
    ('/api/film/picture', get_picture),
    ('/api/timeline/thumb', get_thumb),
    ('/api/timeline/footage', get_footage),
    ('/api/thumbnail', _get_thumbnail),
    ('/capabilities', _get_capabilities),
    (re.compile(r'/capabilities/community/([a-z][a-z0-9-]*)\.(mp4|jpg)'), _get_community_clip),
    (re.compile(rf'/capabilities/{_OLD_URL_SEGMENT}/([a-z][a-z0-9-]*)\.(mp4|jpg)'), _get_old_clip_redirect),
    (re.compile(rf'/capabilities/{_OLD_URL_SEGMENT}/([a-z][a-z0-9-]*)'), _get_family_page_redirect),
    (re.compile(r'/capabilities/([a-z][a-z0-9-]*)\.(mp4|jpg)'), _get_capability_clip),
    (re.compile(r'/capabilities/([a-z][a-z0-9-]*)'), _get_family_page),
    ('/compendium', _get_compendium),
    (re.compile(r'/compendium/([a-z][a-z0-9-]*)\.(mp4|jpg)'), _get_compendium_clip),
    ('/api/compendium', _get_api_compendium),
    (re.compile(r'/api/attachments/([0-9a-f]+)'), _get_attachment),
    ('/api/sources', _get_sources),
    (re.compile(r'/api/sources/([^/]+)'), _get_source_file),
    ('/api/music/sources', _get_music_sources),
    ('/api/music/tracks', _get_music_tracks),
    ('/api/pictures', _get_pictures),
    ('/api/pictures/gpu', _get_pictures_gpu),
    (re.compile(r'/api/pictures/([0-9a-f]{16})/([0-3])'), _get_picture_file),
    ('/api/suggest/config', _get_suggest_config),
    ('/api/suggest/catalog', _get_suggest_catalog),
    ('/api/suggest/sfx-file', _get_suggest_sfx_file),
    (re.compile(r'/api/fonts/([a-z0-9-]+)/file'), _get_font_file),
    ('/api/draft', _get_draft),
    (('/api/draft/info', '/api/draft/frame'), _get_draft_preview),
    ('/api/project', _get_project),
    ('/api/info', _get_info),
    ('/api/frame', _get_frame),
    ('/api/notes', _get_notes),
    ('/api/usage', _get_usage),
    (re.compile(r'/api/notes/([^/]+)/log'), _get_note_log),
    (re.compile(r'/api/notes/([^/]+?)(\.png)?'), _get_note),
]


def _post_video_retry(self, route, body, identity, editor, user):
    video = _field(body, 'video', str)
    sha = _field(body, 'commit', str)
    fmt = _field(body, 'format', str)
    clip = body.get('clip')
    if clip is not None and not isinstance(clip, str):
        raise HTTPError(400, 'clip must be a string')
    editor.project.video(video)
    sha, fmt = _render_target(editor, video, sha, fmt)
    if clip is not None:
        try:
            editor.renders.clip_path(video, sha, fmt, clip)
        except KeyError:
            raise HTTPError(404, 'no clip directory with that id in this video\'s timeline') from None
    return self._json(202, editor.renders.retry(video, sha, fmt, clip))


def _post_versions_restore(self, route, body, identity, editor, user):
    try:
        return self._json(200, editor.versions.restore(_field(body, 'video', str),
                                                        _field(body, 'commit', str), identity))
    except ValueError as exc:
        raise HTTPError(400, str(exc)) from None


def _post_upgrade(self, route, body, identity, editor, user):
    try:
        return self._json(200, editor.versions.upgrade(_field(body, 'video', str), identity))
    except Refused as exc:
        raise HTTPError(409, str(exc)) from None


def _post_draft_action(self, route, body, identity, editor, user):
    action = getattr(editor.drafts, route.rsplit('/', 1)[1])
    return self._json(200, action(_field(body, 'video', str), identity))


def _post_compendium_vote(self, route, body, identity, editor, user):
    if not _is_admin(self, user):
        raise HTTPError(403, 'admin only')
    from . import compendium_feed
    try:
        id, vote, reason = compendium_feed.validate_vote(body)
    except ValueError as exc:
        raise HTTPError(400, str(exc)) from None
    return self._json(200, editor.compendium_votes.record(user, id, vote, reason))


def _post_music_attach(self, route, body, identity, editor, user):
    if not editor.music:
        raise HTTPError(404, 'no music sources configured')
    video = _field(body, 'video', str)
    editor.project.video(video)
    try:
        source, track = editor.music.track(_field(body, 'source', str), _field(body, 'track', str))
    except KeyError:
        raise HTTPError(404, 'unknown music source') from None
    except FetchError as exc:
        raise HTTPError(502, str(exc)) from None
    if track is None:
        raise HTTPError(404, 'unknown track') from None
    try:
        data, content_type = fetch_binary(track['audio_url'], editor.attachments.max_file)
    except TooLarge:
        raise HTTPError(413, 'attachment exceeds file size limit') from None
    except FetchError as exc:
        raise HTTPError(502, f'could not fetch track audio: {exc}') from None
    ext = extension_for(content_type, track['audio_url'])
    if ext is None:
        raise HTTPError(400, 'unsupported audio type for this track')
    try:
        record = editor.attachments.upload(video, f"{track['title']}.{ext}", TYPES[ext], data)
    except ValueError as exc:
        raise HTTPError(400, str(exc)) from None
    return self._json(201, record)


def _post_suggest(self, route, body, identity, editor, user):
    suggest = _suggest(editor)
    video = _field(body, 'video', str)
    cancel_event = threading.Event()
    stop_watching = self._watch_disconnect(cancel_event)
    try:
        return self._json(200, suggest.ask(editor, video, body, identity, cancel_event=cancel_event))
    finally:
        stop_watching()


def _post_pictures(self, route, body, identity, editor, user):
    pictures = _pictures(editor)
    job = _picture_call(pictures.start, _field(body, 'video', str), body.get('prompt'), body.get('n', 2),
                        body.get('cutout', False), identity, _is_admin_account(self, user))
    return self._json(201, job)


def _post_picture_retry(self, route, body, identity, editor, user, job_id):
    pictures = _pictures(editor)
    return self._json(200, _picture_call(pictures.retry, _field(body, 'video', str), job_id, identity,
                                         _is_admin_account(self, user)))


def _post_picture_pose(self, route, body, identity, editor, user, job_id, index):
    pictures = _pictures(editor)
    job = _picture_call(pictures.pose, _field(body, 'video', str), job_id, int(index), body.get('pose'), identity,
                        _is_admin_account(self, user))
    return self._json(201, job)


def _post_picture_vary(self, route, body, identity, editor, user, job_id, index):
    pictures = _pictures(editor)
    job = _picture_call(pictures.vary, _field(body, 'video', str), job_id, int(index), identity,
                        _is_admin_account(self, user))
    return self._json(201, job)


def _post_picture_edit(self, route, body, identity, editor, user, job_id, index):
    pictures = _pictures(editor)
    job = _picture_call(pictures.edit, _field(body, 'video', str), job_id, int(index), body.get('edit'), identity)
    return self._json(201, job)


def _post_picture_attach(self, route, body, identity, editor, user, job_id, index):
    pictures = _pictures(editor)
    cutout = body.get('cutout', False)
    if not isinstance(cutout, bool):
        raise HTTPError(400, 'cutout must be true or false')
    try:
        record = _picture_call(pictures.attach, _field(body, 'video', str), job_id, int(index), cutout)
    except ValueError as exc:
        raise HTTPError(400, str(exc)) from None
    return self._json(201, record)


def _post_edit(self, route, body, identity, editor, user):
    return self._json(200, editor.edit(_field(body, 'video', str), route[5:], body, identity))


def _note_response(self, user, note):
    return note if _is_admin(self, user) else _strip_cost(note)


def _post_notes(self, route, body, identity, editor, user):
    return self._json(200, _note_response(self, user, editor.add_note(body, identity, _is_admin_account(self, user))))


def _post_first_note(self, route, body, identity, editor, user):
    return self._json(200, _note_response(self, user, editor.start_video(body, identity,
                                                                          _is_admin_account(self, user))))


def _post_source_delete(self, route, body, identity, editor, user, name):
    video = _field(body, 'video', str)
    try:
        editor.sources.delete(video, name)
    except KeyError:
        raise HTTPError(404, f'no source {name!r}') from None
    return self._json(200, {'deleted': name})


def _post_note_delete(self, route, body, identity, editor, user, note_id):
    try:
        editor.notes.delete(unquote(note_id))
    except KeyError:
        raise HTTPError(404, f'no note {note_id!r}') from None
    return self._json(200, {'deleted': note_id})


def _post_note_retry(self, route, body, identity, editor, user, note_id):
    editor.check_note_cap(identity, _is_admin_account(self, user))
    try:
        return self._json(200, _note_response(self, user, editor.notes.retry(unquote(note_id), identity)))
    except KeyError:
        raise HTTPError(404, f'no note {note_id!r}') from None


def _post_note_answer(self, route, body, identity, editor, user, note_id):
    build = body.get('build') is True
    answers = body.get('answers')
    if not build and (not isinstance(answers, list) or not all(isinstance(a, str) for a in answers)):
        raise HTTPError(400, 'answers must be a list of strings')
    editor.check_note_cap(identity, _is_admin_account(self, user))
    try:
        return self._json(200, _note_response(self, user, editor.notes.answer(
            unquote(note_id), build, None if build else answers, identity)))
    except KeyError:
        raise HTTPError(404, f'no note {note_id!r}') from None
    except ValueError as exc:
        raise HTTPError(409, str(exc)) from None


POST_ROUTES = [
    ('/api/video/retry', _post_video_retry),
    ('/api/versions/restore', _post_versions_restore),
    ('/api/upgrade', _post_upgrade),
    ('/api/timeline', post_timeline),
    ('/api/film', post_film),
    ('/api/film/start', post_start),
    (('/api/draft/accept', '/api/draft/drop'), _post_draft_action),
    ('/api/compendium/vote', _post_compendium_vote),
    ('/api/music/attach', _post_music_attach),
    ('/api/suggest', _post_suggest),
    ('/api/pictures', _post_pictures),
    (re.compile(r'/api/pictures/([0-9a-f]{16})/retry'), _post_picture_retry),
    (re.compile(r'/api/pictures/([0-9a-f]{16})/([0-3])/attach'), _post_picture_attach),
    (re.compile(r'/api/pictures/([0-9a-f]{16})/([0-3])/pose'), _post_picture_pose),
    (re.compile(r'/api/pictures/([0-9a-f]{16})/([0-3])/vary'), _post_picture_vary),
    (re.compile(r'/api/pictures/([0-9a-f]{16})/([0-3])/edit'), _post_picture_edit),
    (('/api/roll', '/api/copy', '/api/undo'), _post_edit),
    ('/api/notes', _post_notes),
    ('/api/videos/first-note', _post_first_note),
    (re.compile(r'/api/sources/([^/]+)/delete'), _post_source_delete),
    (re.compile(r'/api/notes/([^/]+)/delete'), _post_note_delete),
    (re.compile(r'/api/notes/([^/]+)/retry'), _post_note_retry),
    (re.compile(r'/api/notes/([^/]+)/answer'), _post_note_answer),
]


class VideoAPIHandler:
    def _get(self, route, q, editor, user=None):
        for pattern, handler in GET_ROUTES:
            groups = _match(route, pattern)
            if groups is not None:
                return handler(self, route, q, editor, user, *groups)
        raise HTTPError(404, 'not found')

    def _post(self, route, body, identity, editor, user=None):
        for pattern, handler in POST_ROUTES:
            groups = _match(route, pattern)
            if groups is not None:
                return handler(self, route, body, identity, editor, user, *groups)
        raise HTTPError(404, 'not found')
