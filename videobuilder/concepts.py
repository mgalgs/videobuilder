"""Concept art for pre-production (see preprod.py, notes.strip_concepts,
docs/preproduction.md): a builder reply's ```concepts block becomes one
artbox job per request, generated only after that note's change actually
lands (see `kick`) -- never through pictures.py's Pictures: artbox is a home
GPU with no per-image cost here, and a concept must never show up in the
director's own Pictures panel or count against its caps.

Jobs live in `<state_dir>/concepts/jobs.json`:
{"jobs": [{id, video, note, set, key, prompt, status, remote, polls,
next_poll, submitted, fetch_failures, message}]}. `status` is one of:

    requested   accepted, waiting to learn whether the note that asked for
                it actually landed (see `kick`)
    making      submitted to artbox, polled by `tick`
    ready       the PNG is fetched (<state_dir>/concepts/<job-id>.png) but
                not committed yet -- main's checkout was dirty; `tick`
                retries the commit every time after this
    done        committed into the bible; final
    unavailable final; `message` says why (no artbox, artbox unreachable,
                the job failed, the note's change wasn't kept, or the
                request was over the note's own cap)
"""
import json
import secrets
import sys
import threading
import time
from pathlib import Path

from . import preprod
from .atomic import write_json_atomic
from .pictures import ArtboxError, GIVE_UP_SECONDS, POLL_DELAYS, valid_file_name

NO_ARTBOX = "The picture maker isn't set up on this editor."
UNREACHABLE = "The picture maker isn't answering."
FAILED = "This picture couldn't be made."
NOT_KEPT = "The builder's change was not kept."
OVER_LIMIT = 'over the limit for one note'

CAP_CHARACTER, CAP_LOOK, CAP_OTHER, CAP_TOTAL = 3, 4, 4, 16
FETCH_ATTEMPTS = 3

# A note whose commits are on main (landed, or there never was a branch to land) is kept;
# one of these is not, so a request riding on it is moot.
_NOT_KEPT_STATES = ('refused', 'conflict', 'dropped', 'failed')


def _cap(set_id):
    if set_id == 'look':
        return CAP_LOOK
    if isinstance(set_id, str) and set_id.startswith('character-'):
        return CAP_CHARACTER
    return CAP_OTHER


def has_pending(root):
    """Whether `root` (a concepts dir, <state_dir>/concepts) has a job still
    on its way, read straight off disk -- Library.tick_pictures, without
    opening an Editor."""
    try:
        data = json.loads((Path(root) / 'jobs.json').read_text())
    except (OSError, ValueError):
        return False
    jobs = data.get('jobs') if isinstance(data, dict) else None
    return bool(jobs) and any(j.get('status') in ('requested', 'making', 'ready') for j in jobs)


class Concepts:
    def __init__(self, editor, artbox):
        self.editor, self.artbox = editor, artbox
        self.root = Path(editor.state_dir) / 'concepts'
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'jobs.json'
        self.lock = threading.RLock()

    def _load(self):
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return []
        return data.get('jobs', []) if isinstance(data, dict) else []

    def _save(self, jobs):
        write_json_atomic(self.path, {'jobs': jobs})

    def _update(self, job_id, **changes):
        with self.lock:
            jobs = self._load()
            job = next((j for j in jobs if j['id'] == job_id), None)
            if job is None:
                return
            job.update(**changes)
            self._save(jobs)

    # ---- accepting a note's requests (notes.py's NoteStore.concepts) ----

    def request(self, video, note_id, requests):
        """`requests`: [{'set', 'key', 'prompt'}], already parsed from a
        reply's ```concepts block (notes.strip_concepts). Returns the
        note's own `concepts`: each request plus `status` ('requested', or
        already 'unavailable' when it's over the note's own cap or this
        editor has no artbox configured at all)."""
        out = []
        per_set, total = {}, 0
        with self.lock:
            jobs = self._load()
            for r in requests:
                set_id, key, prompt = r.get('set'), r.get('key'), r.get('prompt')
                entry = {'set': set_id, 'key': key, 'prompt': prompt}
                count = per_set.get(set_id, 0)
                if total >= CAP_TOTAL or count >= _cap(set_id):
                    out.append({**entry, 'status': 'unavailable', 'message': OVER_LIMIT})
                    continue
                per_set[set_id], total = count + 1, total + 1
                if self.artbox is None:
                    out.append({**entry, 'status': 'unavailable', 'message': NO_ARTBOX})
                    continue
                jobs.append({'id': secrets.token_hex(8), 'video': video, 'note': note_id, 'set': set_id,
                            'key': key, 'prompt': prompt, 'status': 'requested', 'remote': None, 'polls': 0,
                            'next_poll': 0, 'submitted': None, 'fetch_failures': 0, 'message': None})
                out.append({**entry, 'status': 'requested'})
            self._save(jobs)
        return out

    def refresh(self, note_id, entries):
        """`entries` (a note's stored `concepts`, as `request` returned
        them) brought up to date from the jobs `kick`/`tick` have moved
        along since -- NoteStore.get applies this on every read, so a
        note's `concepts` (and the board's, read off the notes) is never
        staler than jobs.json. A job's `ready` (fetched, commit pending)
        shows as `making`: to a reader, it isn't in the bible yet."""
        if not any(e.get('status') in ('requested', 'making') for e in entries):
            return entries
        # request() made one job per entry it didn't mark unavailable up front, in entry order.
        jobs = iter([j for j in self._load() if j['note'] == note_id])
        out = []
        for entry in entries:
            if entry.get('status') == 'unavailable' and entry.get('message') in (OVER_LIMIT, NO_ARTBOX):
                out.append(entry)
                continue
            job = next(jobs, None)
            if job is None:
                out.append(entry)
                continue
            status = 'making' if job['status'] == 'ready' else job['status']
            out.append({**entry, 'status': status, 'message': job.get('message')})
        return out

    def pending(self, video=None):
        return [j for j in self._load() if j['status'] in ('requested', 'making', 'ready')
               and (video is None or j['video'] == video)]

    def has_pending(self):
        return bool(self.pending())

    # ---- a note's fate decides whether a request actually starts ----

    def kick(self, video):
        """Once a note's commits have landed (or it never had a branch to
        land), submit its still-`requested` jobs to artbox; once a note's
        change was *not* kept, mark them unavailable instead. Idempotent:
        a job already past `requested` is left alone, so this is safe to
        call after every note outcome (Editor._on_reply, Drafts.accept,
        Drafts.drop)."""
        with self.lock:
            jobs = self._load()
            changed = False
            for job in jobs:
                if job['video'] != video or job['status'] != 'requested':
                    continue
                try:
                    note = self.editor.notes.get(job['note'])
                except KeyError:
                    job.update(status='unavailable', message=NOT_KEPT)
                    changed = True
                    continue
                kept = self._kept(note)
                if kept:
                    self._start(job)
                    changed = True
                elif kept is False:
                    job.update(status='unavailable', message=NOT_KEPT)
                    changed = True
            if changed:
                self._save(jobs)

    def _kept(self, note):
        """True once `note`'s commits are on main, False once they never
        will be, None while that's still open. A `questions` note counts
        like a `replied` one: the prompt has the builder commit an option
        set and then ask about it, and neither Accept (notes.resolve only
        moves `replied` notes) nor a missing branch moves it on."""
        from .gitutil import git
        state = note['state']
        if state in ('landed', 'accepted'):
            return True
        if state in _NOT_KEPT_STATES:
            return False
        if state not in ('replied', 'questions'):
            return None
        branch = note.get('branch')
        if not branch:
            return True
        try:
            git(self.editor.root, 'rev-parse', '--verify', 'refs/heads/' + branch)
        except ValueError:
            return False
        try:
            git(self.editor.root, 'merge-base', '--is-ancestor', 'refs/heads/' + branch, 'refs/heads/main')
        except ValueError:
            return None
        return True

    def _start(self, job):
        try:
            remote = self.artbox.submit(job['prompt'], 1, False)
        except ArtboxError as exc:
            print(f'[editor] concepts: start failed: {exc}', file=sys.stderr, flush=True)
            job.update(status='unavailable', message=UNREACHABLE)
            return
        job.update(remote=remote['id'], status='making', polls=0, submitted=time.time(),
                  next_poll=time.time() + POLL_DELAYS[0])

    # ---- polling and committing ----

    def tick(self):
        """Advance every job due a poll, then retry committing every job
        whose picture is fetched but not yet landed (a dirty main checkout
        at the time -- see docs/preproduction.md)."""
        # A note's fate can settle without passing through a kick (a `questions` note with no
        # branch never calls on_reply), so every tick also settles still-`requested` jobs.
        for video in dict.fromkeys(j['video'] for j in self._load() if j['status'] == 'requested'):
            self.kick(video)
        now = time.time()
        with self.lock:
            due = [dict(j) for j in self._load() if j['status'] == 'making' and j.get('next_poll', 0) <= now]
        for job in due:
            self._advance(job)
        with self.lock:
            ready = [dict(j) for j in self._load() if j['status'] == 'ready']
        for job in ready:
            self._commit(job)

    def _advance(self, job):
        now = time.time()
        if now - job['submitted'] > GIVE_UP_SECONDS:
            self._update(job['id'], status='unavailable', message=UNREACHABLE)
            return
        try:
            remote = self.artbox.job(job['remote'])
        except ArtboxError as exc:
            if exc.status == 404:
                self._update(job['id'], status='unavailable', message=FAILED)
            else:
                self._update(job['id'], next_poll=now + POLL_DELAYS[-1])
            return
        state = remote.get('state')
        if state == 'failed':
            self._update(job['id'], status='unavailable', message=FAILED)
            return
        if state != 'done':
            polls = job.get('polls', 0) + 1
            self._update(job['id'], polls=polls, next_poll=now + POLL_DELAYS[min(polls, len(POLL_DELAYS) - 1)])
            return
        images = remote.get('images')
        name = images[0].get('name') if isinstance(images, list) and images and isinstance(images[0], dict) else None
        if not valid_file_name(name):
            self._update(job['id'], status='unavailable', message=FAILED)
            return
        try:
            data = self.artbox.file(job['remote'], name)
        except ArtboxError as exc:
            print(f'[editor] concepts: fetching {job["remote"]}: {exc}', file=sys.stderr, flush=True)
            failures = job.get('fetch_failures', 0) + 1
            if failures >= FETCH_ATTEMPTS:
                self._update(job['id'], status='unavailable', message=FAILED)
            else:
                self._update(job['id'], fetch_failures=failures, next_poll=now + POLL_DELAYS[-1])
            return
        from .pictures import _store_png
        if not _store_png(data, self.root, job['id'], 'RGB'):
            self._update(job['id'], status='unavailable', message=FAILED)
            return
        self._update(job['id'], status='ready')

    def _commit(self, job):
        from .editor import HTTPError
        png_path = self.root / f"{job['id']}.png"
        try:
            data = png_path.read_bytes()
        except OSError:
            self._update(job['id'], status='unavailable', message=FAILED)
            return
        video, set_id, key = job['video'], job['set'], job['key']
        try:
            directory = Path(self.editor.project.video(video).path).parent
        except KeyError:
            self._update(job['id'], status='unavailable', message=NOT_KEPT)
            self._cleanup(job['id'])
            return
        try:
            current = preprod.read_set(directory, set_id)
        except ValueError:
            current = None
        if current is None or key not in [o['key'] for o in current['options']]:
            self._update(job['id'], status='unavailable', message=NOT_KEPT)
            self._cleanup(job['id'])
            return
        image_path = f'{preprod.set_image_dir(set_id)}/{key}.png'
        options = [dict(o) for o in current['options']]
        for o in options:
            if o['key'] == key:
                o['image'], o['kind'] = image_path, 'concept'
        new_set = {**current, 'options': options}
        with self.editor.lock:
            try:
                self.editor.commit_files(video, {image_path: data, preprod.set_path(set_id): preprod.set_bytes(new_set)},
                                         f'Concept: {set_id} {key}', 'editor')
            except HTTPError:
                # Main's checkout has local changes right now (another commit mid-flight):
                # stays 'ready', retried on the next tick rather than losing the picture.
                return
        self._cleanup(job['id'])
        self._update(job['id'], status='done')

    def _cleanup(self, job_id):
        (self.root / f'{job_id}.png').unlink(missing_ok=True)
        (self.root / f'{job_id}.thumb.webp').unlink(missing_ok=True)
