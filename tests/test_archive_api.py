"""HTTP-level tests for the two archive.org routes: GET /api/archive/search
and POST /api/sources/import. archive_org's own network calls are mocked at
the module level -- this sandbox has no network, and CI must not depend on
archive.org being reachable (see tests/test_archive_org.py for archive_org's
own unit tests, and tests/test_sources.py's ArchiveImport class for direct,
Python-level tests of Sources.import_archive_item)."""
import io
import shutil
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from videobuilder import archive_org
from tests import fixtures
from tests.test_sources import _join_imports

FFMPEG = shutil.which('ffmpeg') and shutil.which('ffprobe')


def _mp4(path, seconds=1, size='64x64'):
    subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=blue:s={size}:d={seconds}:r=10',
                    '-pix_fmt', 'yuv420p', str(path)], check=True, capture_output=True)


class _FakeDownload:
    def __init__(self, data):
        self.buf = io.BytesIO(data)
        self.closed = False

    def read(self, n):
        return self.buf.read(n)

    def close(self):
        self.closed = True


class Search(fixtures.API):
    def test_search_returns_results(self):
        results = [{'identifier': 'farm-safety-1955', 'title': 'Farm Safety', 'year': '1955', 'duration': 630.0,
                   'license': 'https://creativecommons.org/publicdomain/mark/1.0/', 'rights': None,
                   'thumbnail': 'https://archive.org/services/img/farm-safety-1955',
                   'details_url': 'https://archive.org/details/farm-safety-1955'}]
        with mock.patch('videobuilder.archive_org.search_films', return_value=results) as searched:
            data = self.get('/api/archive/search?q=farm+safety')
        self.assertEqual(data, {'results': results})
        searched.assert_called_once_with('farm safety')

    def test_empty_query_is_a_default_page_not_an_error(self):
        with mock.patch('videobuilder.archive_org.search_films', return_value=[]) as searched:
            data = self.get('/api/archive/search')
        self.assertEqual(data, {'results': []})
        searched.assert_called_once_with('')

    def test_upstream_failure_is_502(self):
        with mock.patch('videobuilder.archive_org.search_films',
                        side_effect=archive_org.ArchiveError('could not reach archive.org')):
            with self.assertRaises(urllib.error.HTTPError) as e:
                self.get('/api/archive/search?q=x')
            e.exception.close()
            self.assertEqual(e.exception.code, 502)


@unittest.skipUnless(FFMPEG, 'needs ffmpeg/ffprobe')
class Import(fixtures.API):
    def setUp(self):
        super().setUp()
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.clip = Path(self.scratch.name) / 'clip.mp4'
        _mp4(self.clip)

    def _item(self, **overrides):
        item = dict(identifier='farm-safety-1955', title='Farm Safety', creator='A. Studio', year='1955',
                   license='https://creativecommons.org/publicdomain/mark/1.0/', rights=None,
                   details_url='https://archive.org/details/farm-safety-1955', collection=['prelinger'],
                   mediatype='movies',
                   files=[{'name': 'farm-safety-1955.mp4', 'size': str(len(self.clip.read_bytes()))}])
        item.update(overrides)
        return item

    def _mocked_import(self, body, item=None):
        data = self.clip.read_bytes()
        with mock.patch('videobuilder.archive_org.get_metadata', return_value=item or self._item()), \
             mock.patch('videobuilder.archive_org.open_download',
                        return_value=(_FakeDownload(data), len(data), 'video/mp4')):
            code, record = self.post('/api/sources/import', body)
            _join_imports(self.editor.sources)
        return code, record

    def test_import_lands_as_a_source_with_license_and_credit(self):
        code, record = self._mocked_import({'video': 'promo/film', 'identifier': 'farm-safety-1955'})
        self.assertEqual(code, 202, record)
        self.assertEqual(record['name'], 'farm-safety')
        self.assertEqual(record['status'], 'importing')
        self.assertEqual(record['license'], 'https://creativecommons.org/publicdomain/mark/1.0/')
        self.assertEqual(record['credit']['title'], 'Farm Safety')
        sources = self.get('/api/sources?video=promo%2Ffilm')['sources']
        self.assertEqual([s['name'] for s in sources], ['farm-safety'])
        self.assertNotIn('status', sources[0])
        self.assertEqual(sources[0]['size'], len(self.clip.read_bytes()))
        self.assertEqual(sources[0]['credit']['title'], 'Farm Safety')

    def test_explicit_name_is_honoured(self):
        code, record = self._mocked_import({'video': 'promo/film', 'identifier': 'farm-safety-1955',
                                            'name': 'My Import'})
        self.assertEqual(code, 202, record)
        self.assertEqual(record['name'], 'my-import')

    def test_unknown_identifier_is_404(self):
        with mock.patch('videobuilder.archive_org.get_metadata',
                        side_effect=archive_org.NotFound('no such archive.org item')):
            code, result = self.post('/api/sources/import', {'video': 'promo/film', 'identifier': 'nope'})
        self.assertEqual(code, 404, result)

    def test_upstream_failure_is_502(self):
        with mock.patch('videobuilder.archive_org.get_metadata',
                        side_effect=archive_org.ArchiveError('could not reach archive.org')):
            code, result = self.post('/api/sources/import', {'video': 'promo/film', 'identifier': 'x'})
        self.assertEqual(code, 502, result)

    def test_no_derivative_fits_is_400_with_nothing_left(self):
        code, result = self._mocked_import({'video': 'promo/film', 'identifier': 'farm-safety-1955'},
                                           item=self._item(files=[]))
        self.assertEqual(code, 400, result)
        self.assertEqual(self.get('/api/sources?video=promo%2Ffilm')['sources'], [])

    def test_non_string_name_is_400(self):
        code, result = self._mocked_import({'video': 'promo/film', 'identifier': 'farm-safety-1955', 'name': 5})
        self.assertEqual(code, 400, result)

    def test_item_outside_prelinger_is_refused_with_nothing_left(self):
        code, result = self._mocked_import({'video': 'promo/film', 'identifier': 'some-upload'},
                                           item=self._item(identifier='some-upload', collection=['opensource']))
        self.assertEqual(code, 400, result)
        self.assertEqual(self.get('/api/sources?video=promo%2Ffilm')['sources'], [])


if __name__ == '__main__':
    unittest.main()
