"""Recognising a library link in a note's text -- see video_refs.extract and
library.video_name_in_path. The actual resolve-and-stage path (video_refs.stage)
is covered end to end in tests/test_library.py, against a real Library with two
videos."""
import unittest

from videobuilder import video_refs
from videobuilder.library import video_name_in_path


class _FakeLibrary:
    def __init__(self, hosts):
        self.allowed_hosts = set(hosts)


class VideoNameInPath(unittest.TestCase):
    def test_bare_video_page(self):
        self.assertEqual(video_name_in_path('/v/launch'), 'launch')

    def test_two_part_name(self):
        self.assertEqual(video_name_in_path('/v/acme/launch'), 'acme/launch')

    def test_two_part_name_with_api_subroute(self):
        self.assertEqual(video_name_in_path('/v/acme/launch/api/notes'), 'acme/launch')

    def test_trailing_slash(self):
        self.assertEqual(video_name_in_path('/v/acme/launch/'), 'acme/launch')

    def test_tuning_and_director_subroutes(self):
        self.assertEqual(video_name_in_path('/v/acme/launch/tuning.html'), 'acme/launch')
        self.assertEqual(video_name_in_path('/v/acme/launch/director.js'), 'acme/launch')

    def test_percent_encoded_name_is_not_valid(self):
        # Checked straight off the raw path, like the router itself (handler_library._handle):
        # valid_name's charset excludes '%', so this is never a name, encoded or not.
        self.assertIsNone(video_name_in_path('/v/a%63me/launch'))

    def test_not_a_video_path(self):
        self.assertIsNone(video_name_in_path('/git/acme/launch.git'))
        self.assertIsNone(video_name_in_path('/api/usage'))
        self.assertIsNone(video_name_in_path('/'))

    def test_invalid_name_shape(self):
        self.assertIsNone(video_name_in_path('/v/..'))
        self.assertIsNone(video_name_in_path('/v/a/b/c'))


class Extract(unittest.TestCase):
    def setUp(self):
        self.library = _FakeLibrary(['editor.example', '127.0.0.1'])

    def test_no_library_means_nothing_is_ever_a_reference(self):
        links = ['https://editor.example/v/launch']
        self.assertEqual(video_refs.extract(links, None), ([], links))

    def test_a_library_link_is_pulled_out(self):
        refs, rest = video_refs.extract(['https://editor.example/v/launch'], self.library)
        self.assertEqual((refs, rest), (['launch'], []))

    def test_mixing_a_library_link_and_a_public_link_splits_them(self):
        refs, rest = video_refs.extract(
            ['https://editor.example/v/launch', 'https://site.example/about'], self.library)
        self.assertEqual((refs, rest), (['launch'], ['https://site.example/about']))

    def test_wrong_host_is_left_as_an_ordinary_link(self):
        refs, rest = video_refs.extract(['https://other.example/v/launch'], self.library)
        self.assertEqual((refs, rest), ([], ['https://other.example/v/launch']))

    def test_non_http_scheme_is_never_a_reference(self):
        refs, rest = video_refs.extract(['ftp://editor.example/v/launch'], self.library)
        self.assertEqual((refs, rest), ([], ['ftp://editor.example/v/launch']))

    def test_host_matching_is_case_and_trailing_dot_insensitive(self):
        refs, _ = video_refs.extract(['https://EDITOR.EXAMPLE./v/launch'], self.library)
        self.assertEqual(refs, ['launch'])

    def test_duplicates_keep_the_first_occurrence_only(self):
        refs, rest = video_refs.extract(
            ['https://editor.example/v/launch', 'https://editor.example/v/launch/api/notes'], self.library)
        self.assertEqual((refs, rest), (['launch'], []))

    def test_order_is_preserved_across_both_lists(self):
        links = ['https://site.example/a', 'https://editor.example/v/launch',
                'https://site.example/b', 'https://editor.example/v/acme/promo']
        refs, rest = video_refs.extract(links, self.library)
        self.assertEqual(refs, ['launch', 'acme/promo'])
        self.assertEqual(rest, ['https://site.example/a', 'https://site.example/b'])


if __name__ == '__main__':
    unittest.main()
