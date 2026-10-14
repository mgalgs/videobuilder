"""The crawler: same-site scope, breadth-first order, the page cap, dedupe,
the skip rules and the time cap, against a local fixture site. The fixture
is reached only because these tests pass `allow_loopback=True`, the explicit
test-only switch guard.py documents; production code never does."""
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from videobuilder import gather


PAGES = {
    '/': '<html><head><title>Home</title></head><body><nav>Nav junk</nav>'
         '<p>Welcome home.</p><a href="/about">About</a> <a href="/contact">Contact</a>'
         '<a href="https://off-site.example/other">Off-site</a></body></html>',
    '/about': '<html><head><title>About</title></head><body><p>About us.</p>'
              '<a href="/">Home</a><a href="/team">Team</a></body></html>',
    '/contact': '<html><head><title>Contact</title></head><body><p>Contact us.</p>'
               '<a href="/login">Sign in</a></body></html>',
    '/team': '<html><head><title>Team</title></head><body><p>The team.</p>'
            '<a href="/alpha">Alpha</a><a href="/beta">Beta</a><a href="/gamma">Gamma</a>'
            '<a href="/delta">Delta</a><a href="/epsilon">Epsilon</a>'
            '<a href="/zeta">Zeta</a></body></html>',
    '/login': '<html><head><title>Sign in</title></head><body><p>Sign in here.</p></body></html>',
    '/alpha': '<html><title>Alpha</title><body>Alpha page.</body></html>',
    '/beta': '<html><title>Beta</title><body>Beta page.</body></html>',
    '/gamma': '<html><title>Gamma</title><body>Gamma page.</body></html>',
    '/delta': '<html><title>Delta</title><body>Delta page.</body></html>',
    '/epsilon': '<html><title>Epsilon</title><body>Epsilon page.</body></html>',
    '/zeta': '<html><title>Zeta</title><body>Zeta page.</body></html>',
    '/file.json': '{"not": "html"}',
}


class _Site(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/slow':
            time.sleep(3)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><title>Slow</title><body>late</body></html>')
            return
        if self.path == '/file.json':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(PAGES[self.path].encode())
            return
        body = PAGES.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


class GatherFixture(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(('127.0.0.1', 0), _Site)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.thread.join)
        self.addCleanup(self.server.shutdown)

    def url(self, path):
        return f'http://127.0.0.1:{self.port}{path}'


class Crawl(GatherFixture):
    def test_same_site_breadth_first_cap_and_dedupe(self):
        pages, errors = gather.crawl([self.url('/')], max_pages=4, allow_loopback=True, chromium=None)
        urls = [p['url'] for p in pages]
        self.assertEqual(len(urls), 4)
        self.assertEqual(len(set(urls)), 4)  # dedupe: no page visited twice
        # breadth-first: '/' first, then its direct links before anything deeper
        self.assertEqual(urls[0], self.url('/'))
        self.assertEqual(set(urls[1:3]), {self.url('/about'), self.url('/contact')})
        # off-site link never followed
        self.assertNotIn('off-site.example', ''.join(urls))
        self.assertTrue(all('off-site.example' not in u for u in urls))

    def test_login_like_pages_are_skipped(self):
        pages, errors = gather.crawl([self.url('/contact')], max_pages=10, allow_loopback=True, chromium=None)
        self.assertNotIn(self.url('/login'), [p['url'] for p in pages])
        self.assertTrue(any('login' in url for url, reason in errors))

    def test_non_html_is_skipped(self):
        pages, errors = gather.crawl([self.url('/file.json')], max_pages=10, allow_loopback=True, chromium=None)
        self.assertEqual(pages, [])
        self.assertTrue(any('not an HTML page' in reason for _, reason in errors))

    def test_page_cap_of_ten_by_default(self):
        pages, errors = gather.crawl([self.url('/')], allow_loopback=True, chromium=None)
        self.assertLessEqual(len(pages), 10)

    def test_text_and_title_are_captured_without_boilerplate(self):
        pages, errors = gather.crawl([self.url('/')], max_pages=1, allow_loopback=True, chromium=None)
        self.assertEqual(pages[0]['title'], 'Home')
        self.assertIn('Welcome home.', pages[0]['text'])
        self.assertNotIn('Nav junk', pages[0]['text'])

    def test_time_cap_stops_the_crawl(self):
        start = time.monotonic()
        pages, errors = gather.crawl([self.url('/slow'), self.url('/about')], max_pages=10,
                                     time_budget=1, page_timeout=1, allow_loopback=True, chromium=None)
        self.assertLess(time.monotonic() - start, 10)

    def test_no_browser_means_no_screenshots_but_pages_still_gathered(self):
        pages, errors = gather.crawl([self.url('/about')], max_pages=1, allow_loopback=True, chromium=None)
        self.assertEqual(len(pages), 1)
        self.assertIsNone(pages[0]['desktop_png'])
        self.assertIsNone(pages[0]['phone_png'])
        self.assertTrue(any('no browser' in reason for _, reason in errors))

    def test_empty_links_refused(self):
        with self.assertRaises(ValueError):
            gather.crawl([])

    def test_production_default_refuses_the_loopback_fixture(self):
        pages, errors = gather.crawl([self.url('/')], max_pages=1, chromium=None)  # allow_loopback defaults False
        self.assertEqual(pages, [])
        self.assertTrue(any('blocked address' in reason for _, reason in errors))


class WriteAttachments(unittest.TestCase):
    class FakeStore:
        def __init__(self):
            self.uploads = []

        def upload(self, video, name, ctype, data):
            self.uploads.append((video, name, ctype, data))
            return {'id': f'id{len(self.uploads)}', 'name': name, 'type': ctype, 'size': len(data)}

    def test_index_id_first_then_per_page_attachments(self):
        store = self.FakeStore()
        pages = [dict(url='http://x/1', title='One', text='hello', desktop_png=b'd', phone_png=b'p')]
        ids = gather.write_attachments(store, 'film', pages, [('http://x/skip', 'blocked address')])
        names = [u[1] for u in store.uploads]
        self.assertIn('page-1.txt', names)
        self.assertIn('page-1-desktop.png', names)
        self.assertIn('page-1-phone.png', names)
        self.assertEqual(names[-1], 'gathered-pages.md')  # written last, once every page is known
        index_upload = store.uploads[-1]
        self.assertEqual(ids[0], f'id{len(store.uploads)}')  # the index's id leads the list
        self.assertEqual(set(ids[1:]), {f'id{n}' for n in range(1, len(store.uploads))})
        index_body = index_upload[3].decode()
        self.assertIn('One', index_body)
        self.assertIn('skip', index_body)


if __name__ == '__main__':
    unittest.main()
