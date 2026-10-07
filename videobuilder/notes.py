"""Review notes: a reviewer's request pinned to a moment of a video, for an
agent to act on. The editor stores them; an `AgentBackend` takes them on.

A note pins its text to (video, format, frame, segment) and keeps that
frame's PNG beside it. Notes live in the editor's state directory, one JSON
file and one PNG per note:

    <state>/notes/<id>.json
    <state>/notes/<id>.png

The backend interface is two calls, so a note's life can run anywhere (a
local agent, a queue, a hosted service):

    class AgentBackend:
        name: str
        def submit(self, note) -> str            # a handle for the note
        def poll(self, handle) -> AgentStatus    # its state, reply and branch

`AgentStatus.state` is one of STATES: 'queued' (waiting), 'working',
'replied' (the agent answered, maybe with a draft branch), 'failed'. The
editor submits each new note once, stores the handle, and polls handles of
notes not yet 'replied' or 'failed' when notes are listed. v1 ships only
`NullBackend`, which keeps every note queued.
"""
import json
import os
import secrets
import threading
import time
from dataclasses import asdict, dataclass

STATES = ('queued', 'working', 'replied', 'failed')
FINAL = ('replied', 'failed')


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

    def __init__(self, dir, backend=None):
        self.dir = os.path.abspath(dir)
        self.backend = backend or NullBackend()
        self.lock = threading.Lock()

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

    def add(self, video, format, frame, segment, text, png, author=None):
        """Store a new note with its frame's PNG bytes, submit it, and return it."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError('a note needs some text')
        os.makedirs(self.dir, exist_ok=True)
        now = time.time()
        nid = time.strftime('%Y%m%dT%H%M%S', time.gmtime(now)) + f'{int(now % 1 * 1e6):06d}Z-{secrets.token_hex(3)}'
        with open(self._path(nid, 'png'), 'wb') as fh:
            fh.write(png)
        note = {'id': nid, 'video': video, 'format': format, 'frame': frame, 'segment': segment,
                'text': text.strip(), 'author': author,
                'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)),
                'backend': self.backend.name, 'handle': None, **asdict(AgentStatus('queued'))}
        with self.lock:
            self._save(note)
        try:
            handle = self.backend.submit({**note, 'image': self._path(nid, 'png')})
        except Exception as e:  # the note is kept; its state says why it went nowhere
            note.update(state='failed', reply=f'could not submit: {e}')
        else:
            note['handle'] = handle
        with self.lock:
            self._save(note)
        return note

    def get(self, nid):
        try:
            with open(self._path(nid, 'json'), encoding='utf-8') as fh:
                return json.load(fh)
        except FileNotFoundError:
            raise KeyError(nid) from None

    def image(self, nid):
        """The PNG bytes of a note's frame."""
        try:
            with open(self._path(nid, 'png'), 'rb') as fh:
                return fh.read()
        except FileNotFoundError:
            raise KeyError(nid) from None

    def list(self, video=None, refresh=True):
        """Notes, oldest first (all of them, or one video's). With `refresh`,
        notes still in flight are polled and their new status stored."""
        try:
            names = sorted(f for f in os.listdir(self.dir) if f.endswith('.json'))
        except FileNotFoundError:
            return []
        out = []
        for name in names:
            try:
                note = self.get(name[:-5])
            except (KeyError, ValueError):
                continue
            if video is not None and note.get('video') != video:
                continue
            if refresh and note.get('handle') and note.get('state') not in FINAL:
                self._refresh(note)
            out.append(note)
        return out

    def _refresh(self, note):
        try:
            status = self.backend.poll(note['handle'])
        except Exception:
            return  # a backend hiccup: try again on the next look
        new = asdict(status)
        if any(note.get(k) != v for k, v in new.items()):
            note.update(new)
            with self.lock:
                self._save(note)

    def delete(self, nid):
        found = False
        for ext in ('json', 'png'):
            try:
                os.remove(self._path(nid, ext))
                found = True
            except FileNotFoundError:
                pass
        if not found:
            raise KeyError(nid)
