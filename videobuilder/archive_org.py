"""The Internet Archive's free, keyless API (https://archive.org/developers/)
as a footage source: Prelinger, mostly public-domain ephemeral films,
searched and imported into a video's own Sources (see sources.py's
`Sources.import_archive_item`).

Every network call here goes through `_fetch`, which refuses before any
network call unless the URL is https on an archive.org host (`archive.org`
itself, or a subdomain of it: the `ia<n>.us.archive.org`-style mirrors
archive.org's own metadata hands back as download hosts) -- the same
allowlist-first shape as `videobuilder/xpost.py`'s own `_fetch`, and for the
same reason: the query text a creator types is the only thing here that
isn't already fixed by this module's own code, and it never reaches a URL.
`_open` is the single seam every test patches (this sandbox has no network,
and CI must not depend on archive.org being reachable); in production it
also runs `guard.resolve_and_check` on the request's host first as a
fail-fast check, then routes the actual connection -- the initial one and
any redirect's, since a redirect still only ever lands on archive.org or a
mirror of it -- through a lazily-started `guard.GuardProxy`, the same
forward proxy `gather.py` uses, so the address actually connected to is the
one the guard checked, not a second, possibly rebound, resolution of the
same name.

Search results and metadata lookups are cached in memory for CACHE_TTL
seconds, process-wide, the same shape as `music.MusicLibrary`'s own cache.
"""
import json
import re
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode, urlsplit

from . import guard

FETCH_TIMEOUT = 15
SEARCH_MAX_BYTES = 2 * 1024 * 1024
METADATA_MAX_BYTES = 5 * 1024 * 1024
CACHE_TTL = 600
MAX_REDIRECTS = 3
CHUNK = 1 << 16

SEARCH_ROWS = 24
PRELINGER_COLLECTION = 'prelinger'

SEARCH_URL = 'https://archive.org/advancedsearch.php'
METADATA_URL = 'https://archive.org/metadata/{}'
DOWNLOAD_URL = 'https://archive.org/download/{}/{}'
DETAILS_URL = 'https://archive.org/details/{}'
THUMBNAIL_URL = 'https://archive.org/services/img/{}'
USER_AGENT = 'videobuilder-archive-import/1'

_IDENTIFIER_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}')
_FILENAME_RE = re.compile(r'[^/\\]{1,200}')


class ArchiveError(ValueError):
    """A search, metadata or download call to archive.org failed."""


class NotFound(ArchiveError):
    """No such archive.org item (or it has no metadata at all)."""


class TooLarge(ArchiveError):
    """A fetch exceeded its byte cap."""


def _host_ok(host):
    host = (host or '').lower()
    return host == 'archive.org' or host.endswith('.archive.org')


class _AllowlistRedirect(urllib.request.HTTPRedirectHandler):
    """Refuses to follow a redirect that leaves archive.org (scheme must stay
    https too) -- the same shape as xpost.py's own redirect handler."""
    max_redirections = MAX_REDIRECTS

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != 'https' or not _host_ok(parsed.hostname):
            raise urllib.error.HTTPError(newurl, code, 'redirect host not allowed', headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _AlwaysProxy(urllib.request.ProxyHandler):
    """Routes every request through the guard proxy at `proxy_port`
    regardless of a `no_proxy` environment variable -- the same override
    `guard.opener` makes, needed here because we build our own opener
    (to keep `_AllowlistRedirect` alongside it) instead of using that
    function directly."""

    def __init__(self, proxy_port):
        proxy = f'127.0.0.1:{proxy_port}'
        super().__init__({'http': proxy, 'https': proxy})

    def proxy_open(self, req, proxy, type):
        req.set_proxy(proxy, type)


_guard_proxy_lock = threading.Lock()
_guard_proxy = None


def _get_guard_proxy():
    """The process-wide `guard.GuardProxy` every real connection this module
    makes is routed through, started on first use. Its own `_dial` resolves
    a host once and connects to that address -- the single resolution
    `resolve_and_check` promises -- so the host actually connected to for
    any request or redirect this module issues is the one the guard
    checked, never a second, independently-resolved answer for the same
    name."""
    global _guard_proxy
    with _guard_proxy_lock:
        if _guard_proxy is None:
            _guard_proxy = guard.GuardProxy()
        return _guard_proxy


def _open(request, timeout):
    """The single network seam: every test here patches this. Checks the
    request's own host resolves to a public address up front, as a
    fail-fast rejection (see the module docstring), then hands the request
    to an opener that both refuses a redirect leaving archive.org
    (_AllowlistRedirect) and routes the real connection through the guard
    proxy (_get_guard_proxy), so a rebound DNS answer cannot slip in
    between the check above and the connection actually made."""
    parsed = urlsplit(request.full_url)
    try:
        guard.resolve_and_check(parsed.hostname, parsed.port or 443)
    except guard.Refused as exc:
        raise ArchiveError(str(exc)) from None
    proxy = _get_guard_proxy()
    opener = urllib.request.build_opener(_AlwaysProxy(proxy.port), _AllowlistRedirect())
    return opener.open(request, timeout=timeout)


def _fetch(url, max_bytes, timeout=FETCH_TIMEOUT):
    """`url`'s bytes, refusing before any network call if it isn't https on
    an archive.org host; refusing a Content-Length over `max_bytes` before
    the body is read, and the streamed body if it grows past it. The final
    URL (after any redirect) is re-checked too, belt and braces over
    _AllowlistRedirect."""
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not _host_ok(parsed.hostname):
        raise ArchiveError('refusing to fetch from a non-archive.org host')
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        response = _open(request, timeout)
    except (urllib.error.URLError, OSError) as exc:
        raise ArchiveError(f'{url}: {exc}') from None
    try:
        final = urlsplit(response.geturl())
        if final.scheme != 'https' or not _host_ok(final.hostname):
            raise ArchiveError('redirected off archive.org')
        length = response.headers.get('Content-Length')
        if length is not None and int(length) > max_bytes:
            raise TooLarge(f'{url}: response exceeds {max_bytes} bytes')
        data = bytearray()
        while True:
            chunk = response.read(CHUNK)
            if not chunk:
                break
            data += chunk
            if len(data) > max_bytes:
                raise TooLarge(f'{url}: response exceeds {max_bytes} bytes')
        return bytes(data)
    finally:
        close = getattr(response, 'close', None)
        if close:
            close()


CACHE_MAX_ENTRIES = 500


class _Cache:
    """An in-memory, process-wide cache keyed by whatever the caller asks
    for, TTL-expired the same way MusicLibrary's own per-source cache is.
    Unlike MusicLibrary's cache, whose keys are a fixed, configured set of
    source ids, this one is keyed in part by a creator's own search text
    (see search_films), so every insert also drops expired entries and
    caps the live set at CACHE_MAX_ENTRIES (oldest first) rather than
    growing for as long as the process runs."""

    def __init__(self):
        self._lock = threading.Lock()
        self._entries = {}

    def get_or_fetch(self, key, fetch):
        with self._lock:
            cached = self._entries.get(key)
        if cached is not None and time.monotonic() - cached[1] < CACHE_TTL:
            return cached[0]
        result = fetch()
        with self._lock:
            now = time.monotonic()
            self._entries[key] = (result, now)
            self._evict(now)
        return result

    def _evict(self, now):
        for k, (_, at) in list(self._entries.items()):
            if now - at >= CACHE_TTL:
                del self._entries[k]
        over = len(self._entries) - CACHE_MAX_ENTRIES
        if over > 0:
            oldest = sorted(self._entries.items(), key=lambda kv: kv[1][1])[:over]
            for k, _ in oldest:
                del self._entries[k]


_cache = _Cache()


def _coerce_year(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return str(int(value))
    if isinstance(value, str) and re.fullmatch(r'\d{4}', value.strip()):
        return value.strip()
    return None


def _parse_runtime(value):
    """Seconds for archive.org's own 'runtime' field, which shows up as a
    plain number of seconds or as an 'H:MM:SS'/'MM:SS' clock; None for
    anything else (missing, or a format this doesn't recognise)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    value = value.strip()
    if re.fullmatch(r'\d+(\.\d+)?', value):
        return float(value)
    m = re.fullmatch(r'(?:(\d+):)?(\d{1,2}):(\d{1,2}(?:\.\d+)?)', value)
    if not m:
        return None
    hours, minutes, seconds = m.groups()
    return int(hours or 0) * 3600 + int(minutes) * 60 + float(seconds)


def _search(collection, mediatype, query, rows, timeout):
    """Raw advancedsearch result docs for `collection`/`mediatype`, each a
    dict with at least 'identifier' (anything without one, or malformed, is
    dropped). Raises ArchiveError on a fetch or parse failure."""
    q = f'collection:{collection} AND mediatype:{mediatype}'
    if query:
        q += f' AND ({query})'
    params = [('q', q), ('rows', str(rows)), ('page', '1'), ('output', 'json')]
    params += [('fl[]', field) for field in
              ('identifier', 'title', 'creator', 'year', 'licenseurl', 'rights', 'runtime')]
    url = SEARCH_URL + '?' + urlencode(params)
    try:
        data = json.loads(_fetch(url, SEARCH_MAX_BYTES, timeout))
    except ArchiveError:
        raise
    except ValueError as exc:
        raise ArchiveError(f'could not parse archive.org search results: {exc}') from None
    docs = ((data.get('response') or {}).get('docs')) if isinstance(data, dict) else None
    if not isinstance(docs, list):
        return []
    return [d for d in docs if isinstance(d, dict) and isinstance(d.get('identifier'), str)]


def search_films(query='', rows=SEARCH_ROWS, timeout=FETCH_TIMEOUT):
    """Prelinger films (collection `prelinger`, mediatype `movies`) matching
    `query` (an empty query is a default page, not an error): a list of
    {identifier, title, year, duration, license, rights, thumbnail,
    details_url}, as archive.org's own relevance ranking orders them.
    `license`/`rights` are archive.org's own `licenseurl`/`rights` fields,
    either of which may be absent -- Prelinger is mostly, not entirely,
    public domain, and this is the only per-item signal of that. Cached in
    memory per (query, rows) for CACHE_TTL seconds. Raises ArchiveError on a
    fetch or parse failure."""
    key = ('films', query, rows)

    def go():
        out = []
        for doc in _search(PRELINGER_COLLECTION, 'movies', query, rows, timeout):
            identifier = doc['identifier']
            title = doc.get('title')
            out.append({
                'identifier': identifier,
                'title': title if isinstance(title, str) and title else identifier,
                'year': _coerce_year(doc.get('year')),
                'duration': _parse_runtime(doc.get('runtime')),
                'license': doc.get('licenseurl') if isinstance(doc.get('licenseurl'), str) else None,
                'rights': doc.get('rights') if isinstance(doc.get('rights'), str) else None,
                'thumbnail': THUMBNAIL_URL.format(quote(identifier, safe='')),
                'details_url': DETAILS_URL.format(quote(identifier, safe='')),
            })
        return out
    return _cache.get_or_fetch(key, go)


def _coerce_collection(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def get_metadata(identifier, timeout=FETCH_TIMEOUT):
    """Full metadata for one archive.org item: {identifier, title, creator,
    year, license, rights, details_url, collection: [...], mediatype,
    files: [{name, size, ...}...]}. Raises NotFound for an identifier that
    doesn't validate or that archive.org has no metadata for, ArchiveError
    for any other fetch or parse failure. Cached per identifier for
    CACHE_TTL seconds."""
    if not isinstance(identifier, str) or not _IDENTIFIER_RE.fullmatch(identifier):
        raise NotFound('not a valid archive.org item identifier')
    return _cache.get_or_fetch(('metadata', identifier), lambda: _fetch_metadata(identifier, timeout))


def _fetch_metadata(identifier, timeout):
    url = METADATA_URL.format(quote(identifier, safe=''))
    try:
        data = json.loads(_fetch(url, METADATA_MAX_BYTES, timeout))
    except ArchiveError:
        raise
    except ValueError as exc:
        raise ArchiveError(f'{identifier}: could not parse archive.org metadata: {exc}') from None
    if not isinstance(data, dict) or not isinstance(data.get('metadata'), dict) or not data['metadata']:
        raise NotFound(f'{identifier}: no such archive.org item')
    meta = data['metadata']
    creator = meta.get('creator')
    if isinstance(creator, list):
        creator = ', '.join(str(c) for c in creator if isinstance(c, (str, int, float))) or None
    elif not isinstance(creator, str):
        creator = None
    year = _coerce_year(meta.get('year'))
    if year is None:
        date = meta.get('date')
        if isinstance(date, str) and re.match(r'^\d{4}', date):
            year = date[:4]
    title = meta.get('title')
    files = [f for f in (data.get('files') or []) if isinstance(f, dict)]
    return {
        'identifier': identifier,
        'title': title if isinstance(title, str) and title else identifier,
        'creator': creator,
        'year': year,
        'license': meta.get('licenseurl') if isinstance(meta.get('licenseurl'), str) else None,
        'rights': meta.get('rights') if isinstance(meta.get('rights'), str) else None,
        'details_url': DETAILS_URL.format(quote(identifier, safe='')),
        'collection': _coerce_collection(meta.get('collection')),
        'mediatype': meta.get('mediatype') if isinstance(meta.get('mediatype'), str) else None,
        'files': files,
    }


def pick_derivative(files, max_bytes):
    """The largest `.mp4` file in `files` (archive.org's own metadata file
    list) that still fits under `max_bytes`, or None when nothing does --
    archive.org usually offers several encodes of a Prelinger film (a small
    '512Kb MP4' alongside a much larger original), and this prefers quality
    within the budget over always taking the biggest file there is."""
    best = None
    for f in files:
        if not isinstance(f, dict):
            continue
        name = f.get('name')
        if not isinstance(name, str) or not name.lower().endswith('.mp4'):
            continue
        try:
            size = int(f.get('size'))
        except (TypeError, ValueError):
            continue
        if size <= 0 or size > max_bytes:
            continue
        if best is None or size > best[0]:
            best = (size, name)
    return best[1] if best else None


def open_download(identifier, filename, timeout=FETCH_TIMEOUT):
    """Opens (without reading) one file of an archive.org item for
    streaming into a caller's own chunked reader (Sources.import_archive_item
    streams it exactly as it would a browser upload's request body); returns
    (response, content_length, content_type). The caller must close
    `response`. Raises NotFound/ArchiveError without opening anything on a
    bad identifier/filename or an unreported size."""
    if not isinstance(identifier, str) or not _IDENTIFIER_RE.fullmatch(identifier):
        raise NotFound('not a valid archive.org item identifier')
    if not isinstance(filename, str) or not _FILENAME_RE.fullmatch(filename):
        raise ArchiveError('not a valid archive.org file name')
    url = DOWNLOAD_URL.format(quote(identifier, safe=''), quote(filename, safe=''))
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        response = _open(request, timeout)
    except (urllib.error.URLError, OSError) as exc:
        raise ArchiveError(f'{url}: {exc}') from None
    final = urlsplit(response.geturl())
    if final.scheme != 'https' or not _host_ok(final.hostname):
        response.close()
        raise ArchiveError('redirected off archive.org')
    length = response.headers.get('Content-Length')
    try:
        content_length = int(length)
    except (TypeError, ValueError):
        response.close()
        raise ArchiveError('archive.org did not report a usable file size') from None
    return response, content_length, response.headers.get('Content-Type') or 'video/mp4'
