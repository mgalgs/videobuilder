"""A capability's `source`: the post or page it came from (schema.Source),
shown as a Source link on its card and carried in the index JSON; a
community capability added from a link carries the same shape."""
import unittest
from dataclasses import replace
from unittest import mock

from videobuilder import capabilities, community
from videobuilder.capabilities import registry
from videobuilder.capabilities.schema import Source

POST = 'https://x.com/someone/status/1'
REPO = 'https://github.com/someone/repo'


class Record(unittest.TestCase):
    def test_a_source_needs_an_http_link_and_a_credit(self):
        self.assertEqual(Source(POST, '@someone').as_json(), {'url': POST, 'credit': '@someone'})
        self.assertEqual(Source(POST, '@someone', upstream=REPO, upstream_credit='someone/repo').as_json(),
                         {'url': POST, 'credit': '@someone', 'upstream': REPO, 'upstream_credit': 'someone/repo'})
        for bad in (dict(url='x.com/1'), dict(url='ftp://x.com/1'), dict(credit=''), dict(credit=' @a'),
                    dict(upstream=REPO), dict(upstream_credit='repo'), dict(upstream='nope', upstream_credit='r')):
            with self.subTest(**bad), self.assertRaises(ValueError):
                Source(**{'url': POST, 'credit': '@someone', **bad})

    def test_a_record_takes_only_a_source(self):
        t = registry.get('ease-out-back')
        self.assertIsNone(t.source)                    # most capabilities have none
        with self.assertRaises(ValueError):
            replace(t, source={'url': POST, 'credit': '@someone'})


class Shown(unittest.TestCase):
    def test_the_link_shows_the_credit_and_the_upstream_when_there_is_one(self):
        self.assertEqual(capabilities.source_html(None), '')
        one = capabilities.source_html(Source(POST, '@some<one>'))
        self.assertIn(f'Source: <a href="{POST}" target="_blank" rel="noopener noreferrer">@some&lt;one&gt;</a>', one)
        self.assertNotIn('built on', one)
        two = capabilities.source_html(Source(POST, '@someone', upstream=REPO, upstream_credit='someone/repo'))
        self.assertIn(f'built on <a href="{REPO}" target="_blank" rel="noopener noreferrer">someone/repo</a>', two)
        self.assertEqual(capabilities.source_html({'url': POST, 'credit': '@someone'}),
                         capabilities.source_html(Source(POST, '@someone')))

    def test_a_card_with_no_source_is_unchanged(self):
        plain = capabilities._card_html('a', 'A', 'Line.', 'thumb')
        self.assertTrue(plain.startswith('<button class="card"'))
        sourced = capabilities._card_html('a', 'A', 'Line.', 'thumb', Source(POST, '@someone'))
        self.assertEqual(sourced, f'<div class="sourced-card">{plain}{capabilities.source_html(Source(POST, "@someone"))}</div>')

    def test_a_sourced_record_shows_its_link_on_the_page_and_in_the_index(self):
        real = registry.get
        sourced = replace(real('eased-entrances'), source=Source(POST, '@someone'))
        cards = tuple(sourced if t.id == 'eased-entrances' else t for t in capabilities.cards())
        with mock.patch.object(capabilities, 'cards', lambda: cards):
            page = capabilities.page_html(None, '0').decode()
        card = page[page.index('<div class="sourced-card">'):]
        self.assertTrue(card.startswith('<div class="sourced-card"><button class="card" type="button" '
                                        'data-card="eased-entrances">'))
        self.assertIn(f'href="{POST}"', card[:card.index('</div>')])
        self.assertEqual(page.count('class="sourced-card"'), 1)
        self.assertEqual(registry._data(sourced)['source'], {'url': POST, 'credit': '@someone'})
        self.assertNotIn('source', registry._data(real('ease-out-back')))

    def test_a_community_card_shows_its_source(self):
        entry = {'slug': 'c-20260101-abc123', 'id': 'zoom-reveal', 'family': None, 'category': 'Motion',
                 'title': 'Zoom reveal', 'card': 'Zooms.', 'description': 'Zooms.', 'prompts': ('a', 'b', 'c'),
                 'available': False, 'pending_update': False, 'source': {'url': POST, 'credit': '@someone'}}
        page = capabilities.page_html(None, '0', community={'published': [entry], 'drafts': [], 'can_submit': False,
                                                          'is_admin': False, 'fetch': False}).decode()
        card = page[page.index('<div class="community-card">'):]
        card = card[:card.index('</div>')]
        self.assertIn(f'Source: <a href="{POST}"', card)


class Community(unittest.TestCase):
    def test_post_source_credits_the_handle_else_the_title_else_the_host(self):
        self.assertEqual(community.post_source({'url': POST, 'handle': 'someone', 'text': 'hi'}, POST),
                         {'url': POST, 'credit': '@someone'})
        page = {'kind': 'page', 'url': 'https://blog.example/zoom', 'title': 'Zoom reveal', 'text': ''}
        self.assertEqual(community.post_source(page, 'https://blog.example/zoom?utm=1'),
                         {'url': 'https://blog.example/zoom', 'credit': 'Zoom reveal'})
        self.assertEqual(community.post_source(None, 'https://blog.example/zoom'),
                         {'url': 'https://blog.example/zoom', 'credit': 'blog.example'})
        self.assertIsNone(community.post_source(None, 'not a link'))
        self.assertIsNone(community.post_source(None, None))


def _index_sources():
    return {t['id']: t['source'] for f in registry.index_data()['families'] for g in f['groups']
            for t in g['capabilities'] if 'source' in t}


if __name__ == '__main__':
    unittest.main()
