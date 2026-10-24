"""The settings-card static assets (settings_card.js/css and its demo page)
are served like director.js/suggest.js. The component's own behaviour is
exercised by settings_card_test.html in a real browser (see the handoff);
this just covers the server-side wiring: the files are there, with real
narration settings (preview URLs included) behind them."""
import urllib.request

from tests import fixtures


class StaticAssets(fixtures.API):
    def test_js_css_and_test_page_are_served(self):
        with urllib.request.urlopen(self.base + '/settings_card.js') as r:
            self.assertEqual(r.headers.get_content_type(), 'text/javascript')
            js = r.read()
        self.assertIn(b'window.SettingsCard', js)
        with urllib.request.urlopen(self.base + '/settings_card.css') as r:
            self.assertEqual(r.headers.get_content_type(), 'text/css')
            self.assertIn(b'.sc-card', r.read())
        with urllib.request.urlopen(self.base + '/settings_card_test.html') as r:
            self.assertEqual(r.headers.get_content_type(), 'text/html')
            html = r.read()
        self.assertIn(b'settings_card.js', html)
        self.assertIn(b'api/suggest/catalog', html)

    def test_narrations_settings_in_the_catalog_carry_preview_urls(self):
        catalog = self.get('/api/suggest/catalog')
        narration = next(c for c in catalog['capabilities'] if c['id'] == 'narration')
        voice = next(s for s in narration['settings'] if s['id'] == 'voice')
        self.assertTrue(voice['options'])
        for option in voice['options']:
            self.assertTrue(option['preview'].startswith('api/narration/voice-sample?voice='))

    def test_a_capability_without_settings_has_no_settings_key(self):
        catalog = self.get('/api/suggest/catalog')
        plain = next(c for c in catalog['capabilities'] if c['id'] == 'seamless-loops')
        self.assertNotIn('settings', plain)


if __name__ == '__main__':
    import unittest
    unittest.main()
