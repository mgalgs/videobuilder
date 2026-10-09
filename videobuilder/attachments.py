"""Validated per-video uploads and per-note copies for fork-sandbox."""
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import time

MAGIC = {
    'png': (b'\x89PNG\r\n\x1a\n',), 'jpg': (b'\xff\xd8\xff',), 'jpeg': (b'\xff\xd8\xff',),
    'webp': (b'RIFF',), 'gif': (b'GIF87a', b'GIF89a'), 'mp4': (b'\x00\x00',),
    'mov': (b'\x00\x00',), 'webm': (b'\x1a\x45\xdf\xa3',), 'mp3': (b'ID3', b'\xff\xfb', b'\xff\xf3'),
    'wav': (b'RIFF',), 'm4a': (b'\x00\x00',), 'aac': (b'\xff\xf1', b'\xff\xf9'),
    'ogg': (b'OggS',), 'pdf': (b'%PDF-',), 'txt': (), 'md': ()}
TYPES = {'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp','gif':'image/gif',
         'mp4':'video/mp4','mov':'video/quicktime','webm':'video/webm','mp3':'audio/mpeg','wav':'audio/wav',
         'm4a':'audio/mp4','aac':'audio/aac','ogg':'audio/ogg','pdf':'application/pdf',
         'txt':'text/plain','md':'text/plain'}


class Attachments:
    def __init__(self, editor, max_file, max_files, max_message):
        self.editor = editor
        self.max_file, self.max_files, self.max_message = max_file, max_files, max_message
        self.root = Path(editor.state_dir) / 'attachments'
        self.root.mkdir(parents=True, exist_ok=True)

    def upload(self, video, name, ctype, data):
        self.editor.project.video(video)
        self.expire()
        if len(data) > self.max_file:
            raise ValueError('attachment exceeds file size limit')
        name = re.sub(r'[^A-Za-z0-9._-]', '_', Path(name.replace('\\', '/')).name).lstrip('.') or 'file'
        ext = name.rsplit('.', 1)[-1].lower()
        if ext not in MAGIC:
            raise ValueError('unsupported attachment type')
        if ctype.split(';', 1)[0].strip().lower() != TYPES[ext]:
            raise ValueError('Content-Type does not match attachment extension')
        if ext in ('txt', 'md'):
            try:
                data.decode('utf-8')
            except UnicodeError:
                raise ValueError('text attachment must be UTF-8') from None
        elif not any(data.startswith(x) for x in MAGIC[ext]):
            raise ValueError('attachment magic bytes do not match extension')
        if ext in ('webp', 'wav') and data[8:12] != (b'WEBP' if ext == 'webp' else b'WAVE'):
            raise ValueError('attachment magic bytes do not match extension')
        if ext in ('mp4', 'mov', 'm4a') and data[4:8] != b'ftyp':
            raise ValueError('attachment magic bytes do not match extension')
        ident = secrets.token_hex(16)
        record = dict(id=ident, video=video, name=name, type=TYPES[ext], size=len(data), created=time.time())
        path = self.root / ident
        path.mkdir()
        (path / name).write_bytes(data)
        (path / 'meta.json').write_text(json.dumps(record))
        return {k: record[k] for k in ('id', 'name', 'type', 'size')}

    def get(self, ident, video=None):
        if not re.fullmatch('[0-9a-f]{32}', ident):
            raise KeyError(ident)
        try:
            meta = json.loads((self.root / ident / 'meta.json').read_text())
        except FileNotFoundError:
            raise KeyError(ident) from None
        if video is not None and meta['video'] != video:
            raise KeyError(ident)
        return meta, self.root / ident / meta['name']

    def validate(self, video, ids):
        if not isinstance(ids, list) or len(ids) > self.max_files or len(ids) != len(set(ids)):
            raise ValueError('too many or duplicate attachments')
        records = [self.get(ident, video)[0] for ident in ids]
        if sum(x['size'] for x in records) > self.max_message:
            raise ValueError('attachments exceed message size limit')
        out, names = [], set()
        for x in records:
            item = {k: x[k] for k in ('id', 'name', 'type', 'size')}
            if item['name'] in names:
                stem, dot, ext = item['name'].rpartition('.')
                item['name'] = (stem or ext) + '-' + item['id'][:8] + (dot + ext if dot else '')
            names.add(item['name'])
            out.append(item)
        return out

    def stage(self, note):
        records = note.get('attachments') or []
        if not records:
            return None
        path = self.editor.notes.session_dir(note['video']) / ('attachments-' + note['id'])
        path.mkdir(exist_ok=True)
        for record in records:
            source = self.get(record['id'], note['video'])[1]
            shutil.copyfile(source, path / record['name'])
        return str(path)

    def expire(self):
        used = {x['id'] for n in self.editor.notes.list(refresh=False) for x in n.get('attachments', [])}
        for path in self.root.glob('*/meta.json'):
            try:
                meta = json.loads(path.read_text())
                if meta['id'] not in used and time.time() - meta['created'] >= 86400:
                    shutil.rmtree(path.parent)
            except (ValueError, KeyError):
                continue
