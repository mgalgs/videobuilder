"""Review notes: a reviewer's request pinned to a moment of a video, for an
agent to act on. The editor stores them; an `AgentBackend` takes them on.

A note pins its text to (video, format, frame, segment) and keeps that
frame's PNG beside it. Notes live in the editor's state directory, one JSON
file and one PNG per note:

    <state>/notes/<id>.json
    <state>/notes/<id>.png

The backend retains submit(note) -> str and poll(handle) -> AgentStatus.
Submissions additionally carry project, film, directory, beat, time, image,
note_file, state_dir, session (stable id), and draft (current branch or null).
One note per video is submitted at a time; other notes wait in order.
Listing notes polls in-flight handles, including after restart, and dispatches
the next note after replied/failed. accepted/dropped are reviewer decisions.
Per-video session.json survives both decisions. The runner owns any additional
session files. See agents.py for the external command protocol. Submission
must be idempotent by note id to tolerate a crash before saving the handle.
"""
import hashlib
from pathlib import Path
import json
import os
import secrets
import threading
import time
from dataclasses import asdict, dataclass

STATES = ('queued', 'working', 'replied', 'failed', 'accepted', 'dropped', 'landed', 'refused', 'conflict')
FINAL = ('replied', 'failed', 'accepted', 'dropped', 'landed', 'refused', 'conflict')


@dataclass
class AgentStatus:
    state: str                 # one of STATES
    reply: str | None = None   # the agent's answer to the reviewer
    branch: str | None = None  # a draft branch with the agent's change, for review

    def __post_init__(self):
        if self.state not in STATES:
            raise ValueError(f'unknown note state {self.state!r}; known: {", ".join(STATES)}')


class AgentBackend:
    """Where notes go. Subclass it, and pass an instance to the editor."""
    name = 'agent'

    def submit(self, note):
        """Take on `note` (a dict: id, video, format, frame, segment, text,
        author, created, and `image`, the path of its frame's PNG). Return a
        handle (a string) to poll it by. Called once per note."""
        raise NotImplementedError

    def poll(self, handle):
        """The `AgentStatus` of the note submitted as `handle`."""
        raise NotImplementedError


class NullBackend(AgentBackend):
    """Sends notes nowhere: every note stays queued."""
    name = 'null'

    def submit(self, note):
        return f'null:{note["id"]}'

    def poll(self, handle):
        return AgentStatus('queued')


class NoteStore:
    """Notes on disk under `dir`, submitted to `backend` as they are added."""

    def __init__(self, dir, backend=None, context=None, before_submit=None, on_reply=None, attachments=None):
        self.dir = os.path.abspath(dir)
        self.backend = backend or NullBackend()
        self.lock = threading.RLock()
        self.video_locks = {}
        self.context = context or (lambda video: {})
        self.before_submit, self.on_reply, self.attachments = before_submit, on_reply, attachments

    def video_lock(self, video):
        with self.lock:
            return self.video_locks.setdefault(video, threading.RLock())

    def _path(self, nid, ext):
        if not nid or not all(c.isalnum() or c in '-_' for c in nid):
            raise KeyError(nid)
        return os.path.join(self.dir, f'{nid}.{ext}')

    def _save(self, note):
        path = self._path(note['id'], 'json')
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(note, fh, indent=1, ensure_ascii=False)
            fh.write('\n')
        os.replace(tmp, path)

    def add(self, video, format, frame, segment, text, png, author=None, **context):
        """Store a new note with its frame's PNG bytes, submit it, and return it."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError('a note needs some text')
        os.makedirs(self.dir, exist_ok=True)
        now = time.time()
        nid = time.strftime('%Y%m%dT%H%M%S', time.gmtime(now)) + f'{int(now % 1 * 1e6):06d}Z-{secrets.token_hex(3)}'
        if png is not None:
            with open(self._path(nid, 'png'), 'wb') as fh:
                fh.write(png)
        note = {'id': nid, 'video': video, 'format': format, 'frame': frame, 'segment': segment,
                'text': text.strip(), 'author': author,
                'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)),
                **context, 'backend': self.backend.name, 'handle': None, **asdict(AgentStatus('queued'))}
        with self.video_lock(video):
            self._save(note)
            self._advance(video)
            note = self.get(nid)
        return note

    def get(self, nid):
        try:
            with open(self._path(nid, 'json'), encoding='utf-8') as fh:
                return json.load(fh)
        except FileNotFoundError:
            raise KeyError(nid) from None

    def current(self, nid):
        """One note after polling its video's backend, as list() does."""
        video = self.get(nid)['video']
        with self.video_lock(video):
            self._advance(video)
        return self.get(nid)

    def image(self, nid):
        """The PNG bytes of a note's frame."""
        try:
            with open(self._path(nid, 'png'), 'rb') as fh:
                return fh.read()
        except FileNotFoundError:
            raise KeyError(nid) from None

    def session_dir(self, video):
        slug = ''.join(c if c.isascii() and c.isalnum() else '-' for c in video)
        slug = slug[:96]
        slug += '-' + hashlib.sha256(video.encode()).hexdigest()[:12]
        path = Path(self.dir).parent / 'sessions' / slug
        path.mkdir(parents=True, exist_ok=True)
        return path

    def session(self, video):
        path = self.session_dir(video) / 'session.json'
        if path.exists():
            return json.loads(path.read_text())
        state = dict(session=path.parent.name, draft=None)
        self.save_session(video, state)
        return state

    def save_session(self, video, state):
        path = self.session_dir(video) / 'session.json'
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state))
        tmp.replace(path)

    def list(self, video=None, refresh=True):
        notes = []
        for path in sorted(Path(self.dir).glob('*.json')):
            try:
                note = self.get(path.stem)
            except KeyError:
                continue
            if video is None or note['video'] == video:
                notes.append(note)
        if refresh:
            for vid in dict.fromkeys(n['video'] for n in notes):
                with self.video_lock(vid):
                    self._advance(vid)
            return self.list(video, refresh=False)
        return notes

    def pending(self):
        """The videos that have a note not yet in a final state."""
        return list(dict.fromkeys(n['video'] for n in self.list(refresh=False) if n['state'] not in FINAL))

    def tick(self):
        """Advance every video with unfinished notes, as a page poll would."""
        for vid in self.pending():
            with self.video_lock(vid):
                self._advance(vid)

    def _advance(self, video):
        for note in self.list(video, refresh=False):
            if note['state'] in FINAL:
                continue
            state = self.session(video)
            if not note['handle']:
                try:
                    if self.before_submit:
                        self.before_submit(video, note, state)
                    payload = {**note, **self.context(video), **state,
                               'state_dir': str(self.session_dir(video)),
                               'image': self._path(note['id'], 'png') if note.get('frame') is not None else None}
                    path = self.session_dir(video) / (note['id'] + '.md')
                    lines = ['# Review request', '', *([note['rejection']] if note.get('rejection') else []), note['text'], '']
                    if note.get('time') is not None:
                        t = note['time']
                        lines += [f'At {int(t // 60)}:{int(t % 60):02d} (frame {note["frame"]}, segment {json.dumps(note.get("segment"))})', '']
                    if note.get('attachments'):
                        lines += ['Attachments (read-only reference files):']
                        for item in note['attachments']:
                            lines.append(f'- /attachments/{item["name"]} ({item["type"]}, {item["size"]} bytes)')
                        lines += ['Use them as reference. To include one in the video, copy it into the video assets directory and commit it there. Never write into /attachments.', '']
                    for key in ('video', 'film', 'format', 'frame', 'segment', 'beat', 'time', 'image', 'draft'):
                        lines.append(f"{key}: {payload.get(key)}")
                    lines += ['', f"Change files only under {payload.get('directory', video)}.",
                              'Commit only changes to the video. Never commit a reply or notes file: '
                              'end with a short answer for the reviewer as your final message, '
                              'and it is shown to them as your reply.',
                              'Continue the supplied draft, or start from main when draft is null.',
                              'End your reply with Summary: <one line>.']
                    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                    payload['note_file'] = str(path)
                    if self.attachments:
                        payload['attach_dir'] = self.attachments.stage(note)
                    note['handle'] = self.backend.submit(payload)
                    note['started'] = time.time()
                    self._save(note)
                    return
                except Exception as e:
                    note.update(state='failed', reply=f'could not submit: {e}')
            else:
                try:
                    status = self.backend.poll(note['handle'])
                    if status.branch and state['draft'] and status.branch != state['draft']:
                        status = AgentStatus('failed', 'Runner returned a different draft branch; '
                                             'continue ' + state['draft'])
                    note.update(asdict(status))
                    note.pop('poll_error', None)
                    if status.branch:
                        state['draft'] = status.branch
                        self.save_session(video, state)
                    self._save(note)
                    if status.state == 'replied' and self.on_reply:
                        self.on_reply(video, note)
                except Exception as e:
                    note['poll_error'] = str(e)
                    self._save(note)
                    return
            self._save(note)
            if note['state'] not in FINAL:
                return

    def resolve(self, video, branch, action, author):
        with self.video_lock(video):
            for note in self.list(video, refresh=False):
                if note['branch'] == branch and note['state'] == 'replied':
                    note['state'] = action
                    note.setdefault('history', []).append(dict(state=action, author=author, at=time.time()))
                    self._save(note)
            state = self.session(video)
            state['draft'] = None
            self.save_session(video, state)

    def delete(self, nid):
        video = self.get(nid)['video']
        with self.video_lock(video):
            note = self.get(nid)
            if note['state'] not in FINAL and note['handle'] and self.backend.name != 'null':
                raise ValueError('cannot delete an in-flight note')
            for ext in ('json', 'png'):
                try:
                    os.remove(self._path(nid, ext))
                except FileNotFoundError:
                    pass
