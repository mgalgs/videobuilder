"""Generated pictures for a video: the director's Pictures panel asks an image
service ("artbox", configured with `--artbox-url`) to make pictures from a
prompt, optionally with the background cut out, and the creator adds any of
them to the note they are writing as an ordinary attachment.

The artbox API is batch: POST /api/images starts a job, GET /api/jobs/<id>
reports it (queued/running/done/failed), GET /files/<id>/<name> returns a PNG,
GET /api/gpu says whether its shared GPU is free. A job can sit queued for
hours, so each video's jobs are kept in the editor's state dir and polled in
the background (Pictures.tick), surviving a restart; a finished job's PNGs are
copied into a per-video store beside them. A stored picture is not an
attachment (those expire) until the creator adds it to a note.

Layout, under `<state_dir>/pictures/`: one directory per video (named like
sources.py's, a slug plus a hash), holding `jobs.json` ({video, jobs: [...]})
and one directory per finished job with `<i>.png`, `<i>.thumb.webp` and, for a
cut-out, `<i>-cutout.png` / `<i>-cutout.thumb.webp`.

Another pose (Pictures.pose) is a job like any other, asked of artbox with a
finished picture as its reference: artbox redraws the same character (its
"KI", keep-identity, mode) from that picture's seed, in the pose the creator
describes. More like this (Pictures.vary) asks for two more in the same
spirit: the picture is only an inspiration ("I" mode) and no seed is sent, so
they differ. Either reference is built here from the stored job, never taken
from the client.

An edit (Pictures.edit: flip, rotate, crop) is done here with Pillow, at once
and at no cost, and makes a new single-picture set beside the original, which
is kept; for a cut-out, the cut-out and the original are edited alike. An
edited picture has no artbox file of its own, so a pose or more like it is
drawn from the picture it was edited from, and says so.

Network safety: the editor only talks to the configured base URL. Every file
URL is built from the base, a job id and a url-quoted name taken from the job
JSON, each checked against a strict pattern first; nothing in a response is
ever followed as a URL, redirects are refused, and every read has a timeout
and a byte cap.
"""
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlsplit

from .atomic import write_json_atomic

SIZE = '1024x1024'
TAG = 'videobuilder'
MAX_PROMPT = 1000
MAX_COUNT = 4
MAX_PENDING = 2
MAX_POSE = 300
POSE_COUNT = 2
LIKE_COUNT = 2
# Edited pictures cost nothing to make, so they skip the daily cap; past this
# many in one video, making another drops the oldest.
MAX_EDITS = 40
DEFAULT_DAILY_CAP = 40
# artbox gives a job up after 12 hours; past that it will never finish.
GIVE_UP_SECONDS = 12 * 3600
DAY_SECONDS = 24 * 3600
# Seconds between polls of one job, by how many polls it has had; the last repeats.
POLL_DELAYS = (5, 10, 15, 20, 30)
FETCH_ATTEMPTS = 5
API_TIMEOUT = 10
FILE_TIMEOUT = 30
JSON_MAX_BYTES = 1 << 20
FILE_MAX_BYTES = 20 << 20
MAX_SIDE = 4096
THUMB_SIDE = 512
VIDEO_MAX_BYTES = 500 << 20
GPU_CACHE_SECONDS = 10
# Cut-outs lose faint white parts (steam, glass, white fur) against white.
CUTOUT_SUFFIX = ', on a plain mid-grey background'
# The same prompt gets the same names back, so trying again can't help.
CANT_USE = "These pictures came back in a form this editor can't use. Try describing them differently."

JOB_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}')
# Names carry the prompt's words, punctuation and all, and are url-quoted with
# safe='' before use, so only path separators, control characters, a leading
# '.' and '..' (checked in valid_file_name) are refused. The length allows a
# whole MAX_PROMPT prompt plus the suffix and artbox's timestamp and seed.
FILE_NAME = re.compile(r'[^\x00-\x1f\x7f/\\.][^\x00-\x1f\x7f/\\]{0,2043}\.png')
SEED_IN_NAME = re.compile(r'_seed(\d{1,19})_')
LOCAL_ID = re.compile(r'[0-9a-f]{16}')
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'

PENDING = ('waiting', 'making')


class ArtboxError(Exception):
    """The picture service could not be reached, or answered with something unusable.
    `status` is its HTTP status, when it answered at all."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class PictureError(ValueError):
    """A request the creator should see refused, with `code` and a plain message."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def valid_job_id(value):
    return isinstance(value, str) and bool(JOB_ID.fullmatch(value))


def valid_file_name(value):
    return isinstance(value, str) and bool(FILE_NAME.fullmatch(value)) and '..' not in value


def check_base_url(url):
    """The artbox base URL, without a trailing slash; ValueError unless it is
    a plain http(s) URL with a host and no credentials, query or fragment."""
    if not isinstance(url, str):
        raise ValueError('--artbox-url must be a URL')
    parts = urlsplit(url.strip())
    if (parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment):
        raise ValueError('--artbox-url must be a plain http(s) URL, like http://artbox.local:8000')
    return url.strip().rstrip('/')


class Artbox:
    """A client for one artbox base URL. Every request goes to that base."""

    def __init__(self, base):
        self.base = check_base_url(base)
        self._opener = urllib.request.build_opener(_NoRedirect)
        self._gpu = (0.0, 'unknown')
        self._gpu_lock = threading.Lock()

    def _request(self, path, body=None, max_bytes=JSON_MAX_BYTES, timeout=API_TIMEOUT):
        headers = {'User-Agent': 'videobuilder-pictures/1'}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(self.base + path, data=data, headers=headers,
                                         method='POST' if body is not None else 'GET')
        try:
            with self._opener.open(request, timeout=timeout) as response:
                payload = response.read(max_bytes + 1)
        except urllib.error.HTTPError as exc:
            exc.close()
            raise ArtboxError(f'HTTP {exc.code} from {path}', exc.code) from None
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise ArtboxError(f'{path}: {exc}') from None
        if len(payload) > max_bytes:
            raise ArtboxError(f'{path}: response over {max_bytes} bytes')
        return payload

    def _json(self, path, body=None):
        try:
            data = json.loads(self._request(path, body))
        except ValueError:
            raise ArtboxError(f'{path}: not JSON') from None
        if not isinstance(data, dict):
            raise ArtboxError(f'{path}: not a JSON object')
        return data

    def submit(self, prompt, n, matte, refs=None, seed=None, ref_mode='KI'):
        """Start a job; with `refs` (["<jobId>/<fileName>"]) artbox draws from
        them, keeping the identity of the character in them ("KI") or only
        taking them as inspiration ("I"), and `seed` repeats a picture's seed."""
        body = {'prompt': prompt, 'n': n, 'size': SIZE, 'tag': TAG, 'matte': bool(matte)}
        if refs:
            body.update(refs=list(refs), refMode=ref_mode)
        if seed is not None:
            body['seed'] = seed
        job = self._json('/api/images', body)
        if not valid_job_id(job.get('id')):
            raise ArtboxError('the new job has no usable id')
        return job

    def job(self, job_id):
        if not valid_job_id(job_id):
            raise ArtboxError('bad job id')
        return self._json('/api/jobs/' + job_id)

    def file(self, job_id, name):
        if not valid_job_id(job_id) or not valid_file_name(name):
            raise ArtboxError('bad file name')
        return self._request(f'/files/{job_id}/{quote(name, safe="")}', max_bytes=FILE_MAX_BYTES,
                             timeout=FILE_TIMEOUT)

    def gpu(self):
        """'free', 'busy' or 'unknown', cached briefly: every open Pictures panel asks."""
        with self._gpu_lock:
            at, value = self._gpu
            if time.monotonic() - at < GPU_CACHE_SECONDS:
                return value
        try:
            value = _gpu_state(self._json('/api/gpu'))
        except ArtboxError:
            value = 'unknown'
        with self._gpu_lock:
            self._gpu = (time.monotonic(), value)
        return value


def _gpu_state(data):
    """artbox's /api/gpu shape is not pinned down; read it loosely."""
    for key in ('free', 'available', 'idle'):
        if isinstance(data.get(key), bool):
            return 'free' if data[key] else 'busy'
    if isinstance(data.get('busy'), bool):
        return 'busy' if data['busy'] else 'free'
    for key in ('state', 'status', 'gpu'):
        value = data.get(key)
        if isinstance(value, str):
            value = value.lower()
            if value in ('free', 'idle', 'available', 'ready'):
                return 'free'
            if value in ('busy', 'running', 'working', 'queued'):
                return 'busy'
    for key in ('queue', 'queued', 'pending'):
        value = data.get(key)
        if isinstance(value, list):
            value = len(value)
        if isinstance(value, int) and not isinstance(value, bool):
            return 'busy' if value > 0 else 'free'
    return 'unknown'


def _video_dir_name(video):
    slug = re.sub(r'[^A-Za-z0-9]+', '-', video).strip('-')[:96]
    return slug + '-' + hashlib.sha256(video.encode()).hexdigest()[:12]


def _read_jobs(path):
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get('jobs'), list) else None


def has_pending(root):
    """Whether any video under the pictures dir `root` has a job still waiting,
    read straight off disk (Library.tick_pictures, without opening an Editor)."""
    for path in Path(root).glob('*/jobs.json'):
        data = _read_jobs(path)
        if data and any(j.get('status') in PENDING for j in data['jobs']):
            return True
    return False


def submissions(root):
    """(author, time, count) for every time a set of pictures was asked for,
    across every video under the pictures dir `root` -- the daily cap's input."""
    for path in Path(root).glob('*/jobs.json'):
        data = _read_jobs(path)
        for job in (data or {}).get('jobs', []):
            for at in job.get('submitted', []):
                yield job.get('author'), at, job.get('n', 0)


def _plain_count(n):
    return '1 picture' if n == 1 else f'{n} pictures'


# Where a picture's subject stops and what it is doing begins: "a fox standing
# on a rock" is about "fox". Words ending in -ing count too, after the first,
# unless they are one of the common nouns that only look like a verb.
_SUBJECT_STOP = {'on', 'in', 'at', 'against', 'over', 'under', 'near', 'by', 'from', 'into', 'onto',
                 'towards', 'toward', 'beside', 'behind', 'above', 'below', 'and', 'that', 'who', 'which'}
_ING_NOUNS = {'viking', 'duckling', 'gosling', 'hatchling', 'fledgling', 'starling', 'halfling', 'earthling',
              'sapling', 'seedling', 'dumpling', 'pudding', 'darling', 'sibling', 'offspring', 'painting',
              'drawing', 'building', 'earring', 'clothing', 'ceiling', 'wedding', 'evening', 'morning'}
_ARTICLE = {'a', 'an', 'the', 'one', 'some'}
_SIDEWAYS = re.compile(r'\b(?:to|towards|toward)\s+the\s+(left|right)\b(?!\s+(?:edge|side|of))',
                       re.IGNORECASE)


def _subject(prompt):
    """The thing a prompt draws, as best a few rules can tell: its first
    clause, without a leading article, cut where a place or action starts."""
    clause = re.split(r'[,;.:!?\n]| - ', prompt, maxsplit=1)[0]
    words = clause.split()
    if words and words[0].lower() in _ARTICLE:
        words = words[1:]
    out = []
    for word in words:
        bare = word.lower().strip('"\'()')
        if out and (bare in _SUBJECT_STOP or (bare.endswith('ing') and len(bare) > 4 and bare not in _ING_NOUNS)):
            break
        out.append(word)
        if len(out) == 8:
            break
    return ' '.join(out) or 'character'


def _style(prompt):
    """The base prompt, standing in for its style, without any clause about
    a background: the pose is always drawn on mid-grey."""
    clauses = [c.strip() for c in re.split(r'[,;]', prompt)]
    kept = [c for c in clauses if c and 'background' not in c.lower()]
    return ', '.join(kept).rstrip(' .') or 'the same style'


def pose_prompt(base_prompt, pose):
    """artbox's prompt for another pose of a picture made from `base_prompt`.
    A direction said about the character ("pointing to the left") is put
    about the picture instead, which is what artbox follows. The character's
    own side ("to his left") is left as said: facing the viewer, that is the
    image's other side, so rewriting it would mirror the pose."""
    pose = _SIDEWAYS.sub(lambda m: f'towards the {m.group(1).lower()} edge of the image', pose.strip().rstrip('.'))
    return (f'the same {_subject(base_prompt)} from image 1, now {pose}. '
            'Keep the same face, colours, proportions and outline weight. '
            f'{_style(base_prompt)}{CUTOUT_SUFFIX}')


def _slug(prompt):
    words = re.findall(r'[A-Za-z0-9]+', prompt.lower())
    out = ''
    for word in words:
        if len(out) + len(word) + 1 > 40:
            break
        out = f'{out}-{word}' if out else word
    return out or 'picture'


class Pictures:
    """One project's generated pictures: every video's jobs and stored files."""

    def __init__(self, editor, artbox, daily_cap=DEFAULT_DAILY_CAP, video_max_bytes=VIDEO_MAX_BYTES):
        self.editor = editor
        self.artbox = artbox
        self.daily_cap = daily_cap
        self.video_max_bytes = video_max_bytes
        self.root = Path(editor.state_dir) / 'pictures'
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._ticking = threading.Lock()

    # ---- storage ----

    def _dir(self, video):
        return self.root / _video_dir_name(video)

    def _load(self, video):
        data = _read_jobs(self._dir(video) / 'jobs.json')
        return data['jobs'] if data and data.get('video') == video else []

    def _save(self, video, jobs):
        path = self._dir(video)
        path.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path / 'jobs.json', {'video': video, 'jobs': jobs}, indent=1)

    def _videos(self):
        for path in self.root.glob('*/jobs.json'):
            data = _read_jobs(path)
            if data and isinstance(data.get('video'), str) and path.parent.name == _video_dir_name(data['video']):
                yield data['video']

    def _find(self, jobs, job_id):
        for job in jobs:
            if job['id'] == job_id:
                return job
        raise PictureError(404, 'Those pictures are gone.')

    # ---- what the director sees ----

    def public(self, job):
        pending_for = time.time() - job['submitted'][-1] if job['status'] in PENDING else 0
        out = {'id': job['id'], 'prompt': job['prompt'], 'n': job['n'], 'cutout': job['cutout'],
               'status': job['status'], 'message': job.get('message'), 'created': job['created'],
               'retryable': job.get('retryable', True),
               'waited': round(pending_for),
               'pictures': [{'index': p['index'], 'cutout': p['cutout'], 'posable': bool(_ref(job, p))}
                            for p in job.get('pictures', [])]}
        for key, name in (('pose_of', 'poseOf'), ('like_of', 'likeOf'), ('edit_of', 'editOf')):
            source = job.get(key)
            if source:
                out[name] = {'id': source['job'], 'index': source['index'], 'prompt': source['prompt'],
                             'cutout': source['cutout']}
                if source.get('edited'):
                    out[name]['edited'] = True
                if key == 'edit_of':
                    out[name].update(edit=source['edit'], label=source['label'])
        return out

    def list(self, video):
        with self.lock:
            jobs = self._load(video)
        return [self.public(j) for j in sorted(jobs, key=lambda j: j['created'], reverse=True)]

    def gpu(self):
        return self.artbox.gpu()

    # ---- limits ----

    def check_daily_cap(self, author, is_admin, count):
        """Refuse, like the note cap, once `author`'s account has asked for
        `daily_cap` pictures over the trailing 24 hours, across every video
        (and, in a library, every project). Never for an admin account, nor
        for one whose own limit (Accounts.get_limit) is "unlimited"; a
        "custom" limit names no picture count, so the flat cap applies."""
        from .editor import _account_key, _plain_local_time
        if is_admin or self.daily_cap is None:
            return
        library = self.editor.library
        has_accounts = bool(library and library.accounts)
        account = _account_key(author, has_accounts)
        limit = library.accounts.get_limit(account) if has_accounts else None
        if limit and limit['kind'] == 'unlimited':
            return
        roots = library.picture_dirs() if library else [self.root]
        cutoff = time.time() - DAY_SECONDS
        mine = sorted((at, n) for root in roots for who, at, n in submissions(root)
                      if at >= cutoff and _account_key(who, has_accounts) == account)
        used = sum(n for _, n in mine)
        if used + count <= self.daily_cap:
            return
        left = self.daily_cap - used
        if left > 0:
            raise PictureError(429, f'You have {_plain_count(left)} left for today. Ask for fewer.')
        when = _plain_local_time(mine[0][0] + DAY_SECONDS) if mine else 'tomorrow'
        raise PictureError(429, f"You've reached today's limit of {self.daily_cap} pictures. "
                                f'You can make more after {when}.')

    def _check_pending(self, jobs):
        if sum(j['status'] in PENDING for j in jobs) >= MAX_PENDING:
            raise PictureError(429, 'Two sets of pictures are already on the way. '
                                    'Wait for one to finish, then make more.')

    # ---- starting and retrying ----

    def _submit(self, job):
        pose, like = job.get('pose_of'), job.get('like_of')
        try:
            if pose:
                remote = self.artbox.submit(pose['ask'], job['n'], job['cutout'], refs=[pose['ref']],
                                            seed=pose['seed'])
            elif like:
                remote = self.artbox.submit(like['ask'], job['n'], job['cutout'], refs=[like['ref']],
                                            ref_mode='I')
            else:
                remote = self.artbox.submit(job['prompt'] + (CUTOUT_SUFFIX if job['cutout'] else ''), job['n'],
                                            job['cutout'])
        except ArtboxError as exc:
            print(f'[editor] pictures: start failed: {exc}', file=sys.stderr, flush=True)
            raise PictureError(502, "The picture maker isn't answering right now. Try again in a moment.") from None
        now = time.time()
        job.update(remote=remote['id'], status='making' if remote.get('state') == 'running' else 'waiting',
                   message=None, polls=0, fetch_failures=0, next_poll=now + POLL_DELAYS[0], pictures=[])
        job.setdefault('submitted', []).append(now)

    def start(self, video, prompt, n, cutout, author, is_admin=False):
        if not isinstance(prompt, str) or not prompt.strip():
            raise PictureError(400, 'Describe the picture first.')
        prompt = prompt.strip()
        if len(prompt) > MAX_PROMPT:
            raise PictureError(400, f'That description is too long. Keep it under {MAX_PROMPT:,} characters.')
        if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= MAX_COUNT:
            raise PictureError(400, f'Choose from 1 to {MAX_COUNT} pictures.')
        if not isinstance(cutout, bool):
            raise PictureError(400, 'cutout must be true or false')
        self.editor.project.video(video)
        with self.lock:
            jobs = self._load(video)
            self._check_pending(jobs)
            self.check_daily_cap(author, is_admin, n)
            job = {'id': secrets.token_hex(8), 'video': video, 'prompt': prompt, 'n': n, 'cutout': cutout,
                   'author': author, 'created': time.time()}
            self._submit(job)
            jobs.append(job)
            self._save(video, jobs)
        return self.public(job)

    def pose(self, video, job_id, index, pose, author, is_admin=False):
        """Start another pose of picture `index` of the finished set `job_id`:
        two pictures of the same character, cut out if the set was."""
        if not isinstance(pose, str) or not pose.strip():
            raise PictureError(400, 'Say what the new pose is first.')
        pose = ' '.join(pose.split())
        if len(pose) > MAX_POSE:
            raise PictureError(400, f'That pose is too long. Keep it under {MAX_POSE} characters.')
        return self._derive(video, job_id, index, author, is_admin, 'pose_of', POSE_COUNT, pose,
                            "This picture is too old to make another pose of. Make it again first.")

    def vary(self, video, job_id, index, author, is_admin=False):
        """Start a set of two more like picture `index` of the finished set
        `job_id`: its words, the picture as a loose reference and no seed, so
        they differ; cut out if the set was."""
        return self._derive(video, job_id, index, author, is_admin, 'like_of', LIKE_COUNT, None,
                            "This picture is too old to make more like it. Make it again first.")

    def _derive(self, video, job_id, index, author, is_admin, kind, n, pose, too_old):
        """A new artbox set drawn from a finished picture: a pose (`pose` says
        which) or more like it. The reference is the stored picture's own
        artbox file, or for an edited picture the one it was edited from."""
        if not LOCAL_ID.fullmatch(job_id or ''):
            raise PictureError(404, 'Those pictures are gone.')
        self.editor.project.video(video)
        with self.lock:
            jobs = self._load(video)
            base, picture = self._finished(jobs, job_id, index)
            ref = _ref(base, picture)
            if not ref:
                raise PictureError(409, too_old)
            self._check_pending(jobs)
            self.check_daily_cap(author, is_admin, n)
            # A pose of a pose is still described by the first picture's words, not the last pose's.
            described = _described(base)
            origin = picture.get('origin') or {'job': base['id'], 'index': index, 'cutout': picture['cutout']}
            source = {'job': origin['job'], 'index': origin['index'], 'prompt': base['prompt'],
                      'cutout': origin['cutout'], 'ref': ref, 'seed': picture.get('seed'), 'described': described,
                      'ask': pose_prompt(described, pose) if kind == 'pose_of' else _ask(base)}
            if picture.get('origin'):
                source['edited'] = True
            job = {'id': secrets.token_hex(8), 'video': video, 'prompt': pose if kind == 'pose_of' else base['prompt'],
                   'n': n, 'cutout': base['cutout'], 'author': author, 'created': time.time(), kind: source}
            self._submit(job)
            jobs.append(job)
            self._save(video, jobs)
        return self.public(job)

    def _finished(self, jobs, job_id, index):
        """The finished set `job_id` of `jobs` and its picture `index`."""
        base = self._find(jobs, job_id)
        if base['status'] != 'done':
            raise PictureError(409, 'Wait for those pictures to finish first.')
        picture = next((p for p in base.get('pictures', []) if p['index'] == index), None)
        if picture is None:
            raise PictureError(404, 'That picture is gone.')
        return base, picture

    # ---- edits ----

    def edit(self, video, job_id, index, edit, author):
        """Flip, rotate or crop picture `index` of the finished set `job_id`
        into a new set of one, keeping the original. For a cut-out the
        original is edited alike, so "See original" still matches. Free, so
        outside the daily cap; past MAX_EDITS in a video the oldest goes."""
        if not isinstance(edit, str) or edit not in EDITS:
            raise PictureError(400, "That isn't an edit this editor can make.")
        if not LOCAL_ID.fullmatch(job_id or ''):
            raise PictureError(404, 'Those pictures are gone.')
        self.editor.project.video(video)
        with self.lock:
            jobs = self._load(video)
            base, picture = self._finished(jobs, job_id, index)
            folder = self._dir(video) / base['id']
            stems = [str(index)] + ([f'{index}-cutout'] if picture['cutout'] else [])
            if not all((folder / f'{stem}.png').is_file() for stem in stems):
                raise PictureError(404, 'That picture is gone.')
            new_id = secrets.token_hex(8)
            tmp = self._dir(video) / f'.{new_id}.tmp'
            tmp.mkdir(parents=True)
            try:
                _edit_files(folder, stems, tmp, edit)
                os.replace(tmp, self._dir(video) / new_id)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            now = time.time()
            origin = picture.get('origin') or {'job': base['id'], 'index': index, 'cutout': picture['cutout']}
            edited = {'index': 0, 'cutout': picture['cutout'], 'origin': origin, 'seed': picture.get('seed')}
            ref = _ref(base, picture)
            if ref:
                edited['ref'] = ref
            job = {'id': new_id, 'video': video, 'prompt': base['prompt'], 'n': 1, 'cutout': base['cutout'],
                   'author': author, 'created': now, 'finished': now, 'status': 'done', 'message': None,
                   'pictures': [edited],
                   'edit_of': {'job': base['id'], 'index': index, 'prompt': base['prompt'],
                               'cutout': picture['cutout'], 'edit': edit, 'label': EDITS[edit],
                               'described': _described(base), 'ask': _ask(base)}}
            jobs.append(job)
            edits = sorted((j for j in jobs if j.get('edit_of')), key=lambda j: j['created'])
            for old in edits[:max(0, len(edits) - MAX_EDITS)]:
                shutil.rmtree(self._dir(video) / old['id'], ignore_errors=True)
                jobs.remove(old)
            self._save(video, jobs)
            self._enforce_cap(video)
        return self.public(job)

    def retry(self, video, job_id, author, is_admin=False):
        with self.lock:
            jobs = self._load(video)
            job = self._find(jobs, job_id)
            if job['status'] != 'failed':
                raise PictureError(409, 'Only pictures that failed can be tried again.')
            if job.get('retryable') is False:
                raise PictureError(409, CANT_USE)
            self._check_pending(jobs)
            self.check_daily_cap(author, is_admin, job['n'])
            job['author'] = author
            self._submit(job)
            self._save(video, jobs)
        return self.public(job)

    # ---- background polling ----

    def tick(self):
        """Poll every pending job that is due, and fetch the files of any that
        finished. Network calls happen outside the lock."""
        if not self._ticking.acquire(blocking=False):
            return
        try:
            now = time.time()
            with self.lock:
                due = [(video, dict(job)) for video in list(self._videos()) for job in self._load(video)
                       if job['status'] in PENDING and job.get('next_poll', 0) <= now]
            for video, job in due:
                try:
                    changes = self._advance(video, job)
                except Exception as exc:
                    print(f'[editor] pictures: {video}: {exc}', file=sys.stderr, flush=True)
                    changes = {'next_poll': time.time() + POLL_DELAYS[-1]}
                self._apply(video, job, changes)
        finally:
            self._ticking.release()

    def _apply(self, video, before, changes):
        with self.lock:
            jobs = self._load(video)
            job = next((j for j in jobs if j['id'] == before['id']), None)
            if job is None or job.get('remote') != before.get('remote') or job['status'] not in PENDING:
                return
            job.update(changes)
            self._save(video, jobs)
            if changes.get('status') == 'done':
                self._enforce_cap(video)

    def _delay(self, polls):
        return POLL_DELAYS[min(polls, len(POLL_DELAYS) - 1)]

    def _advance(self, video, job):
        now = time.time()
        polls = job.get('polls', 0) + 1
        later = {'polls': polls, 'next_poll': now + self._delay(polls)}
        if now - job['submitted'][-1] > GIVE_UP_SECONDS:
            return {'status': 'failed', 'message': 'These waited too long and were given up. Try again.'}
        try:
            remote = self.artbox.job(job['remote'])
        except ArtboxError as exc:
            if exc.status == 404:
                return {'status': 'failed', 'message': "These pictures couldn't be made. Try again."}
            return later
        state = remote.get('state')
        if state == 'failed':
            return {'status': 'failed', 'message': "These pictures couldn't be made. Try again."}
        if state != 'done':
            return {**later, 'status': 'making' if state == 'running' else 'waiting'}
        try:
            pictures, refused = self._fetch(video, job, remote)
        except ArtboxError as exc:
            print(f'[editor] pictures: {video}: fetching {job["remote"]}: {exc}', file=sys.stderr, flush=True)
            failures = job.get('fetch_failures', 0) + 1
            if failures >= FETCH_ATTEMPTS:
                return {'status': 'failed', 'message': "These pictures couldn't be brought over. Try again."}
            return {**later, 'status': 'making', 'fetch_failures': failures}
        if not pictures and refused:
            return {'status': 'failed', 'message': CANT_USE, 'retryable': False}
        if not pictures:
            return {'status': 'failed', 'message': "These pictures couldn't be made. Try again."}
        return {'status': 'done', 'pictures': pictures, 'finished': time.time(), 'message': None}

    def _fetch(self, video, job, remote):
        """Copy a done job's PNGs into the store; (the pictures it holds, whether
        any name was refused). A name that fails validation, or a file that
        isn't a sane PNG, is skipped."""
        images = remote.get('images')
        if not isinstance(images, list):
            raise ArtboxError('done, but no images list')
        final = self._dir(video) / job['id']
        tmp = self._dir(video) / f'.{job["id"]}.tmp'
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        pictures = []
        refused = False
        try:
            for image in images[:min(job['n'], MAX_COUNT)]:
                if not isinstance(image, dict) or not valid_file_name(image.get('name')):
                    refused = True
                    print(f'[editor] pictures: refused a file name in job {job["remote"]}', file=sys.stderr, flush=True)
                    continue
                index = len(pictures)
                if not _store_png(self.artbox.file(job['remote'], image['name']), tmp, str(index), 'RGB'):
                    continue
                cutout = False
                matte = image.get('matte')
                if job['cutout'] and matte is not None:
                    if valid_file_name(matte):
                        cutout = _store_png(self.artbox.file(job['remote'], matte), tmp, f'{index}-cutout', 'RGBA')
                    else:
                        print(f'[editor] pictures: refused a file name in job {job["remote"]}', file=sys.stderr,
                              flush=True)
                pictures.append({'index': index, 'cutout': cutout, 'name': image['name'],
                                 'seed': _seed(image)})
            shutil.rmtree(final, ignore_errors=True)
            os.replace(tmp, final)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return pictures, refused

    def _enforce_cap(self, video):
        """Drop the oldest finished sets of pictures until the video's store fits
        its cap. Called with the lock held. A picture already added to a note
        is unaffected: the attachment is its own copy."""
        root = self._dir(video)
        total = sum(f.stat().st_size for f in root.rglob('*') if f.is_file())
        if total <= self.video_max_bytes:
            return
        jobs = self._load(video)
        for job in sorted((j for j in jobs if j['status'] == 'done'), key=lambda j: j.get('finished', 0))[:-1]:
            folder = root / job['id']
            total -= sum(f.stat().st_size for f in folder.rglob('*') if f.is_file()) if folder.is_dir() else 0
            shutil.rmtree(folder, ignore_errors=True)
            jobs.remove(job)
            if total <= self.video_max_bytes:
                break
        self._save(video, jobs)

    # ---- files ----

    def file(self, video, job_id, index, cutout, full):
        """(path, content type) of a stored picture or its thumbnail."""
        if not LOCAL_ID.fullmatch(job_id or ''):
            raise PictureError(404, 'Those pictures are gone.')
        with self.lock:
            job = self._find(self._load(video), job_id)
        picture = next((p for p in job.get('pictures', []) if p['index'] == index), None)
        if picture is None or (cutout and not picture['cutout']):
            raise PictureError(404, 'That picture is gone.')
        stem = f'{index}-cutout' if cutout else str(index)
        path = self._dir(video) / job_id / (stem + ('.png' if full else '.thumb.webp'))
        if not path.is_file():
            raise PictureError(404, 'That picture is gone.')
        return path, 'image/png' if full else 'image/webp'

    def attach(self, video, job_id, index, cutout):
        """Copy a stored picture into the attachment store, the way a music
        track is attached; the upload-shaped record."""
        path, _ = self.file(video, job_id, index, cutout, full=True)
        with self.lock:
            job = self._find(self._load(video), job_id)
        edit = f"-{_slug(job['edit_of']['label'])}" if job.get('edit_of') else ''
        name = f"{_slug(job['prompt'])}{edit}-{index + 1}{'-cutout' if cutout else ''}.png"
        return self.editor.attachments.upload(video, name, 'image/png', path.read_bytes())


def _ref(job, picture):
    """The artbox reference ("<jobId>/<fileName>") a pose or more like a
    stored picture is drawn from: its own file, or for an edited picture the
    one it was edited from; None for a picture from before poses."""
    if picture.get('ref'):
        return picture['ref']
    if picture.get('name') and valid_job_id(job.get('remote')):
        return f"{job['remote']}/{picture['name']}"
    return None


def _derived(job):
    return job.get('pose_of') or job.get('like_of') or job.get('edit_of')


def _described(job):
    """The words a set's subject was first described in, through any poses,
    variations and edits of it."""
    source = _derived(job)
    return source.get('described', job['prompt']) if source else job['prompt']


def _ask(job):
    """What artbox was asked to draw a set's pictures."""
    source = _derived(job)
    return source['ask'] if source else job['prompt'] + (CUTOUT_SUFFIX if job['cutout'] else '')


EDITS = {'flip': 'Flipped', 'rotate-left': 'Rotated left', 'rotate-right': 'Rotated right',
         'square': 'Cropped square', '16:9': 'Cropped to 16:9', '9:16': 'Cropped to 9:16',
         'trim': 'Edges trimmed'}
CROPS = {'square': (1, 1), '16:9': (16, 9), '9:16': (9, 16)}
# A cut-out's alpha at or under this is empty, for trimming and for finding its middle.
EMPTY_ALPHA = 8


def _crop_box(edit, size, alpha):
    """The box to crop a picture of `size` to; `alpha` is its cut-out's alpha
    channel, if it has one. A crop to a shape keeps the cut-out's subject in
    the middle as far as the edges allow."""
    w, h = size
    content = alpha.point(lambda a: 255 if a > EMPTY_ALPHA else 0).getbbox() if alpha else None
    if edit == 'trim':
        if alpha is None:
            raise PictureError(409, 'Only a picture with its background cut out has empty edges to trim.')
        if content is None:
            raise PictureError(409, 'This picture is empty, so there is nothing to keep.')
        if content == (0, 0, w, h):
            raise PictureError(409, 'This picture has no empty edges to trim.')
        return content
    rw, rh = CROPS[edit]
    cw, ch = (round(h * rw / rh), h) if w * rh > h * rw else (w, round(w * rh / rw))
    if (cw, ch) == (w, h):
        raise PictureError(409, 'This picture is already that shape.')
    cx, cy = ((content[0] + content[2]) / 2, (content[1] + content[3]) / 2) if content else (w / 2, h / 2)
    left = min(max(round(cx - cw / 2), 0), w - cw)
    top = min(max(round(cy - ch / 2), 0), h - ch)
    return left, top, left + cw, top + ch


def _edit_files(folder, stems, out, edit):
    """Write `edit` of each stored `<stem>.png` in `folder` (the original,
    then its cut-out if any) into `out` as picture 0, with its thumbnail. A
    crop is worked out on the cut-out and applied to both, scaled if their
    sizes differ."""
    from PIL import Image
    images = []
    for stem in stems:
        with Image.open(folder / f'{stem}.png') as im:
            im.load()
            images.append(im)
    if edit in CROPS or edit == 'trim':
        cutout = images[1] if len(images) > 1 else None
        alpha = cutout.convert('RGBA').getchannel('A') if cutout else None
        box = _crop_box(edit, (cutout or images[0]).size, alpha)
        sized = (cutout or images[0]).size
        edited = []
        for im in images:
            sx, sy = im.size[0] / sized[0], im.size[1] / sized[1]
            edited.append(im.crop((round(box[0] * sx), round(box[1] * sy), round(box[2] * sx), round(box[3] * sy))))
    else:
        turn = {'flip': Image.Transpose.FLIP_LEFT_RIGHT, 'rotate-left': Image.Transpose.ROTATE_90,
                'rotate-right': Image.Transpose.ROTATE_270}[edit]
        edited = [im.transpose(turn) for im in images]
    for stem, mode, im in zip(('0', '0-cutout'), ('RGB', 'RGBA'), edited):
        im.save(out / f'{stem}.png', 'PNG')
        _write_thumb(im, out, stem, mode)


def _write_thumb(im, folder, stem, mode):
    thumb = im.convert(mode)
    thumb.thumbnail((THUMB_SIDE, THUMB_SIDE))
    thumb.save(folder / f'{stem}.thumb.webp', 'WEBP', quality=82)


def _seed(image):
    """An artbox image's seed: its own `seed`, or the one artbox writes into
    its file name ("..._seed1234_..."); None when neither says."""
    seed = image.get('seed')
    if isinstance(seed, int) and not isinstance(seed, bool) and 0 <= seed < 2 ** 63:
        return seed
    match = SEED_IN_NAME.search(image['name'])
    return int(match.group(1)) if match and int(match.group(1)) < 2 ** 63 else None


def _store_png(data, folder, stem, mode):
    """Check `data` is a PNG of sane size, then write it and a small WebP
    thumbnail (keeping transparency for a cut-out); False if it isn't one."""
    from PIL import Image
    if not data.startswith(PNG_MAGIC):
        return False
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.format != 'PNG' or max(im.size) > MAX_SIDE:
                return False
            im.load()
            thumb = im.convert(mode)
    except Exception:
        return False
    (folder / f'{stem}.png').write_bytes(data)
    _write_thumb(thumb, folder, stem, mode)
    return True
