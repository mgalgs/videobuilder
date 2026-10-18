"""What's new: the instance's release-notes entries, each with up to one video
per format, kept in the state directory (never in git: the repo is public and
the videos are big, and each instance has its own).

Layout, under `<state_dir>/whats-new/`: one directory per entry, named by its
id (the entry's date, `2026-10-18`, then `2026-10-18-02` and so on for a second
one that day), holding `entry.json` ({id, title, date, versions, notes,
created}) and `<format>.mp4` for each video it has (`9x16.mp4`, `16x9.mp4`,
`1x1.mp4`). Ids sort in date order, so the newest entry is the largest id: the
app bar's unseen dot compares it with the one the viewer last opened.

Written by the `whats-new` CLI on the server, or by an admin from the What's
new page (videos streamed to disk in bounded chunks with a size cap, like
source uploads); read by everyone who can use the library."""
import datetime
import html
import json
import re
import secrets
import shutil
import time
from pathlib import Path

from .atomic import write_json_atomic

FORMATS = ('9x16', '16x9', '1x1')
MAX_VIDEO_BYTES = 300 * 1048576
STREAM_CHUNK = 1 << 20
TITLE_MAX, VERSIONS_MAX, NOTES_MAX = 120, 60, 4000
ID = re.compile(r'\d{4}-\d{2}-\d{2}(?:-\d{2})?\Z')


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


class WhatsNew:
    def __init__(self, state_dir, max_video_bytes=MAX_VIDEO_BYTES):
        self.root = Path(state_dir) / 'whats-new'
        self.max_video_bytes = max_video_bytes

    def _dir(self, entry_id):
        if not isinstance(entry_id, str) or not ID.fullmatch(entry_id):
            raise KeyError(entry_id)
        return self.root / entry_id

    def _read(self, folder):
        try:
            entry = json.loads((folder / 'entry.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
        entry['videos'] = [f for f in FORMATS if (folder / f'{f}.mp4').is_file()]
        return entry

    def list(self):
        """Every entry, newest first."""
        if not self.root.is_dir():
            return []
        folders = sorted((p for p in self.root.iterdir() if p.is_dir() and ID.fullmatch(p.name)),
                         key=lambda p: p.name, reverse=True)
        return [e for e in (self._read(p) for p in folders) if e]

    def newest_id(self):
        """The newest entry's id, or None with no entries (the app bar then has no link)."""
        entries = self.list()
        return entries[0]['id'] if entries else None

    def get(self, entry_id):
        entry = self._read(self._dir(entry_id))
        if entry is None:
            raise KeyError(entry_id)
        return entry

    def add(self, title, versions, notes, date=None):
        """A new entry without videos; returns it. Raises ValueError on a bad field."""
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

    def video_path(self, entry_id, fmt):
        """The stored MP4 for `fmt`, or KeyError."""
        path = self._dir(entry_id) / f'{_format(fmt)}.mp4'
        if not path.is_file():
            raise KeyError(entry_id)
        return path

    def add_video_file(self, entry_id, fmt, source):
        """Copy the MP4 at `source` in as the entry's `fmt` video (the CLI)."""
        source = Path(source)
        with open(source, 'rb') as fh:
            return self.stream_video(entry_id, fmt, fh, source.stat().st_size)

    def stream_video(self, entry_id, fmt, rfile, content_length):
        """Stream `content_length` bytes of an MP4 from `rfile` to disk in
        bounded chunks as the entry's `fmt` video, replacing any it had.
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
