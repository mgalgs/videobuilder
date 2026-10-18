"""What's new: the project's named releases, shipped in the package, merged
with any notes this instance adds itself, newest first.

Named releases are text files in `videobuilder/release_notes/<id>.md` (see
docs/RELEASES.md): a front-matter block (codename, headline, date, tag, to,
and a video file name per format) and the notes. A release covers everything
since the previous one, so its first version is derived, never stored: the
version after the previous release's `to`. The page shows the ones whose `to`
is no newer than the running version. Their videos are assets of the GitHub
release at `tag`: the server fetches each once into
`<state_dir>/whats-new-cache/<tag>/<file>` and serves it itself, so viewers
never contact GitHub. Until a video is cached, when offline, or with remote
videos turned off, the entry shows its text only.

Local entries are this instance's own, under `<state_dir>/whats-new/`: one
directory per entry, named by its id (the entry's date, `2026-10-18`, then
`2026-10-18-02` for a second one that day), holding `entry.json` ({id,
title, date, versions, notes, created}) and `<format>.mp4` for each video.
Written by the `whats-new` CLI on the server, or by an admin from the What's
new page (videos streamed to disk in bounded chunks with a size cap, like
source uploads). Never in git: the repo is public and the videos are big."""
import datetime
import html
import json
import re
import secrets
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
from importlib import resources
from pathlib import Path

from . import __version__
from .atomic import write_json_atomic

FORMATS = ('9x16', '16x9', '1x1')
DEFAULT_REPO = 'mgalgs/videobuilder'
MAX_VIDEO_BYTES = 300 * 1048576
STREAM_CHUNK = 1 << 20
FETCH_TIMEOUT = 30          # seconds per network read
FETCH_BUDGET = 600          # seconds for a whole video
RETRY_AFTER = 3600          # seconds before trying a failed fetch again
TITLE_MAX, VERSIONS_MAX, NOTES_MAX = 120, 60, 4000
ID = re.compile(r'\d{4}-\d{2}-\d{2}(?:-\d{2})?\Z')
RELEASE_ID = re.compile(r'[a-z][a-z0-9-]{0,40}\Z')
ASSET = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,120}\Z')
VERSION = re.compile(r'\d+(?:\.\d+)*\Z')


class TooLarge(ValueError):
    pass


def _text(value, field, limit, required=True):
    if not isinstance(value, str):
        raise ValueError(f'{field} must be text')
    value = value.strip()
    if required and not value:
        raise ValueError(f'{field} is required')
    if len(value) > limit:
        raise ValueError(f'{field} is longer than {limit} characters')
    if any(ord(c) < 32 and c not in '\n\t' or ord(c) == 127 for c in value):
        raise ValueError(f'{field} has control characters')
    return value


def _date(value):
    if value is None or value == '':
        return datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        return datetime.date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        raise ValueError('date must look like 2026-10-18') from None


def _format(fmt):
    if fmt not in FORMATS:
        raise ValueError('format must be one of ' + ', '.join(FORMATS))
    return fmt


def _looks_like_mp4(first):
    return len(first) >= 12 and first[4:8] == b'ftyp'


def _version(text):
    """(0, 1, 87) for '0.1.87' (or '0.1.87.dev1': only the leading numbers count)."""
    m = re.match(r'\d+(?:\.\d+)*', text)
    return tuple(int(p) for p in m.group().split('.')) if m else ()


def notes_html(text):
    """`text` as HTML: blank-line-separated paragraphs, and runs of lines
    starting with "- " or "* " as a bullet list. Everything else is escaped
    -- no links, no inline markup."""
    out = []
    for block in re.split(r'\n\s*\n', text.replace('\r\n', '\n').strip()):
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        para, items = [], []

        def flush_para():
            if para:
                out.append('<p>' + '<br>'.join(html.escape(p) for p in para) + '</p>')
                para.clear()

        def flush_items():
            if items:
                out.append('<ul>' + ''.join(f'<li>{html.escape(i)}</li>' for i in items) + '</ul>')
                items.clear()

        for line in lines:
            if line[:2] in ('- ', '* '):
                flush_para()
                items.append(line[2:].strip())
            else:
                flush_items()
                para.append(line)
        flush_para()
        flush_items()
    return ''.join(out)


def parse_release(text, release_id):
    """A release notes file as {id, codename, headline, date, tag, to,
    videos: {format: asset file name}, notes}. Raises ValueError if it
    isn't one."""
    if not RELEASE_ID.fullmatch(release_id):
        raise ValueError(f'{release_id}: a release id is lower-case letters, digits and dashes')
    m = re.fullmatch(r'---\n(.*?)\n---\n?(.*)', text.replace('\r\n', '\n'), re.S)
    if not m:
        raise ValueError(f'{release_id}: no front matter between --- lines')
    fields = {}
    for line in m.group(1).split('\n'):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, sep, value = line.partition(':')
        if not sep:
            raise ValueError(f'{release_id}: {line!r} is not "key: value"')
        fields[key.strip()] = value.strip()
    for key in ('codename', 'headline', 'date', 'tag', 'to'):
        if not fields.get(key):
            raise ValueError(f'{release_id}: {key} is missing')
    if not VERSION.fullmatch(fields['to']):
        raise ValueError(f'{release_id}: to must be a version like 0.1.87')
    if not ASSET.fullmatch(fields['tag']):
        raise ValueError(f'{release_id}: tag {fields["tag"]!r} is not a tag name')
    videos = {}
    for fmt in FORMATS:
        name = fields.pop('video-' + fmt, '')
        if name:
            if not ASSET.fullmatch(name) or not name.endswith('.mp4'):
                raise ValueError(f'{release_id}: video-{fmt} must be an .mp4 file name')
            videos[fmt] = name
    unknown = set(fields) - {'codename', 'headline', 'date', 'tag', 'to'}
    if unknown:
        raise ValueError(f'{release_id}: unknown field(s) ' + ', '.join(sorted(unknown)))
    return dict(id=release_id, codename=_text(fields['codename'], 'codename', 40),
                headline=_text(fields['headline'], 'headline', TITLE_MAX), date=_date(fields['date']),
                tag=fields['tag'], to=fields['to'], videos=videos,
                notes=_text(m.group(2), 'notes', NOTES_MAX, required=False))


def load_releases(folder):
    """Every release file in `folder`, oldest first, each with `from`: the
    version after the previous release's `to` (None for the first)."""
    releases = []
    for path in sorted(Path(folder).glob('*.md')) if folder else ():
        try:
            releases.append(parse_release(path.read_text(encoding='utf-8'), path.stem))
        except (OSError, ValueError) as exc:
            # tests/test_whats_new.py holds the bundled files to the format; this
            # only keeps a bad one from taking every library page down with it.
            print(f"[editor] what's new: skipped {path.name}: {exc}", file=sys.stderr, flush=True)
    releases.sort(key=lambda r: _version(r['to']))
    previous = None
    for r in releases:
        if previous:
            parts = list(_version(previous['to']))
            parts[-1] += 1
            r['from'] = '.'.join(map(str, parts))
        else:
            r['from'] = None
        previous = r
    return releases


class _HttpsOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith('https://'):
            raise urllib.error.URLError(f'refused a redirect to {newurl}')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_url(url, dest, max_bytes):
    """Download `url` to `dest` (an MP4 of at most `max_bytes`), within
    FETCH_TIMEOUT per read and FETCH_BUDGET overall; raises on anything
    else, leaving nothing at `dest`."""
    opener = urllib.request.build_opener(_HttpsOnly)
    request = urllib.request.Request(url, headers={'User-Agent': f'videobuilder/{__version__}'})
    deadline = time.monotonic() + FETCH_BUDGET
    tmp = dest.with_name('.fetch-' + secrets.token_hex(8))
    try:
        with opener.open(request, timeout=FETCH_TIMEOUT) as response, open(tmp, 'wb') as fh:
            length = response.headers.get('Content-Length')
            if length and int(length) > max_bytes:
                raise TooLarge(f'{url} is over {max_bytes} bytes')
            written, first = 0, True
            while chunk := response.read(STREAM_CHUNK):
                if first and not _looks_like_mp4(chunk):
                    raise ValueError(f'{url} is not an MP4')
                first = False
                written += len(chunk)
                if written > max_bytes:
                    raise TooLarge(f'{url} is over {max_bytes} bytes')
                if time.monotonic() > deadline:
                    raise TimeoutError(f'{url} took over {FETCH_BUDGET}s')
                fh.write(chunk)
        if first:
            raise ValueError(f'{url} is empty')
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


class WhatsNew:
    def __init__(self, state_dir, max_video_bytes=MAX_VIDEO_BYTES, repo=DEFAULT_REPO, remote_videos=True,
                 releases_dir=None, version=__version__, fetch=fetch_url):
        """`repo`: the GitHub owner/name whose releases hold the videos;
        `remote_videos`: False never fetches them (text only); `fetch(url,
        dest, max_bytes)`: injected by tests, which must not touch the network."""
        self.root = Path(state_dir) / 'whats-new'
        self.cache = Path(state_dir) / 'whats-new-cache'
        self.max_video_bytes = max_video_bytes
        self.repo = repo
        self.remote_videos = remote_videos
        self.releases_dir = (releases_dir if releases_dir is not None
                             else resources.files(__package__).joinpath('release_notes'))
        self.version = version
        self.fetch = fetch
        self._releases = None
        self._lock = threading.Lock()
        self._fetching = {}    # (tag, file) -> Thread
        self._failed = {}      # (tag, file) -> monotonic time of the last failure

    # -- named releases ------------------------------------------------------

    def releases(self):
        """The bundled releases this version has reached, newest first."""
        if self._releases is None:
            self._releases = load_releases(self.releases_dir)
        running = _version(self.version)
        return [r for r in reversed(self._releases) if _version(r['to']) <= running]

    def _cached(self, release, fmt):
        name = release['videos'].get(fmt)
        return self.cache / release['tag'] / name if name else None

    def fetch_missing(self):
        """Start fetching, in the background, each release video not cached
        yet (one try per video at a time, and not again for RETRY_AFTER after
        a failure)."""
        if not self.remote_videos:
            return
        now = time.monotonic()
        with self._lock:
            for r in self.releases():
                for fmt, name in r['videos'].items():
                    key = (r['tag'], name)
                    if (self._cached(r, fmt).is_file() or key in self._fetching or
                            now - self._failed.get(key, -RETRY_AFTER) < RETRY_AFTER):
                        continue
                    thread = threading.Thread(target=self._fetch_one, args=(key,), daemon=True)
                    self._fetching[key] = thread
                    thread.start()

    def _fetch_one(self, key):
        tag, name = key
        url = f'https://github.com/{self.repo}/releases/download/{tag}/{name}'
        try:
            (self.cache / tag).mkdir(parents=True, exist_ok=True)
            self.fetch(url, self.cache / tag / name, self.max_video_bytes)
        except Exception as exc:
            print(f"[editor] what's new: fetching {url}: {exc}", file=sys.stderr, flush=True)
            with self._lock:
                self._failed[key] = time.monotonic()
        finally:
            with self._lock:
                self._fetching.pop(key, None)

    def wait_for_fetches(self, timeout=10):
        """Join the fetches in flight (tests)."""
        with self._lock:
            threads = list(self._fetching.values())
        for t in threads:
            t.join(timeout)

    # -- the merged list -----------------------------------------------------

    def entries(self):
        """Every entry, releases and local ones, newest first, as {id, kind
        ('release' or 'local'), title, headline, date, versions, notes,
        videos (the formats ready to serve), key (orders entries, for the
        app bar's unseen dot)}."""
        out = []
        for r in self.releases():
            versions = f"{r['from']}–{r['to']}" if r['from'] else f"up to {r['to']}"
            videos = ([f for f in FORMATS if f in r['videos'] and self._cached(r, f).is_file()]
                      if self.remote_videos else [])
            out.append(dict(id=r['id'], kind='release', title=r['codename'], headline=r['headline'],
                            date=r['date'], versions=versions, notes=r['notes'], videos=videos))
        for e in self.local():
            out.append(dict(id=e['id'], kind='local', title=e['title'], headline='', date=e['date'],
                            versions=e['versions'], notes=e['notes'], videos=e['videos']))
        for e in out:
            e['key'] = f"{e['date']} {e['id']}"
        out.sort(key=lambda e: e['key'], reverse=True)
        return out

    def newest_key(self):
        """The newest entry's key, or None with no entries (the app bar then has no link)."""
        entries = self.entries()
        return entries[0]['key'] if entries else None

    def video_path(self, entry_id, fmt):
        """The MP4 to serve for `fmt` of an entry, or KeyError."""
        _format(fmt)
        if isinstance(entry_id, str) and RELEASE_ID.fullmatch(entry_id):
            release = next((r for r in self.releases() if r['id'] == entry_id), None)
            path = release and self.remote_videos and self._cached(release, fmt)
        else:
            path = self._dir(entry_id) / f'{fmt}.mp4'
        if not path or not path.is_file():
            raise KeyError(entry_id)
        return path

    # -- local entries -------------------------------------------------------

    def _dir(self, entry_id):
        if not isinstance(entry_id, str) or not ID.fullmatch(entry_id):
            raise KeyError(entry_id)
        return self.root / entry_id

    def _read(self, folder):
        try:
            entry = json.loads((folder / 'entry.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
        # A hand-edited entry.json reaches every library page (via newest_key): skip
        # one that isn't an entry rather than fail them all.
        if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) for k in ('title', 'date')):
            return None
        entry['id'] = folder.name
        entry.setdefault('versions', '')
        entry.setdefault('notes', '')
        entry['videos'] = [f for f in FORMATS if (folder / f'{f}.mp4').is_file()]
        return entry

    def local(self):
        """This instance's own entries, newest first."""
        if not self.root.is_dir():
            return []
        folders = sorted((p for p in self.root.iterdir() if p.is_dir() and ID.fullmatch(p.name)),
                         key=lambda p: p.name, reverse=True)
        return [e for e in (self._read(p) for p in folders) if e]

    def get(self, entry_id):
        entry = self._read(self._dir(entry_id))
        if entry is None:
            raise KeyError(entry_id)
        return entry

    def add(self, title, versions, notes, date=None):
        """A new local entry without videos; returns it. Raises ValueError on a bad field."""
        title = _text(title, 'title', TITLE_MAX)
        versions = _text(versions, 'versions', VERSIONS_MAX, required=False)
        notes = _text(notes, 'notes', NOTES_MAX, required=False)
        date = _date(date)
        self.root.mkdir(parents=True, exist_ok=True)
        for n in range(1, 100):
            entry_id = date if n == 1 else f'{date}-{n:02d}'
            folder = self.root / entry_id
            try:
                folder.mkdir()
            except FileExistsError:
                continue
            entry = dict(id=entry_id, title=title, date=date, versions=versions, notes=notes,
                         created=time.time())
            write_json_atomic(folder / 'entry.json', entry, newline=True, indent=2)
            return {**entry, 'videos': []}
        raise ValueError(f'too many entries on {date}')

    def remove(self, entry_id):
        folder = self._dir(entry_id)
        if not (folder / 'entry.json').is_file():
            raise KeyError(entry_id)
        shutil.rmtree(folder)

    def add_video_file(self, entry_id, fmt, source):
        """Copy the MP4 at `source` in as a local entry's `fmt` video (the CLI)."""
        source = Path(source)
        with open(source, 'rb') as fh:
            return self.stream_video(entry_id, fmt, fh, source.stat().st_size)

    def stream_video(self, entry_id, fmt, rfile, content_length):
        """Stream `content_length` bytes of an MP4 from `rfile` to disk in
        bounded chunks as a local entry's `fmt` video, replacing any it had.
        Raises TooLarge over the cap, ValueError for a bad upload, and leaves
        nothing behind either way."""
        folder = self._dir(entry_id)
        if not (folder / 'entry.json').is_file():
            raise KeyError(entry_id)
        _format(fmt)
        if content_length is None or content_length < 0:
            raise ValueError('a video upload needs a known Content-Length')
        if content_length == 0:
            raise ValueError('the upload is empty')
        if content_length > self.max_video_bytes:
            raise TooLarge(f'videos are limited to {self.max_video_bytes // 1048576} MB')
        tmp = folder / ('.upload-' + secrets.token_hex(8))
        try:
            with open(tmp, 'wb') as fh:
                remaining, first = content_length, b''
                while remaining > 0:
                    chunk = rfile.read(min(STREAM_CHUNK, remaining))
                    if not chunk:
                        raise ValueError('the upload ended early')
                    if not first:
                        first = chunk
                        if not _looks_like_mp4(first):
                            raise ValueError('videos must be MP4 files')
                    fh.write(chunk)
                    remaining -= len(chunk)
            tmp.replace(folder / f'{fmt}.mp4')
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        return self.get(entry_id)
