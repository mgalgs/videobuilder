"""Per-video source footage: creator-uploaded clips (and an optional caption
file) that persist until deleted, live outside git, and are exposed to the
builder and to the editor's own previews/renders read-only, at a fixed path
relative to the film's checkout: `sources/<name>.<ext>` (plus
`sources/<name>.vtt`/`.srt` for a caption).

Storage is `<state_dir>/sources/<video-dir>/<name>/`: the video file, an
optional caption, and `meta.json`. `sync()` hardlinks the current set into a
checkout (the project's own, or a draft/render worktree) and removes stale
links; `stage_dir()` is the same content, flattened into one reused
directory, for a backend that can't share the editor's filesystem.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import subprocess
import time

from .attachments import TYPES, _validate_content

EXTS = ('mp4', 'mov', 'webm')
CAPTION_EXTS = ('vtt', 'srt')
STREAM_CHUNK = 1 << 20
CAPTION_MAX_BYTES = 2 * 1048576
PUBLIC_FIELDS = ('name', 'ext', 'size', 'duration', 'width', 'height', 'has_audio', 'caption', 'created')
SYNC_MANIFEST = '.vb-sync.json'
_NAME_RE = re.compile(r'^[a-z0-9-]{1,80}$')


class TooLarge(ValueError):
    """An upload refused for exceeding a size limit; mapped to HTTP 413."""


def _slug(text):
    slug = re.sub(r'[^a-z0-9-]+', '-', text.strip().lower()).strip('-')
    return slug[:80] or 'source'


def _basename(name):
    return Path(str(name).replace('\\', '/')).name


def probe(path):
    """(duration, width, height, has_audio) of the video at `path`; raises
    ValueError if ffprobe can't read it, or it has no video stream."""
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height:format=duration',
         '-of', 'json', str(path)], capture_output=True, text=True)
    if result.returncode:
        raise ValueError('could not read this video file')
    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise ValueError('could not read this video file') from None
    streams = data.get('streams') or []
    video = next((s for s in streams if s.get('codec_type') == 'video'), None)
    if video is None:
        raise ValueError('this file has no video stream')
    has_audio = any(s.get('codec_type') == 'audio' for s in streams)
    try:
        duration = float((data.get('format') or {}).get('duration') or 0)
    except (TypeError, ValueError):
        duration = 0.0
    return duration, video.get('width'), video.get('height'), has_audio


class Sources:
    def __init__(self, editor, max_file, max_total):
        self.editor = editor
        self.max_file = max_file
        self.max_total = max_total
        self.root = Path(editor.state_dir) / 'sources'
        self.root.mkdir(parents=True, exist_ok=True)

    def _exclude_checkout(self, rel_dir):
        """Ignore this one video's `sources/` directory in the project's own git
        checkout via `.git/info/exclude`, without touching tracked files or the
        repo's own .gitignore. The entry is anchored to this video's own directory
        (`/<rel_dir>/sources/`), not a bare `sources/`, so it can't also match an
        unrelated `sources/` directory the creator has elsewhere in the repo. A
        no-op outside a git repo, or if the pattern is already there (also covers
        any worktree, since `info/exclude` is shared repo-wide)."""
        if not self.editor.project.git:
            return
        pattern = '/' + PurePosixPath(rel_dir).as_posix() + '/sources/'
        try:
            info_dir = Path(subprocess.run(
                ['git', 'rev-parse', '--git-common-dir'], cwd=self.editor.root,
                capture_output=True, text=True, check=True).stdout.strip())
            if not info_dir.is_absolute():
                info_dir = Path(self.editor.root) / info_dir
            info_dir = info_dir / 'info'
            info_dir.mkdir(parents=True, exist_ok=True)
            exclude = info_dir / 'exclude'
            existing = exclude.read_text() if exclude.exists() else ''
            if pattern not in existing.splitlines():
                with open(exclude, 'a') as fh:
                    if existing and not existing.endswith('\n'):
                        fh.write('\n')
                    fh.write(pattern + '\n')
        except (OSError, subprocess.CalledProcessError):
            pass

    # ---- storage ----

    def _video_dir(self, video):
        slug = re.sub(r'[^A-Za-z0-9]+', '-', video).strip('-')[:96]
        return self.root / (slug + '-' + hashlib.sha256(video.encode()).hexdigest()[:12])

    def _dir(self, video, name):
        return self._video_dir(video) / name

    def _meta_path(self, video, name):
        return self._dir(video, name) / 'meta.json'

    def _save(self, video, name, meta):
        path = self._meta_path(video, name)
        path.write_text(json.dumps(meta))

    def list(self, video):
        d = self._video_dir(video)
        if not d.is_dir():
            return []
        out = []
        for meta_path in sorted(d.glob('*/meta.json')):
            try:
                out.append(json.loads(meta_path.read_text()))
            except (OSError, ValueError):
                continue
        return out

    def get(self, video, name):
        # `name` reaches here raw from a URL path segment (see video_api.py / handler_library.py):
        # every other method below funnels through get(), so this is the one place a traversal
        # name like '..' or '.' -- which `[^/]+` lets through the route regex unchanged -- is
        # rejected, rather than resolving to a directory this code does not own.
        if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
            raise KeyError(name)
        try:
            return json.loads(self._meta_path(video, name).read_text())
        except FileNotFoundError:
            raise KeyError(name) from None

    def _total_bytes(self, video):
        return sum(m['size'] for m in self.list(video))

    @staticmethod
    def public(meta):
        return {k: meta.get(k) for k in PUBLIC_FIELDS}

    def file_path(self, video, name):
        meta = self.get(video, name)
        return meta, self._dir(video, name) / f"{meta['name']}.{meta['ext']}"

    # ---- upload ----

    def stream_upload(self, video, filename, name, content_type, rfile, content_length):
        """Stream `content_length` bytes of a new source video from `rfile`
        to disk in bounded chunks, enforcing the per-file and per-video
        total limits as bytes arrive. Raises `TooLarge` (over a limit) or
        `ValueError` (bad type, name clash, unreadable video) and leaves
        nothing on disk either way."""
        self.editor.project.video(video)
        if content_length is None or content_length < 0:
            raise ValueError('a source upload needs a known Content-Length')
        if content_length == 0:
            raise ValueError('the upload is empty')
        ext = Path(_basename(filename)).suffix.lstrip('.').lower()
        if ext not in EXTS:
            raise ValueError('source videos must be .mp4, .mov or .webm')
        base = _basename(filename).rsplit('.', 1)[0]
        slug = _slug(name) if name else _slug(base)
        video_dir = self._video_dir(video)
        dest = video_dir / slug
        if dest.exists():
            raise ValueError(f'a source named {slug!r} already exists for this video')
        existing_total = self._total_bytes(video)
        if existing_total >= self.max_total:
            raise TooLarge('this video has reached its total limit for source videos')
        budget = min(self.max_file, self.max_total - existing_total)
        video_dir.mkdir(parents=True, exist_ok=True)
        tmp = video_dir / ('.upload-' + secrets.token_hex(8))
        written = 0
        first_chunk = b''
        try:
            with open(tmp, 'wb') as fh:
                remaining = content_length
                while remaining > 0:
                    chunk = rfile.read(min(STREAM_CHUNK, remaining))
                    if not chunk:
                        raise ValueError('the upload ended early')
                    if not first_chunk:
                        first_chunk = chunk
                    written += len(chunk)
                    if written > budget:
                        if budget == self.max_file:
                            raise TooLarge('this source video exceeds the file size limit')
                        raise TooLarge('this video has reached its total limit for source videos')
                    fh.write(chunk)
                    remaining -= len(chunk)
            _validate_content(content_type, first_chunk, ext)
            duration, width, height, has_audio = probe(tmp)
            try:
                dest.mkdir()
            except FileExistsError:
                raise ValueError(f'a source named {slug!r} already exists for this video') from None
            final = dest / f'{slug}.{ext}'
            tmp.rename(final)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        meta = dict(name=slug, ext=ext, size=written, duration=duration, width=width, height=height,
                    has_audio=has_audio, caption=None, created=time.time())
        self._save(video, slug, meta)
        self.sync(video)
        return self.public(meta)

    def add_caption(self, video, name, filename, data):
        meta = self.get(video, name)
        ext = _basename(filename).rsplit('.', 1)[-1].lower() if '.' in _basename(filename) else ''
        if ext not in CAPTION_EXTS:
            raise ValueError('caption files must be .vtt or .srt')
        if len(data) > CAPTION_MAX_BYTES:
            raise ValueError('caption file is too large')
        try:
            data.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError('caption file must be UTF-8') from None
        d = self._dir(video, name)
        if meta.get('caption'):
            (d / meta['caption']).unlink(missing_ok=True)
        caption_name = f'{name}.{ext}'
        (d / caption_name).write_bytes(data)
        meta['caption'] = caption_name
        self._save(video, name, meta)
        self.sync(video)
        return self.public(meta)

    def delete(self, video, name):
        self.get(video, name)  # validates `name` and that the source exists
        shutil.rmtree(self._dir(video, name))
        self.sync(video)

    # ---- staging ----

    def sync(self, video, root=None):
        """Hardlink this video's current sources (and captions) into
        `<root>/<video-dir>/sources/`, removing anything stale; `root`
        defaults to the project's own checkout -- a directory this code
        does not otherwise own, and may already hold content of the
        creator's own that happens to be named `sources/`. So the only
        entries ever removed are ones a previous sync() itself put there,
        tracked in a small manifest file alongside them; anything else in
        that directory, including a pre-existing subdirectory, is left
        alone. Reused across calls: a source already linked in costs only
        a stat."""
        try:
            video_path = Path(self.editor.project.video(video).path)
        except KeyError:
            return
        try:
            rel_dir = video_path.parent.relative_to(self.editor.root)
        except ValueError:
            return
        self._exclude_checkout(rel_dir)
        dest_dir = (Path(root) if root is not None else Path(self.editor.root)) / rel_dir / 'sources'
        wanted = {}
        for meta in self.list(video):
            src_dir = self._dir(video, meta['name'])
            wanted[f"{meta['name']}.{meta['ext']}"] = src_dir / f"{meta['name']}.{meta['ext']}"
            if meta.get('caption'):
                wanted[meta['caption']] = src_dir / meta['caption']
        manifest = dest_dir / SYNC_MANIFEST
        try:
            managed = set(json.loads(manifest.read_text()))
        except (OSError, ValueError):
            managed = set()
        for stale in managed - set(wanted):
            path = dest_dir / stale
            if path.is_file():
                path.unlink(missing_ok=True)
        if not wanted:
            manifest.unlink(missing_ok=True)
            try:
                dest_dir.rmdir()  # only succeeds if nothing but our own links was left in it
            except OSError:
                pass
            return
        dest_dir.mkdir(parents=True, exist_ok=True)
        for rel_name, src in wanted.items():
            dst = dest_dir / rel_name
            if dst.is_file():
                if dst.stat().st_ino == src.stat().st_ino and dst.stat().st_dev == src.stat().st_dev:
                    continue
                dst.unlink()
            elif dst.exists():
                continue  # something not ours is sitting at this name; don't clobber it
            try:
                os.link(src, dst)
            except OSError:
                shutil.copyfile(src, dst)
        manifest.write_text(json.dumps(sorted(wanted)))

    def stage_dir(self, video):
        """A persistent, reused directory holding this video's current
        sources (and captions) hardlinked flat as `<name>.<ext>`, for a
        backend that forks the project elsewhere and can't rely on the
        editor's own checkout to carry them along. None with no sources."""
        metas = self.list(video)
        if not metas:
            return None
        stage = self.root / '.stage' / self._video_dir(video).name
        wanted = {}
        for meta in metas:
            src_dir = self._dir(video, meta['name'])
            wanted[f"{meta['name']}.{meta['ext']}"] = src_dir / f"{meta['name']}.{meta['ext']}"
            if meta.get('caption'):
                wanted[meta['caption']] = src_dir / meta['caption']
        stage.mkdir(parents=True, exist_ok=True)
        for existing in list(stage.iterdir()):
            if existing.name not in wanted:
                existing.unlink()
        for rel_name, src in wanted.items():
            dst = stage / rel_name
            if dst.exists():
                if dst.stat().st_ino == src.stat().st_ino and dst.stat().st_dev == src.stat().st_dev:
                    continue
                dst.unlink()
            try:
                os.link(src, dst)
            except OSError:
                shutil.copyfile(src, dst)
        return str(stage)
