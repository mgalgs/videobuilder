"""Per-video source footage: creator-uploaded clips (and an optional caption
file) that persist until deleted, live outside git, and are exposed to the
builder and to the editor's own previews/renders read-only, at a fixed path
relative to the film's checkout: `sources/<name>.<ext>` (plus
`sources/<name>.vtt`/`.srt` for a caption).

Storage is `<state_dir>/sources/<video-dir>/<name>/`: the video file, an
optional caption, `meta.json`, and (once built) a `preview/` subdirectory
holding a small H.264/AAC copy, named identically to the original, for a
backend that can't share the editor's filesystem and so gets a copy of the
copy instead (see `stage_for_builder`). `sync()` hardlinks the full-quality
set into a checkout (the project's own, or a draft/render worktree) and
removes stale links.

The preview copy is queued from the request thread, right after an upload
passes its probe (`stream_upload` enqueues it and returns without waiting),
and built by a single background worker **per process** (not per `Sources`
instance: a library editor's own process hosts one `Editor`/`Sources` pair
per open project, and they all share this one worker, see `_BUILD_QUEUE`) --
one encode at a time, never one thread per upload. Builds queued this way, or
found pending at startup (see `__init__`), share that same worker and so still
run one at a time: a frame number in the preview means the same source
moment it does in the original (same frame rate, forced constant even for a
variable-rate source -- see `.clip._displayed_size`/`Clip`), short side at
most PREVIEW_MAX_SIDE px, `-preset veryfast`/`crf 28` (this runs in the same
process that serves the creator's own previews, so it stays cheap), stereo
AAC around 96 kbps. `meta['preview_ready']` flips to True once it exists; a
source deleted or an ffmpeg failure just leaves it False forever -- except
that every `Sources.__init__` (so every editor start) re-queues a build for
any source still not ready, which is also when a scratch file left by a
build interrupted mid-encode gets swept up.
"""
import hashlib
import json
import logging
import os
from pathlib import Path, PurePosixPath
import queue
import re
import secrets
import shutil
import subprocess
import threading
import time

from .attachments import TYPES, _validate_content
from .clip import _displayed_size, _fps_and_cfr

EXTS = ('mp4', 'mov', 'webm')
CAPTION_EXTS = ('vtt', 'srt')
STREAM_CHUNK = 1 << 20
CAPTION_MAX_BYTES = 2 * 1048576
PUBLIC_FIELDS = ('name', 'ext', 'size', 'duration', 'width', 'height', 'has_audio', 'caption', 'created',
                 'preview_ready')
SYNC_MANIFEST = '.vb-sync.json'
_NAME_RE = re.compile(r'^[a-z0-9-]{1,80}$')
PREVIEW_MAX_SIDE = 360
PREVIEW_DIRNAME = 'preview'
_log = logging.getLogger(__name__)

# One background worker for the whole process (not one per `Sources` instance:
# a library editor's process opens a separate `Sources` per project, and they
# must still share a single encode slot -- see the module docstring). Jobs are
# (sources, video, name) so the one worker can serve every instance.
_BUILD_QUEUE = queue.Queue()
_build_worker_started = False
_build_worker_lock = threading.Lock()


def _build_worker():
    while True:
        sources, video, name = _BUILD_QUEUE.get()
        try:
            sources._build_preview(video, name)
        except Exception:
            # A build that raises must not take the only worker down with it --
            # every later upload in every open editor would sit at preview_ready
            # False until the process restarts. Log and move on to the next job.
            _log.exception('preview build failed for %r/%r', video, name)
        finally:
            _BUILD_QUEUE.task_done()


def _ensure_build_worker():
    global _build_worker_started
    with _build_worker_lock:
        if not _build_worker_started:
            threading.Thread(target=_build_worker, daemon=True).start()
            _build_worker_started = True


def _preview_dims(width, height):
    """(w, h) for a preview copy -- short side at most PREVIEW_MAX_SIDE, aspect
    kept, both even (yuv420p needs it) -- or None when the source's own
    dimensions aren't known. Never upscales: a source already at or under the
    cap keeps its own size."""
    if not width or not height:
        return None
    if width <= height:
        w = min(width, PREVIEW_MAX_SIDE)
        h = round(height * w / width)
    else:
        h = min(height, PREVIEW_MAX_SIDE)
        w = round(width * h / height)
    return max(w - w % 2, 2), max(h - h % 2, 2)


class TooLarge(ValueError):
    """An upload refused for exceeding a size limit; mapped to HTTP 413."""


def _slug(text):
    slug = re.sub(r'[^a-z0-9-]+', '-', text.strip().lower()).strip('-')
    return slug[:80] or 'source'


def _basename(name):
    return Path(str(name).replace('\\', '/')).name


def probe(path):
    """(duration, width, height, has_audio) of the video at `path` -- width and
    height are the size as displayed, after ffmpeg's own auto-rotation (see
    `.clip._displayed_size`), matching what `vb.Clip` reports for the same
    file. Raises ValueError if ffprobe can't read it, or it has no video
    stream. Entries aren't restricted with `-show_entries` here (beyond
    picking the two top-level sections): ffprobe's entry filter doesn't
    recurse into a nested field like `side_data_list`, so asking for it by
    name back silently returns empty objects instead of the rotation it
    holds."""
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)],
        capture_output=True, text=True)
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
    if video.get('width') and video.get('height'):
        width, height = _displayed_size(video)
    else:
        width, height = video.get('width'), video.get('height')
    return duration, width, height, has_audio


def _source_fps(path):
    """(fps, is_cfr) for `path`'s first video stream -- the same rate and the
    same CFR/VFR distinction `vb.Clip` computes (see `.clip._fps_and_cfr`),
    so a frame number means the same source moment in the preview copy as it
    does in the original, and a constant-rate source's preview is built the
    same unresampled way `Clip` decodes it."""
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
         'stream=avg_frame_rate,r_frame_rate', '-of', 'json', str(path)],
        capture_output=True, text=True, check=True)
    return _fps_and_cfr(json.loads(result.stdout)['streams'][0])


class Sources:
    def __init__(self, editor, max_file, max_total):
        self.editor = editor
        self.max_file = max_file
        self.max_total = max_total
        self.root = Path(editor.state_dir) / 'sources'
        self.root.mkdir(parents=True, exist_ok=True)
        # Scratch space for a preview build in progress (see _build_preview); on the
        # same filesystem as self.root so the finished file can be moved into place
        # with a rename, not a copy. Created up front, not lazily inside the build
        # thread, so its presence under self.root is never a race for a caller that
        # snapshots self.root's own entries (e.g. a traversal test).
        self._tmp_dir = self.root / '.building'
        self._tmp_dir.mkdir(exist_ok=True)
        for stale in self._tmp_dir.iterdir():
            stale.unlink(missing_ok=True)
        self._locks = {}
        self._locks_guard = threading.Lock()
        # One background worker for the whole process, building queued previews
        # one at a time (see the module docstring) rather than a thread per upload.
        _ensure_build_worker()
        # Recovery for a restart mid-encode: a source left with preview_ready False
        # has nothing else polling for it, so without this it would stay that way
        # forever. Scoped to videos the project still knows about -- a source's own
        # directory name is an irreversible hash of its video id (see _video_dir),
        # so this is the only way back to the (video, name) pair `get`/`_build_preview`
        # need.
        for video in self.editor.project.videos():
            for meta in self.list(video.id):
                if not meta.get('preview_ready'):
                    _BUILD_QUEUE.put((self, video.id, meta['name']))

    def _lock(self, video, name):
        """One lock per (video, name), guarding the small read-modify-write
        windows where `delete()`, `add_caption()` and `_build_preview()`'s own
        publish step touch this source's meta.json -- never the length of an
        ffmpeg encode, which `_build_preview` runs unlocked precisely so a
        concurrent `delete()` doesn't wait minutes for it. Without the lock, a
        caption added while a build is publishing could be saved from a copy
        of meta read before the build's own save, clobbering its
        preview_ready=True with a stale False."""
        key = (video, name)
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

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
        # Write-then-rename, not a direct write_text: `_build_preview` reads this
        # same file via `get()` without taking this source's lock (deliberately,
        # so a concurrent delete() isn't blocked for the length of an encode --
        # see `_build_preview`'s own docstring), so a plain write_text's truncate
        # would be visible, briefly, as a zero-byte file to that unlocked read. A
        # rename is atomic on the same filesystem, so no reader ever sees a
        # partial write.
        path = self._meta_path(video, name)
        tmp = path.with_name(f'.{path.name}.{secrets.token_hex(8)}.tmp')
        tmp.write_text(json.dumps(meta))
        tmp.rename(path)

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
                    has_audio=has_audio, caption=None, created=time.time(), preview_ready=False)
        self._save(video, slug, meta)
        self.sync(video)
        _BUILD_QUEUE.put((self, video, slug))
        return self.public(meta)

    def add_caption(self, video, name, filename, data):
        self.get(video, name)  # validates `name` and that the source exists
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
        caption_name = f'{name}.{ext}'
        with self._lock(video, name):
            # Re-read inside the lock: a background preview build (see _build_preview)
            # may be publishing preview_ready=True right now, and saving the meta this
            # method read before taking the lock would clobber that with a stale copy.
            meta = self.get(video, name)
            if meta.get('caption'):
                (d / meta['caption']).unlink(missing_ok=True)
            (d / caption_name).write_bytes(data)
            meta['caption'] = caption_name
            self._save(video, name, meta)
        self.sync(video)
        return self.public(meta)

    def delete(self, video, name):
        self.get(video, name)  # validates `name` and that the source exists
        with self._lock(video, name):
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

    # ---- the builder's sandbox ----

    def _preview_path(self, video, name, meta=None):
        meta = meta or self.get(video, name)
        return self._dir(video, name) / PREVIEW_DIRNAME / f"{meta['name']}.{meta['ext']}"

    def _build_preview(self, video, name):
        """Encode this source's preview copy (see the module docstring) on the
        background build worker, one at a time with every other queued build.
        The encode itself -- minutes, for a large source -- runs without this
        source's lock held, and writes to a scratch file under `_tmp_dir`,
        never into the source's own directory: that's what lets a concurrent
        delete() of this exact source rmtree that directory without racing
        this encode's own file creation inside it (the lock alone isn't
        enough for that -- it only keeps the two from touching meta.json at
        the same instant, not from touching the filesystem at the same
        time). The lock is taken only afterward, briefly, to publish the
        result: get() inside it either sees the source is still there (and
        this publishes to it) or that delete() already won (KeyError, and
        this is a no-op, the finished scratch file discarded). Any failure --
        a bad probe, ffmpeg erroring out, the source vanishing mid-encode --
        just leaves `preview_ready` False; nothing here is fatal to the
        upload that already succeeded (and a later Sources.__init__ queues
        it again)."""
        try:
            meta = self.get(video, name)
        except KeyError:
            return
        dims = _preview_dims(meta.get('width'), meta.get('height'))
        if dims is None:
            return
        width, height = dims
        src = self._dir(video, name) / f"{meta['name']}.{meta['ext']}"
        try:
            fps, cfr = _source_fps(src)
        except (OSError, subprocess.CalledProcessError, IndexError, KeyError, ValueError, ZeroDivisionError):
            return
        tmp = self._tmp_dir / ('.tmp-' + secrets.token_hex(8))
        audio = ['-c:a', 'aac', '-ac', '2', '-b:a', '96k'] if meta.get('has_audio') else ['-an']
        # Forcing the same constant rate Clip reports for the source (even when the
        # source itself is variable-rate) is what keeps a frame number meaning the
        # same moment in the preview as in the original -- see the module docstring.
        # A constant-rate source skips the fps resample, same as Clip._start's own
        # decode and for the same reason (see _fps_and_cfr); round=up otherwise,
        # see the matching comment there.
        vf = f'scale={width}:{height}'
        if not cfr:
            vf += f',fps=fps={fps.numerator}/{fps.denominator}:round=up'
        # -f mp4 forces an MP4 container regardless of the destination name's extension,
        # so a .mov or .webm source still gets an MP4-inside preview copy (see the module
        # docstring) -- ffmpeg would otherwise infer the container from that extension.
        command = ['ffmpeg', '-y', '-i', str(src), '-vf', vf, '-c:v', 'libx264',
                  '-preset', 'veryfast', '-crf', '28',
                  '-pix_fmt', 'yuv420p', *audio, '-movflags', '+faststart', '-f', 'mp4', str(tmp)]
        try:
            result = subprocess.run(command, capture_output=True)
        except OSError:
            result = None
        if result is None or result.returncode or not tmp.is_file():
            tmp.unlink(missing_ok=True)
            return
        with self._lock(video, name):
            try:
                meta = self.get(video, name)
            except KeyError:
                tmp.unlink(missing_ok=True)
                return
            preview_dir = self._dir(video, name) / PREVIEW_DIRNAME
            try:
                preview_dir.mkdir(exist_ok=True)
                tmp.rename(preview_dir / f"{meta['name']}.{meta['ext']}")
            except OSError:
                tmp.unlink(missing_ok=True)
                return
            meta['preview_ready'] = True
            self._save(video, name, meta)

    def stage_for_builder(self, video, dest_dir, budget):
        """Copy this video's ready preview copies (and their captions) into
        `dest_dir/sources/`, real files rather than hardlinks -- the k8s push
        that mounts a note's attachment directory in the builder's pod
        refuses hard-linked files. Added in name order, stopping as soon as
        the next one would push the running total over `budget`; a source
        whose preview isn't ready yet is left out the same way a too-big one
        is. Returns the set of names actually copied, so the caller can tell
        the prompt which ones are "in your sandbox"."""
        added, used = set(), 0
        sources_dir = dest_dir / 'sources'
        for meta in self.list(video):
            if not meta.get('preview_ready'):
                continue
            preview = self._preview_path(video, meta['name'], meta)
            try:
                size = preview.stat().st_size
            except OSError:
                continue
            caption_src = self._dir(video, meta['name']) / meta['caption'] if meta.get('caption') else None
            if caption_src:
                try:
                    size += caption_src.stat().st_size
                except OSError:
                    caption_src = None
            if used + size > budget:
                break
            sources_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(preview, sources_dir / f"{meta['name']}.{meta['ext']}")
            if caption_src:
                shutil.copyfile(caption_src, sources_dir / meta['caption'])
            used += size
            added.add(meta['name'])
        return added
