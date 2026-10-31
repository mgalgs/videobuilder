"""POST /api/videos/suggest-name: the New video page's Suggest-a-name
button (suggest.py's Suggest.suggest_name, routed in handler_library.py)."""
import os
import unittest
from unittest import mock

from tests.fake_suggest import FakeSuggest
from tests.fixtures import LibraryFixture


AUDIO = b'ID3' + b'song' * 20


class NoModelConfigured(LibraryFixture, unittest.TestCase):
    def test_suggest_name_404s_without_a_model(self):
        code, err = self.request('/api/videos/suggest-name', {'idea': 'A storm film.'})
        self.assertEqual(code, 404)


class SuggestName(LibraryFixture, unittest.TestCase):
    def library_kwargs(self):
        return {'suggest_url': self.fake.base}

    def setUp(self):
        self.fake = FakeSuggest()
        self.addCleanup(self.fake.close)
        patcher = mock.patch.dict(os.environ, {'VIDEOBUILDER_SUGGEST_KEY': 'test-key'})
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()

    def test_suggests_a_name_from_the_idea(self):
        self.fake.answer = {'name': 'lighthouse-storm'}
        code, body = self.request('/api/videos/suggest-name', {'idea': 'A lighthouse keeper riding out a storm.'})
        self.assertEqual(code, 200, body)
        self.assertEqual(body, {'name': 'lighthouse-storm'})

    def test_nothing_to_go_on_skips_the_model_entirely(self):
        code, body = self.request('/api/videos/suggest-name', {'idea': ''})
        self.assertEqual((code, body), (200, {'name': None}))
        self.assertEqual(self.fake.requests, [])

    def test_file_names_and_listening_notes_reach_the_model(self):
        record = self.library.staging.upload('storm-theme.mp3', 'audio/mpeg', AUDIO, None)
        _, path = self.library.staging.get(record['id'])
        from videobuilder import listen
        self.library.listener.cache_dir.mkdir(exist_ok=True)
        key = listen.cache_key(path.read_bytes())
        (self.library.listener.cache_dir / (key + '.md')).write_text('## Overall\nTense, building strings.')
        self.fake.answer = {'name': 'storm-theme'}
        code, body = self.request('/api/videos/suggest-name', {
            'idea': 'A storm film.', 'attachments': [record['id']]})
        self.assertEqual(code, 200, body)
        user_text = self.fake.requests[-1]['body']['messages'][-1]['content']
        self.assertIn('storm-theme.mp3', user_text)
        self.assertIn('Tense, building strings', user_text)

    def test_a_stale_attachment_id_is_simply_ignored(self):
        self.fake.answer = {'name': 'a-storm'}
        code, body = self.request('/api/videos/suggest-name', {
            'idea': 'A storm film.', 'attachments': ['0' * 32]})
        self.assertEqual(code, 200, body)
        self.assertEqual(body, {'name': 'a-storm'})

    def test_a_failing_model_answers_name_none_not_an_error(self):
        self.fake.status = 500
        code, body = self.request('/api/videos/suggest-name', {'idea': 'A storm film, with three characters.'})
        self.assertEqual((code, body), (200, {'name': None}))

    def test_repeat_ask_is_cached_not_re_requested(self):
        self.fake.answer = {'name': 'storm'}
        self.request('/api/videos/suggest-name', {'idea': 'A storm film.'})
        self.request('/api/videos/suggest-name', {'idea': 'A storm film.'})
        self.assertEqual(len(self.fake.requests), 1)

    def test_idea_must_be_a_string(self):
        code, err = self.request('/api/videos/suggest-name', {'idea': 123})
        self.assertEqual(code, 400)

    def test_attachments_must_be_a_list_of_strings(self):
        code, err = self.request('/api/videos/suggest-name', {'idea': 'hi', 'attachments': [1, 2]})
        self.assertEqual(code, 400)


if __name__ == '__main__':
    unittest.main()
