"""Library-level uploads made before a video exists: the New video page
stages each dropped or picked file here as it uploads, with progress, and
`POST /api/videos/new` claims the ones the Start click actually wants
(see `Library.create_video`). Storage is `<state_dir>/staging/<id>/
{meta.json,<name>}`, one directory per upload, validated the same way an
ordinary attachment is (attachments._sanitize_name/_validate_content).

`owner` is the signed-in username with accounts on, else None: with no
accounts, every caller shares one pool and nothing here enforces who staged
what. A `.zip` is refused outright -- unpacking happens on an existing
video's own attachments route, not here. An id not claimed within
EXPIRE_SECONDS is swept, the same rule attachments.Attachments.expire uses.
"""
import json
import re
import secrets
import shutil
import time
from pathlib import Path

from .attachments import MAGIC, TYPES, _sanitize_name, _validate_content

MAX_FILE = 25 * 1048576
MAX_FILES = 50
MAX_BYTES = 300 * 1048576
EXPIRE_SECONDS = 86400


class TooLarge(ValueError):
    """Over the per-file size limit or the owner's pending allowance; mapped
    to HTTP 413, unlike a plain ValueError (400 -- a bad type or magic)."""


class Staging:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def upload(self, name, ctype, data, owner):
        self.expire()
        name = _sanitize_name(name)
        if name.lower().endswith('.zip'):
            raise ValueError('unpack the zip and add its files')
        ext = name.rsplit('.', 1)[-1].lower()
        if ext not in MAGIC:
            raise ValueError('unsupported attachment type')
        if len(data) > MAX_FILE:
            raise TooLarge('attachment exceeds file size limit')
        _validate_content(ctype, data, ext)
        pending = self._pending(owner)
        if len(pending) >= MAX_FILES or sum(r['size'] for r in pending) + len(data) > MAX_BYTES:
            raise TooLarge('too many staged files; start the video or remove some first')
        ident = secrets.token_hex(16)
        record = {'id': ident, 'name': name, 'type': TYPES[ext], 'size': len(data),
                  'created': time.time(), 'owner': owner}
        path = self.root / ident
        path.mkdir()
        (path / name).write_bytes(data)
        (path / 'meta.json').write_text(json.dumps(record))
        return {'id': ident, 'name': name, 'type': record['type'], 'size': record['size']}

    def get(self, ident, owner=None):
        if not re.fullmatch('[0-9a-f]{32}', ident):
            raise KeyError(ident)
        try:
            meta = json.loads((self.root / ident / 'meta.json').read_text())
        except FileNotFoundError:
            raise KeyError(ident) from None
        if owner is not None and meta.get('owner') != owner:
            raise KeyError(ident)
        return meta, self.root / ident / meta['name']

    def delete(self, ident, owner):
        meta, path = self.get(ident, owner)
        shutil.rmtree(path.parent)
        return meta

    def _pending(self, owner):
        out = []
        for p in self.root.glob('*/meta.json'):
            try:
                meta = json.loads(p.read_text())
            except (OSError, ValueError, KeyError):
                continue
            if meta.get('owner') == owner:
                out.append(meta)
        return out

    def expire(self):
        now = time.time()
        for p in self.root.glob('*/meta.json'):
            try:
                meta = json.loads(p.read_text())
                if now - meta['created'] >= EXPIRE_SECONDS:
                    shutil.rmtree(p.parent, ignore_errors=True)
            except (OSError, ValueError, KeyError):
                continue
