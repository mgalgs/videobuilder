"""Zip-upload unpacking: safety, limits and the per-type validation every
member gets, on top of the existing single-upload tests in test_director.py."""
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from videobuilder.editor import Editor
from tests import fixtures
from tests.test_project import TempProject

PNG = b'\x89PNG\r\n\x1a\n' + b'0123456789'


def _zip_bytes(entries):
    """`entries`: [(name, data) or (name, data, {flag_bits, external_attr})]."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for entry in entries:
            name, data = entry[0], entry[1]
            extra = entry[2] if len(entry) > 2 else {}
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            for key, value in extra.items():
                setattr(info, key, value)
            zf.writestr(info, data)
    return buf.getvalue()


def _encrypted_zip(entries, encrypted_index):
    """Flips the encryption bit (general-purpose flag bit 0) of the given
    entry's *central directory* record -- what ZipFile.infolist() actually
    reads -- without touching the (unencrypted) compressed bytes, since the
    check only needs to see the flag to refuse the member."""
    data = bytearray(_zip_bytes(entries))
    offsets = [m.start() for m in re.finditer(rb'PK\x01\x02', bytes(data))]
    flag_offset = offsets[encrypted_index] + 8
    flag = struct.unpack_from('<H', data, flag_offset)[0] | 0x1
    struct.pack_into('<H', data, flag_offset, flag)
    return bytes(data)


def _lying_size_zip(name, real_data, fake_size=5):
    """A zip whose one member's declared uncompressed size understates what
    it actually decompresses to -- the local header and the central
    directory record both lie, the compressed bytes (and their real CRC)
    don't."""
    data = bytearray(_zip_bytes([(name, real_data)]))
    local = data.find(b'PK\x03\x04')
    struct.pack_into('<I', data, local + 22, fake_size)
    central = data.find(b'PK\x01\x02')
    struct.pack_into('<I', data, central + 24, fake_size)
    return bytes(data)


class ZipUpload(fixtures.API):
    """Direct, Python-level tests against Attachments.upload_zip."""

    def test_a_dozen_images_and_one_unsupported_file(self):
        entries = [(f'{i}.png', PNG) for i in range(12)] + [('notes.psd', b'not an image')]
        result = self.editor.attachments.upload_zip('promo/film', 'assets.zip', _zip_bytes(entries))
        self.assertEqual(len(result['attachments']), 12)
        self.assertEqual(result['skipped'], [{'name': 'notes.psd', 'reason': 'not a supported type'}])
        names = {a['name'] for a in result['attachments']}
        self.assertEqual(names, {f'{i}.png' for i in range(12)})

    def test_directories_dotfiles_and_macosx_are_skipped_silently(self):
        entries = [('photos/', b''), ('.DS_Store', b'junk'),
                  ('__MACOSX/._keep.png', PNG), ('keep.png', PNG)]
        result = self.editor.attachments.upload_zip('promo/film', 'assets.zip', _zip_bytes(entries))
        self.assertEqual([a['name'] for a in result['attachments']], ['keep.png'])
        self.assertEqual(result['skipped'], [])

    def test_nested_zip_is_skipped_and_listed(self):
        inner = _zip_bytes([('a.png', PNG)])
        result = self.editor.attachments.upload_zip('promo/film', 'assets.zip',
                                                     _zip_bytes([('inner.zip', inner), ('a.png', PNG)]))
        self.assertEqual([a['name'] for a in result['attachments']], ['a.png'])
        self.assertEqual(result['skipped'], [{'name': 'inner.zip', 'reason': 'not a supported type'}])

    def test_corrupt_content_for_the_extension_is_skipped_not_rejected(self):
        result = self.editor.attachments.upload_zip(
            'promo/film', 'assets.zip', _zip_bytes([('bad.png', b'not actually a png'), ('good.png', PNG)]))
        self.assertEqual([a['name'] for a in result['attachments']], ['good.png'])
        self.assertEqual(len(result['skipped']), 1)
        self.assertEqual(result['skipped'][0]['name'], 'bad.png')

    def _refused_with_no_attachments_written(self, data, message_part):
        before = set(self.editor.attachments.root.iterdir())
        with self.assertRaises(ValueError) as caught:
            self.editor.attachments.upload_zip('promo/film', 'assets.zip', data)
        self.assertIn(message_part, str(caught.exception))
        self.assertEqual(set(self.editor.attachments.root.iterdir()), before)

    def test_absolute_member_path_is_refused(self):
        self._refused_with_no_attachments_written(
            _zip_bytes([('good.png', PNG), ('/etc/evil.png', PNG)]), 'unsafe path')

    def test_traversal_member_path_is_refused(self):
        self._refused_with_no_attachments_written(
            _zip_bytes([('good.png', PNG), ('../evil.png', PNG)]), 'unsafe path')

    def test_symlink_member_is_refused(self):
        entries = [('good.png', PNG), ('link.png', b'target.png', {
            'external_attr': (stat.S_IFLNK | 0o777) << 16})]
        self._refused_with_no_attachments_written(_zip_bytes(entries), 'symlink')

    def test_encrypted_member_is_refused(self):
        entries = [('good.png', PNG), ('secret.png', PNG)]
        self._refused_with_no_attachments_written(_encrypted_zip(entries, encrypted_index=1), 'encrypted')

    def test_zip_upload_itself_over_the_size_limit_is_refused_before_parsing(self):
        self.editor.attachments.zip_max_bytes = 10
        self._refused_with_no_attachments_written(_zip_bytes([('a.png', PNG)]), 'size limit')

    def test_more_supported_members_than_the_cap_refuses_the_whole_zip(self):
        self.editor.attachments.zip_max_members = 2
        entries = [(f'{i}.png', PNG) for i in range(3)]
        self._refused_with_no_attachments_written(_zip_bytes(entries), 'more than 2')

    def test_a_member_over_the_per_file_limit_refuses_the_whole_zip(self):
        self.editor.attachments.max_file = 10
        self._refused_with_no_attachments_written(_zip_bytes([('big.png', PNG)]), 'attachment size limit')

    def test_total_decompressed_bytes_over_the_cap_refuses_the_whole_zip(self):
        self.editor.attachments.zip_max_unpacked = 1000
        # Real, honestly-declared content: highly compressible, so the zip itself stays tiny
        # while the true unpacked size is counted as it streams out, not trusted from the header.
        entries = [('huge.txt', b'0' * 100000)]
        self._refused_with_no_attachments_written(_zip_bytes(entries), 'total unpacked size limit')

    def test_bomb_whose_header_understates_its_size_is_rejected_cleanly(self):
        real = PNG + b'\x00' * 500000
        self._refused_with_no_attachments_written(_lying_size_zip('bomb.png', real), 'corrupt')

    def test_a_damaged_deflate_stream_is_refused_cleanly(self):
        data = bytearray(_zip_bytes([('a.png', PNG * 50)]))
        start = data.find(b'PK\x03\x04') + 30 + len('a.png')
        data[start:start + 8] = b'\xff' * 8
        self._refused_with_no_attachments_written(bytes(data), 'corrupt')

    def test_not_a_zip_file_at_all(self):
        self._refused_with_no_attachments_written(b'this is not a zip file', 'not a valid zip')

    def test_duplicate_basenames_become_distinct_attachments_disambiguated_later(self):
        entries = [('a/photo.png', PNG), ('b/photo.png', PNG)]
        result = self.editor.attachments.upload_zip('promo/film', 'assets.zip', _zip_bytes(entries))
        ids = [a['id'] for a in result['attachments']]
        self.assertEqual([a['name'] for a in result['attachments']], ['photo.png', 'photo.png'])
        validated = self.editor.attachments.validate('promo/film', ids)
        self.assertEqual(len({v['name'] for v in validated}), 2)


class ZipUploadOverHTTP(fixtures.API):
    """The POST /api/attachments route dispatching to a zip by filename."""

    def _upload(self, data, name, ctype='application/octet-stream'):
        from urllib.parse import quote
        req = urllib.request.Request(self.base + '/api/attachments?video=promo/film&name=' + quote(name),
                                     data=data, method='POST', headers={'Content-Type': ctype})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read())

    def test_zip_upload_returns_attachments_and_skipped_list(self):
        entries = [('a.png', PNG), ('b.png', PNG), ('bad.psd', b'nope')]
        code, body = self._upload(_zip_bytes(entries), 'assets.zip', 'application/zip')
        self.assertEqual(code, 201, body)
        self.assertEqual(len(body['attachments']), 2)
        self.assertEqual(body['skipped'], [{'name': 'bad.psd', 'reason': 'not a supported type'}])

    def test_zip_over_content_length_limit_is_413(self):
        self.editor.attachments.zip_max_bytes = 10
        code, body = self._upload(_zip_bytes([('a.png', PNG)]), 'assets.zip')
        self.assertEqual(code, 413, body)

    def test_start_video_accepts_more_attachments_than_an_ordinary_note(self):
        ids = []
        for i in range(15):
            code, record = self._upload(PNG, f'{i}.png', 'image/png')
            self.assertEqual(code, 201, record)
            ids.append(record['id'])
        # The regular per-note cap (10) still refuses this many on an ordinary note.
        code, err = self.post('/api/notes', {'video': 'promo/film', 'text': 'hi', 'attachments': ids})
        self.assertEqual(code, 400, err)
        # The first note from New video gets the larger start_video budget (default 50).
        code, note = self.post('/api/videos/first-note', {'description': 'Launch brief', 'attachments': ids})
        self.assertEqual(code, 200, note)
        self.assertEqual(len(note['attachments']), 15)


SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'


class SvgUpload(ZipUploadOverHTTP):
    def test_an_svg_is_kept_and_served_as_a_download_that_loads_nothing(self):
        code, record = self._upload(SVG, 'logo.svg', 'image/svg+xml')
        self.assertEqual(code, 201, record)
        self.assertEqual(record['type'], 'image/svg+xml')
        with urllib.request.urlopen(self.base + '/api/attachments/' + record['id']) as response:
            self.assertEqual(response.read(), SVG)
            self.assertTrue(response.headers['Content-Disposition'].startswith('attachment'))
            csp = response.headers['Content-Security-Policy']
            self.assertIn('sandbox', csp)
            self.assertIn("default-src 'none'", csp)

    def test_a_bad_svg_is_refused(self):
        cases = {
            'entities': (b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "aaaa">]>'
                         b'<svg xmlns="http://www.w3.org/2000/svg">&a;</svg>', 'declares XML entities'),
            'not svg': (b'<html><body>hi</body></html>', 'not an SVG'),
            'broken': (b'<svg xmlns="http://www.w3.org/2000/svg"><g></svg>', 'not a well-formed SVG'),
            'not utf-8': (b'<svg>\xff</svg>', 'must be UTF-8'),
        }
        for name, (data, message) in cases.items():
            with self.subTest(name):
                code, body = self._upload(data, f'{name.replace(" ", "-")}.svg', 'image/svg+xml')
                self.assertEqual(code, 400, body)
                self.assertIn(message, body['error'])

    def test_a_zip_keeps_its_svgs(self):
        result = self.editor.attachments.upload_zip('promo/film', 'logos.zip', _zip_bytes([('logo.svg', SVG)]))
        self.assertEqual([a['name'] for a in result['attachments']], ['logo.svg'])


class ZipConfigKeys(TempProject):
    def _editor(self, state_dir):
        editor = Editor(self.root, state_dir=state_dir, unsandboxed_previews=True, auto_land=False)
        self.addCleanup(editor.pool.close)
        self.addCleanup(editor.renders.close)
        return editor

    def test_defaults(self):
        editor = self._editor('state-defaults')
        self.assertEqual(editor.attachments.zip_max_bytes, 200 * 1048576)
        self.assertEqual(editor.attachments.zip_max_members, 50)
        self.assertEqual(editor.attachments.zip_max_unpacked, 300 * 1048576)
        self.assertEqual(editor.attachments.start_video_max_files, 50)
        self.assertEqual(editor.attachments.start_video_max_message, 300 * 1048576)

    def test_configured_in_videobuilder_toml(self):
        (self.root / 'videobuilder.toml').write_text(
            '[editor]\n'
            'attachment_zip_max_bytes = 1\n'
            'attachment_zip_max_members = 2\n'
            'attachment_zip_max_unpacked_bytes = 3\n'
            'start_video_attachment_max_files = 4\n'
            'start_video_attachment_max_message = 5\n')
        editor = self._editor('state-configured')
        self.assertEqual(editor.attachments.zip_max_bytes, 1 * 1048576)
        self.assertEqual(editor.attachments.zip_max_members, 2)
        self.assertEqual(editor.attachments.zip_max_unpacked, 3 * 1048576)
        self.assertEqual(editor.attachments.start_video_max_files, 4)
        self.assertEqual(editor.attachments.start_video_max_message, 5 * 1048576)


class StagedDirectoryExpiry(fixtures.API):
    """Attachments.stage() makes a per-note `attachments-<id>` directory under
    the video's session dir; nothing used to ever remove it, and NoteStore._submit
    now makes one for nearly every note on a video with a ready source (force=True),
    not just ones with their own attachments or a pinned frame. expire() sweeps
    these the same way it already sweeps the attachment blobs under self.root: by
    age, not by whether the note that made it is done."""

    def test_old_staged_directory_is_swept_fresh_one_is_not(self):
        old_note = self.post('/api/notes', {'video': 'promo/film', 'text': 'Old'})[1]
        old_dir = Path(self.editor.attachments.stage(old_note, force=True))
        self.assertTrue(old_dir.is_dir())
        stale = time.time() - 90000
        os.utime(old_dir, (stale, stale))

        fresh_note = self.post('/api/notes', {'video': 'promo/film', 'text': 'Fresh'})[1]
        fresh_dir = Path(self.editor.attachments.stage(fresh_note, force=True))

        self.editor.attachments.expire()
        self.assertFalse(old_dir.exists())
        self.assertTrue(fresh_dir.is_dir())
