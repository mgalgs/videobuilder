"""Validated per-video uploads and per-note copies for fork-sandbox."""
import io
import json
from pathlib import Path
import re
import secrets
import shutil
import stat
import time
import zipfile
import zlib
from xml.etree import ElementTree

MAGIC = {
    'png': (b'\x89PNG\r\n\x1a\n',), 'jpg': (b'\xff\xd8\xff',), 'jpeg': (b'\xff\xd8\xff',),
    'webp': (b'RIFF',), 'gif': (b'GIF87a', b'GIF89a'), 'mp4': (b'\x00\x00',),
    'mov': (b'\x00\x00',), 'webm': (b'\x1a\x45\xdf\xa3',), 'mp3': (b'ID3', b'\xff\xfb', b'\xff\xf3'),
    'wav': (b'RIFF',), 'm4a': (b'\x00\x00',), 'aac': (b'\xff\xf1', b'\xff\xf9'),
    'ogg': (b'OggS',), 'pdf': (b'%PDF-',), 'svg': (), 'txt': (), 'md': ()}
TYPES = {'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp','gif':'image/gif',
         'mp4':'video/mp4','mov':'video/quicktime','webm':'video/webm','mp3':'audio/mpeg','wav':'audio/wav',
         'm4a':'audio/mp4','aac':'audio/aac','ogg':'audio/ogg','pdf':'application/pdf',
         'svg':'image/svg+xml','txt':'text/plain','md':'text/plain'}
# Plain-language label for a creator-facing "not a valid ..." skip reason; no internal wording.
CATEGORY = {'png':'image','jpg':'image','jpeg':'image','webp':'image','gif':'image',
            'mp4':'video','mov':'video','webm':'video','mp3':'audio file','wav':'audio file',
            'm4a':'audio file','aac':'audio file','ogg':'audio file','pdf':'PDF',
            'svg':'SVG image','txt':'text file','md':'text file'}
# Staged after the uploads, so it wins a name clash and the note file stays true.
FRAME_NAME = 'pinned-frame.png'
ZIP_CHUNK = 1 << 16


def _sanitize_name(name):
    return re.sub(r'[^A-Za-z0-9._-]', '_', Path(name.replace('\\', '/')).name).lstrip('.') or 'file'


def svg_problem(data):
    """Why `data` is not an acceptable SVG, or None. A DOCTYPE or entity
    declaration is refused before parsing: entities are how an XML bomb
    expands, and real logos and icons never declare them."""
    try:
        text = data.decode('utf-8-sig')
    except UnicodeError:
        return 'an SVG must be UTF-8'
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)', text, re.I):
        return 'an SVG that declares XML entities is refused'
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return 'not a well-formed SVG'
    if root.tag not in ('svg', '{http://www.w3.org/2000/svg}svg'):
        return 'not an SVG'
    return None


def _validate_content(ctype, data, ext):
    """Raises ValueError if `data` (already known to have extension `ext`) doesn't
    actually look like `ctype`. Shared by a single upload and each zip member."""
    if ctype.split(';', 1)[0].strip().lower() != TYPES[ext]:
        raise ValueError('Content-Type does not match attachment extension')
    if ext in ('txt', 'md'):
        try:
            data.decode('utf-8')
        except UnicodeError:
            raise ValueError('text attachment must be UTF-8') from None
    elif ext == 'svg':
        problem = svg_problem(data)
        if problem:
            raise ValueError(problem)
    elif not any(data.startswith(x) for x in MAGIC[ext]):
        raise ValueError('attachment magic bytes do not match extension')
    if ext in ('webp', 'wav') and data[8:12] != (b'WEBP' if ext == 'webp' else b'WAVE'):
        raise ValueError('attachment magic bytes do not match extension')
    if ext in ('mp4', 'mov', 'm4a') and data[4:8] != b'ftyp':
        raise ValueError('attachment magic bytes do not match extension')


class Attachments:
    def __init__(self, editor, max_file, max_files, max_message, zip_max_bytes, zip_max_members,
                 zip_max_unpacked, start_video_max_files, start_video_max_message):
        self.editor = editor
        self.max_file, self.max_files, self.max_message = max_file, max_files, max_message
        self.zip_max_bytes, self.zip_max_members, self.zip_max_unpacked = (
            zip_max_bytes, zip_max_members, zip_max_unpacked)
        self.start_video_max_files, self.start_video_max_message = start_video_max_files, start_video_max_message
        self.root = Path(editor.state_dir) / 'attachments'
        self.root.mkdir(parents=True, exist_ok=True)

    def upload(self, video, name, ctype, data, allow_oversize=False):
        self.editor.project.video(video)
        self.expire()
        if not allow_oversize and len(data) > self.max_file:
            raise ValueError('attachment exceeds file size limit')
        name = _sanitize_name(name)
        ext = name.rsplit('.', 1)[-1].lower()
        if ext not in MAGIC:
            raise ValueError('unsupported attachment type')
        _validate_content(ctype, data, ext)
        return self._write(video, name, ext, data)

    def upload_zip(self, video, name, data):
        """Unpacks a zip into ordinary attachments, one per supported member,
        applying the same per-type validation a single upload gets. An unsafe
        member (an absolute or `..` path, a symlink, or an encrypted entry) or
        exceeding a limit refuses the whole zip and writes nothing; an
        unsupported or invalid member is simply skipped and listed. Nothing is
        written to disk until every member has been scanned, so a rejection
        never leaves a partial set of attachments behind."""
        self.editor.project.video(video)
        self.expire()
        if len(data) > self.zip_max_bytes:
            raise ValueError('zip upload exceeds the size limit')
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            raise ValueError('not a valid zip file') from None
        kept, skipped, total_unpacked = [], [], 0
        for info in zf.infolist():
            raw = info.filename.replace('\\', '/')
            parts = raw.split('/')
            basename = parts[-1]
            if info.is_dir() or not basename or basename.startswith('.') or '__MACOSX' in parts[:-1]:
                continue
            if raw.startswith('/') or '..' in parts:
                raise ValueError(f'zip member has an unsafe path: {basename}')
            if stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF):
                raise ValueError(f'zip member is a symlink: {basename}')
            if info.flag_bits & 0x1:
                raise ValueError(f'zip member is encrypted: {basename}')
            clean = _sanitize_name(basename)
            ext = clean.rsplit('.', 1)[-1].lower()
            if ext not in MAGIC:
                skipped.append((basename, 'not a supported type'))
                continue
            content = self._unpack_member(zf, info, self.zip_max_unpacked - total_unpacked, basename)
            total_unpacked += len(content)
            try:
                _validate_content(TYPES[ext], content, ext)
            except ValueError:
                skipped.append((basename, f'not a valid {CATEGORY[ext]}'))
                continue
            if len(kept) >= self.zip_max_members:
                raise ValueError(f'zip has more than {self.zip_max_members} supported files')
            kept.append((clean, ext, content))
        attachments = [self._write(video, clean, ext, content) for clean, ext, content in kept]
        return {'attachments': attachments, 'skipped': [{'name': n, 'reason': r} for n, r in skipped]}

    def _unpack_member(self, zf, info, remaining, basename):
        """Decompresses one member in chunks, checked against the per-file and
        remaining total-unpacked budgets as bytes actually come out -- never
        against the (attacker-controlled) size the zip header declares. A
        member whose declared size understates its real, decompressed content
        fails zipfile's own CRC check once enough of it has been read; that
        surfaces here as BadZipFile, not a silent pass-through of the lie."""
        buf = bytearray()
        try:
            with zf.open(info) as fh:
                while True:
                    chunk = fh.read(ZIP_CHUNK)
                    if not chunk:
                        break
                    buf += chunk
                    if len(buf) > self.max_file:
                        raise ValueError('a file in the zip exceeds the attachment size limit')
                    if len(buf) > remaining:
                        raise ValueError('the zip exceeds the total unpacked size limit')
        # A damaged stream raises zlib.error or EOFError, an unsupported method
        # NotImplementedError; none of them is BadZipFile, and each must stay a 400.
        except (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError) as exc:
            raise ValueError(f'{basename} is corrupt or its size is wrong') from exc
        return bytes(buf)

    def _write(self, video, name, ext, data):
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

    def validate(self, video, ids, max_files=None, max_message=None):
        max_files = self.max_files if max_files is None else max_files
        max_message = self.max_message if max_message is None else max_message
        if not isinstance(ids, list) or len(ids) > max_files or len(ids) != len(set(ids)):
            raise ValueError('too many or duplicate attachments')
        records = [self.get(ident, video)[0] for ident in ids]
        if sum(x['size'] for x in records) > max_message:
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

    def stage(self, note, frame=None, force=False):
        """The note's attachments, plus its pinned frame PNG as FRAME_NAME, in one
        directory for the runner to mount at /attachments; None if there is
        nothing to put there and `force` wasn't asked for the directory anyway
        (NoteStore._submit does, when the video has a source video ready to
        stage under it, even though the note itself carries no attachments or
        frame)."""
        records = note.get('attachments') or []
        if not records and not frame and not force:
            return None
        path = self.editor.notes.session_dir(note['video']) / ('attachments-' + note['id'])
        path.mkdir(exist_ok=True)
        for record in records:
            source = self.get(record['id'], note['video'])[1]
            shutil.copyfile(source, path / record['name'])
        if frame:
            shutil.copyfile(frame, path / FRAME_NAME)
        return str(path)

    def uploaded_for(self, video):
        """Every currently-existing (not yet expired) attachment id uploaded
        against `video`, oldest first -- for a caller like
        Library.send_capability that needs to recover ids a browser uploaded
        in an earlier step but didn't resend, without keeping its own index."""
        out = []
        for path in self.root.glob('*/meta.json'):
            try:
                meta = json.loads(path.read_text())
            except (ValueError, KeyError):
                continue
            if meta.get('video') == video:
                out.append((meta['created'], meta['id']))
        return [ident for _, ident in sorted(out)]

    def expire(self):
        used = {x['id'] for n in self.editor.notes.list(refresh=False) for x in n.get('attachments', [])}
        for path in self.root.glob('*/meta.json'):
            try:
                meta = json.loads(path.read_text())
                if meta['id'] not in used and time.time() - meta['created'] >= 86400:
                    shutil.rmtree(path.parent)
            except (ValueError, KeyError):
                continue
        # Per-note staging directories made by stage(): nothing else ever removes them,
        # and NoteStore._submit now makes one for nearly every note on a video with a
        # ready source (force=True), not just the ones that carry attachments or a frame.
        # Swept by age, the same as the attachment blobs above -- not by whether the note
        # that made it is still in flight, so a submission left inspectable for debugging
        # survives at least a day.
        sessions_root = Path(self.editor.notes.dir).parent / 'sessions'
        for path in sessions_root.glob('*/attachments-*'):
            try:
                if time.time() - path.stat().st_mtime >= 86400:
                    shutil.rmtree(path)
            except OSError:
                continue
