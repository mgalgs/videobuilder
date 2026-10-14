"""Pluggable music sources for the director: browse a library, preview a track,
and attach one to a note, without naming any particular service.

Configured with `--music-sources FILE`, a TOML file holding a list of sources.
Each needs `id` (kebab-case), `name` (shown in the picker) and `license` (a
free-text label, e.g. "CC BY-NC 4.0"); then either a mapping source:

    [[sources]]
    id = "example-library"
    name = "Example Library"
    license = "CC BY-NC 4.0"
    url = "https://music.example.com/api/tracks.json"
    [sources.fields]
    tracks = "tracks"            # dotted path to the list, "" for a top-level list
    id = "id"
    title = "title"
    audio_url = "download_url"
    tags = "tags"                # optional
    duration = "length_ms"       # optional
    duration_unit = "ms"         # "ms" or "s" (default "s")

or an entry-point source, a Python callable that fetches and returns its own
already-normalised tracks:

    [[sources]]
    id = "example-catalog"
    name = "Example Catalog"
    license = "Public domain"
    entry_point = "example_catalog.music:list_tracks"

`list_tracks(source_config)` receives this source's own table (including its
`id`/`name`/`license`/`entry_point`) and returns an iterable of dicts with
`id`, `title`, `audio_url` and, optionally, `tags` and `duration` (seconds).

A normalised track is `{id, title, tags: [str], duration: seconds|None,
audio_url}`; one missing `id`, `title` or `audio_url`, or whose `audio_url`
is not http(s), is skipped rather than raising. The track list is fetched
with a timeout and a size cap, and cached per source for `CACHE_TTL`
seconds; a refetch failure serves the stale cache instead of raising, when
there is one to serve.
"""
import importlib
import json
import re
import threading
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

FETCH_TIMEOUT = 10
FETCH_MAX_BYTES = 5 * 1024 * 1024
CACHE_TTL = 600
SOURCE_ID = re.compile(r'[a-z0-9]+(-[a-z0-9]+)*')


class FetchError(ValueError):
    """A track list or a track's audio could not be fetched."""


class TooLarge(FetchError):
    """A fetch exceeded its byte cap."""


def fetch_binary(url, max_bytes, timeout=FETCH_TIMEOUT):
    """GET url, capped at max_bytes; (data, content_type), or raises FetchError/TooLarge."""
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'videobuilder-music/1'})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read(max_bytes + 1)
            content_type = response.headers.get('Content-Type', '')
    except (urllib.error.URLError, OSError) as exc:
        raise FetchError(f'{url}: {exc}') from None
    if len(data) > max_bytes:
        raise TooLarge(f'{url}: response exceeds {max_bytes} bytes')
    return data, content_type


def extension_for(content_type, url):
    """The attachment extension for a fetched track, from its Content-Type, else
    the audio_url's own extension; None when neither is a supported audio type."""
    from .attachments import TYPES
    ctype = (content_type or '').split(';', 1)[0].strip().lower()
    reverse = {}
    for ext, t in TYPES.items():
        reverse.setdefault(t, ext)
    ext = reverse.get(ctype)
    if ext:
        return ext
    suffix = Path(urlparse(url).path).suffix.lstrip('.').lower()
    return suffix if suffix in TYPES else None


def _get_path(obj, dotted):
    cur = obj
    for part in dotted.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _coerce_str(value):
    if isinstance(value, str):
        return value or None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def finalize_track(raw):
    """A {id,title,tags,duration,audio_url} normalised track from a loosely-typed
    dict, or None when it is missing id/title/audio_url or audio_url isn't http(s)."""
    id_ = _coerce_str(raw.get('id'))
    title = _coerce_str(raw.get('title'))
    audio_url = raw.get('audio_url')
    if id_ is None or title is None or not isinstance(audio_url, str):
        return None
    if urlparse(audio_url).scheme not in ('http', 'https'):
        return None
    tags = raw.get('tags')
    tags = [str(t) for t in tags] if isinstance(tags, list) else []
    duration = raw.get('duration')
    duration = float(duration) if isinstance(duration, (int, float)) and not isinstance(duration, bool) else None
    return {'id': id_, 'title': title, 'tags': tags, 'duration': duration, 'audio_url': audio_url}


def _mapping_tracks(doc, fields):
    items = doc if fields['tracks'] == '' else _get_path(doc, fields['tracks'])
    if not isinstance(items, list):
        raise ValueError(f'the tracks field {fields["tracks"]!r} is not a list')
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        duration = _get_path(item, fields['duration']) if fields['duration'] else None
        if fields['duration_unit'] == 'ms' and isinstance(duration, (int, float)) and not isinstance(duration, bool):
            duration = duration / 1000
        finalized = finalize_track({
            'id': _get_path(item, fields['id']),
            'title': _get_path(item, fields['title']),
            'audio_url': _get_path(item, fields['audio_url']),
            'tags': _get_path(item, fields['tags']) if fields['tags'] else None,
            'duration': duration,
        })
        if finalized:
            out.append(finalized)
    return out


def _load_entry_point(entry_point):
    parts = entry_point.split(':')
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f'entry_point must be "module:function", got {entry_point!r}')
    module_name, func_name = parts
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise ValueError(f'entry_point {entry_point!r}: cannot import {module_name!r}: {exc}') from None
    func = getattr(module, func_name, None)
    if not callable(func):
        raise ValueError(f'entry_point {entry_point!r}: {func_name!r} is not callable in {module_name!r}')
    return func


def _validate_fields(source_id, fields):
    if not isinstance(fields, dict):
        raise ValueError(f'{source_id}: a mapping source needs a [sources.fields] table')
    for key in ('id', 'title', 'audio_url'):
        if not isinstance(fields.get(key), str):
            raise ValueError(f'{source_id}: fields.{key} must be a dotted path string')
    for key in ('tracks', 'tags', 'duration'):
        if key in fields and not isinstance(fields[key], str):
            raise ValueError(f'{source_id}: fields.{key} must be a dotted path string')
    unit = fields.get('duration_unit', 's')
    if unit not in ('ms', 's'):
        raise ValueError(f'{source_id}: fields.duration_unit must be "ms" or "s"')
    return {'tracks': fields.get('tracks', ''), 'id': fields['id'], 'title': fields['title'],
            'audio_url': fields['audio_url'], 'tags': fields.get('tags'), 'duration': fields.get('duration'),
            'duration_unit': unit}


class Source:
    """One configured source: either a JSON mapping fetched from `url`, or an
    entry-point callable. `fetch_tracks` raises FetchError on failure."""

    def __init__(self, id, name, license, kind, url=None, fields=None, entry_point=None, func=None, config=None):
        self.id, self.name, self.license, self.kind = id, name, license, kind
        self.url, self.fields, self.entry_point, self.func, self.config = url, fields, entry_point, func, config

    def fetch_tracks(self):
        if self.kind == 'mapping':
            data, _ = fetch_binary(self.url, FETCH_MAX_BYTES)
            try:
                doc = json.loads(data)
                return _mapping_tracks(doc, self.fields)
            except ValueError as exc:
                raise FetchError(f'{self.url}: {exc}') from None
        try:
            results = self.func(self.config)
            out = []
            for item in results:
                if isinstance(item, dict):
                    finalized = finalize_track(item)
                    if finalized:
                        out.append(finalized)
        except Exception as exc:
            raise FetchError(f'{self.entry_point}: {exc}') from None
        return out


def _build_source(raw):
    if not isinstance(raw, dict):
        raise ValueError('each source must be a table')
    id_ = raw.get('id')
    if not isinstance(id_, str) or not SOURCE_ID.fullmatch(id_):
        raise ValueError(f'id must be kebab-case, got {id_!r}')
    name = raw.get('name')
    if not isinstance(name, str) or not name:
        raise ValueError(f'{id_}: name is required')
    license_ = raw.get('license')
    if not isinstance(license_, str) or not license_:
        raise ValueError(f'{id_}: license is required')
    is_mapping = 'url' in raw or 'fields' in raw
    is_entry_point = 'entry_point' in raw
    if is_mapping and is_entry_point:
        raise ValueError(f'{id_}: specify either url/fields or entry_point, not both')
    if not is_mapping and not is_entry_point:
        raise ValueError(f'{id_}: specify either url/fields or entry_point')
    if is_entry_point:
        entry_point = raw['entry_point']
        if not isinstance(entry_point, str):
            raise ValueError(f'{id_}: entry_point must be a string')
        func = _load_entry_point(entry_point)
        return Source(id_, name, license_, 'entry_point', entry_point=entry_point, func=func, config=raw)
    url = raw.get('url')
    if not isinstance(url, str) or urlparse(url).scheme not in ('http', 'https'):
        raise ValueError(f'{id_}: url must be an http(s) URL')
    fields = _validate_fields(id_, raw.get('fields'))
    return Source(id_, name, license_, 'mapping', url=url, fields=fields)


class MusicLibrary:
    """Every configured source, with an in-memory, per-source track cache."""

    def __init__(self, sources):
        self.sources = {s.id: s for s in sources}
        self._lock = threading.Lock()
        self._cache = {}  # id -> {'tracks': [...], 'at': monotonic}

    @classmethod
    def from_file(cls, path):
        try:
            with open(path, 'rb') as fh:
                doc = tomllib.load(fh)
        except OSError as exc:
            raise ValueError(f'{path}: {exc}') from None
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f'{path}: {exc}') from None
        raw_sources = doc.get('sources')
        if not isinstance(raw_sources, list):
            raise ValueError(f'{path}: sources must be a list of tables ([[sources]])')
        sources, seen = [], set()
        for i, raw in enumerate(raw_sources):
            try:
                source = _build_source(raw)
            except ValueError as exc:
                raise ValueError(f'{path}: sources[{i}]: {exc}') from None
            if source.id in seen:
                raise ValueError(f'{path}: duplicate source id {source.id!r}')
            seen.add(source.id)
            sources.append(source)
        return cls(sources)

    def list_sources(self):
        return [{'id': s.id, 'name': s.name, 'license': s.license} for s in self.sources.values()]

    def list_tracks(self, source_id):
        """(Source, [track...]) for a configured source id; raises KeyError for an
        unknown one, or FetchError when the fetch fails and there is no cache."""
        source = self.sources.get(source_id)
        if source is None:
            raise KeyError(source_id)
        with self._lock:
            cached = self._cache.get(source_id)
            fresh = cached is not None and time.monotonic() - cached['at'] < CACHE_TTL
        if fresh:
            return source, cached['tracks']
        try:
            tracks = source.fetch_tracks()
        except FetchError:
            if cached is not None:
                return source, cached['tracks']
            raise
        with self._lock:
            self._cache[source_id] = {'tracks': tracks, 'at': time.monotonic()}
        return source, tracks

    def track(self, source_id, track_id):
        """(Source, track|None) for a track id in a configured source's cached list."""
        source, tracks = self.list_tracks(source_id)
        return source, next((t for t in tracks if t['id'] == track_id), None)
