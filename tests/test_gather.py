"""The crawler: same-site scope, breadth-first order, the page cap, dedupe,
the skip rules and the time cap, against a local fixture site. The fixture
is reached only because these tests pass `allow_loopback=True`, the explicit
test-only switch guard.py documents; production code never does."""
import struct
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from videobuilder import gather, guard


def png(width, height):
    """Just enough PNG for the gatherer's checks: the signature and an IHDR."""
    return (b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', width, height)
            + b'\x08\x02\x00\x00\x00' + b'\x00' * 4)


def jpeg(width, height):
    return (b'\xff\xd8\xff\xe0' + struct.pack('>H', 16) + b'JFIF\x00' + b'\x00' * 9
            + b'\xff\xc0' + struct.pack('>HBHH', 17, 8, height, width) + b'\x00' * 12)


def webp(width, height):
    return (b'RIFF' + struct.pack('<I', 22) + b'WEBP' + b'VP8X' + struct.pack('<I', 10) + b'\x00' * 4
            + (width - 1).to_bytes(3, 'little') + (height - 1).to_bytes(3, 'little'))


ART_PAGE = (
    '<html><head><title>Art</title>'
    '<meta name="twitter:image" content="/tw.png">'
    '<meta property="og:image" content="/og.png">'
    '<meta name="theme-color" content="#FFF">'
    '<link rel="stylesheet" href="/site.css">'
    '<link rel="stylesheet" href="https://cdn.off-site.example/x.css">'
    '<style>:root{--brand:#FF0000;--ink: rgb(17, 34, 51)} h1{color:#f00;font-family:\'Inter\', sans-serif}</style>'
    '</head><body><nav><img src="/nav-logo.png"></nav><h1>Art</h1>'
    '<img src="/small.png" srcset="/small.png 400w, /large.png 1600w, /medium.png 800w">'
    '<picture><source srcset="/pic.webp"><img src="/pic-fallback.jpg"></picture>'
    '<img src="/icon.png"><img src="/fake.png"><img src="/wrongtype.png">'
    '<img src="http://10.1.2.3/private.png"><img src="/og.png"><img src="/vector.svg"><img src="/bomb.svg">'
    '<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">'
    '</body></html>')
ASSETS = {
    '/og.png': ('image/png', png(1200, 630)),
    '/tw.png': ('image/png', png(800, 400)),
    '/large.png': ('image/png', png(1600, 900)),
    '/small.png': ('image/png', png(400, 225)),
    '/medium.png': ('image/png', png(800, 450)),
    '/pic.webp': ('image/webp', webp(640, 480)),
    '/pic-fallback.jpg': ('image/jpeg', jpeg(640, 480)),
    '/nav-logo.png': ('image/png', png(200, 80)),
    '/icon.png': ('image/png', png(16, 16)),
    '/fake.png': ('image/png', b'<html>not an image</html>'),
    '/wrongtype.png': ('text/html', png(300, 300)),
    '/vector.svg': ('image/svg+xml', b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'),
    '/bomb.svg': ('image/svg+xml', b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "aaaa">]>'
                                    b'<svg xmlns="http://www.w3.org/2000/svg">&a;</svg>'),
    '/site.css': ('text/css', b'body{background:#ffffff;color:#112233;font-family:"Inter",sans-serif}'
                              b'@font-face{font-family:Brand;src:url(/font.woff2)} a{color:#F00} /* color:#abcdef */'),
    '/font.woff2': ('font/woff2', b'wOF2'),
}


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
    requested = []

    def do_GET(self):
        self.requested.append(self.path)
        if self.path in ASSETS:
            ctype, data = ASSETS[self.path]
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == '/art':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(ART_PAGE.encode())
            return
        if self.path == '/moved':
            self.send_response(301)
            self.send_header('Location', '/about')
            self.end_headers()
            return
        if self.path == '/to-private':
            self.send_response(302)
            self.send_header('Location', 'http://10.1.2.3/secret')
            self.end_headers()
            return
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
        _Site.requested = []
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

    def test_a_redirect_to_a_gathered_page_is_not_gathered_twice(self):
        # /moved lands on /about, which /about's own link then names again.
        pages, errors = gather.crawl([self.url('/moved'), self.url('/about')], max_pages=10,
                                     allow_loopback=True, chromium=None)
        urls = [p['url'] for p in pages]
        self.assertEqual(urls.count(self.url('/about')), 1)

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

    def test_only_http_and_https_links_are_fetched(self):
        links = ['file:///etc/passwd', 'data:text/html,<p>hi</p>', 'ftp://example.com/x']
        pages, errors = gather.crawl(links, max_pages=10, allow_loopback=True, chromium=None)
        self.assertEqual(pages, [])
        self.assertEqual([reason for _, reason in errors], ['not an http or https link'] * 3)

    def test_empty_links_refused(self):
        with self.assertRaises(ValueError):
            gather.crawl([])

    def test_a_redirect_to_a_private_address_is_refused(self):
        pages, errors = gather.crawl([self.url('/to-private')], max_pages=1, allow_loopback=True, chromium=None)
        self.assertEqual(pages, [])
        self.assertTrue(any('10.1.2.3' in url for url, _ in errors), errors)

    def test_production_default_refuses_the_loopback_fixture(self):
        pages, errors = gather.crawl([self.url('/')], max_pages=1, chromium=None)  # allow_loopback defaults False
        self.assertEqual(pages, [])
        self.assertTrue(any('blocked address' in reason for _, reason in errors))


class LinksIn(unittest.TestCase):
    def test_trailing_punctuation_is_not_part_of_the_link(self):
        text = 'See https://a.example/x. Or https://a.example/y, https://a.example/z! "https://a.example/q"'
        self.assertEqual(gather.links_in(text), ['https://a.example/x', 'https://a.example/y',
                                                 'https://a.example/z', 'https://a.example/q'])

    def test_parentheses_close_a_link_only_when_unbalanced(self):
        self.assertEqual(gather.links_in('(see https://a.example/x)'), ['https://a.example/x'])
        self.assertEqual(gather.links_in('[docs](https://a.example/d).'), ['https://a.example/d'])
        self.assertEqual(gather.links_in('https://en.example/wiki/Foo_(bar)'), ['https://en.example/wiki/Foo_(bar)'])

    def test_angle_brackets_and_duplicates(self):
        text = 'Use <https://a.example/x> and http://b.example/?q=1 then https://a.example/x again.'
        self.assertEqual(gather.links_in(text), ['https://a.example/x', 'http://b.example/?q=1'])

    def test_no_links(self):
        self.assertEqual(gather.links_in('Make the title bigger. ftp://a.example is not a web link.'), [])
        self.assertEqual(gather.links_in('https:// nothing'), [])
        self.assertEqual(gather.links_in(''), [])

    def test_an_unparseable_link_is_skipped_not_raised(self):
        text = 'see http://[oops and http://[::1 then https://a.example/x'
        self.assertEqual(gather.links_in(text), ['https://a.example/x'])


class Artwork(GatherFixture):
    def gather_art(self, **kw):
        pages, errors = gather.crawl([self.url('/art')], max_pages=1, allow_loopback=True, chromium=None, **kw)
        self.assertEqual(len(pages), 1)
        return pages[0], errors

    def test_share_image_first_then_content_images_in_page_order(self):
        page, _ = self.gather_art()
        self.assertEqual([i['url'] for i in page['images']],
                         [self.url(p) for p in ('/og.png', '/tw.png', '/large.png', '/pic.webp',
                                                '/pic-fallback.jpg', '/vector.svg')])
        self.assertEqual(page['images'][0]['data'], ASSETS['/og.png'][1])
        # srcset's largest candidate only; nothing in nav; og.png's second mention not fetched again
        self.assertNotIn('/small.png', _Site.requested)
        self.assertNotIn('/medium.png', _Site.requested)
        self.assertNotIn('/nav-logo.png', _Site.requested)
        self.assertEqual(_Site.requested.count('/og.png'), 1)

    def test_icons_wrong_types_and_mismatched_bytes_are_refused_and_reported(self):
        page, _ = self.gather_art()
        reasons = dict(page['skipped'])
        self.assertIn('too small', reasons[self.url('/icon.png')])
        self.assertIn('not the image/png it claims', reasons[self.url('/fake.png')])
        self.assertIn('not an image type', reasons[self.url('/wrongtype.png')])
        # A vector logo is kept whatever its declared size; an entity-declaring SVG is refused.
        self.assertNotIn(self.url('/vector.svg'), reasons)
        self.assertIn('declares XML entities', reasons[self.url('/bomb.svg')])

    def test_an_image_on_a_private_address_is_refused_not_fetched(self):
        page, _ = self.gather_art()
        self.assertEqual(dict(page['skipped'])['http://10.1.2.3/private.png'], 'image refused: blocked address')

    def test_a_stylesheet_on_a_private_address_is_refused_not_fetched(self):
        parser = gather._PageParser()
        parser.feed('<link rel="stylesheet" href="/site.css">')
        proxy = guard.GuardProxy(allow_loopback=True)
        self.addCleanup(proxy.close)
        skipped = []
        gather._page_theme(guard.opener(proxy.port), parser, 'http://10.1.2.3/', True,
                           time.monotonic() + 5, 5, skipped)
        self.assertEqual(skipped, [('http://10.1.2.3/site.css', 'stylesheet refused: blocked address')])

    def test_per_page_and_per_note_image_caps(self):
        old = gather.IMAGES_PER_PAGE, gather.IMAGES_PER_NOTE
        self.addCleanup(lambda: (setattr(gather, 'IMAGES_PER_PAGE', old[0]),
                                 setattr(gather, 'IMAGES_PER_NOTE', old[1])))
        gather.IMAGES_PER_PAGE = 2
        page, _ = self.gather_art()
        self.assertEqual(len(page['images']), 2)
        self.assertTrue(any('more images not gathered' in reason for _, reason in page['skipped']))
        gather.IMAGES_PER_PAGE, gather.IMAGES_PER_NOTE = 8, 1
        pages, _ = gather.crawl([self.url('/art'), self.url('/about')], max_pages=2, follow=False,
                                allow_loopback=True, chromium=None)
        self.assertEqual(sum(len(p['images']) for p in pages), 1)

    def test_the_theme_lists_colours_and_fonts_most_used_first(self):
        page, _ = self.gather_art()
        theme = page['theme']
        self.assertIn('Theme colour (meta theme-color): #ffffff', theme)
        colours = theme.split('## Colours, most used first')[1].split('##')[0]
        self.assertEqual(colours.split()[1], '#ff0000')       # --brand, h1 and a: 3 uses
        self.assertIn('- #ff0000 (3 uses)', colours)
        self.assertIn('- #112233 (2 uses)', colours)          # rgb(17, 34, 51) normalised to hex
        self.assertNotIn('#abcdef', theme)                    # a comment, not a declaration
        self.assertIn('- --brand: #ff0000', theme)
        self.assertIn('- "Inter", sans-serif (2 uses)', theme)
        # The stylesheet was read (an off-site one is tried too); no font file ever was.
        self.assertIn('/site.css', _Site.requested)
        self.assertNotIn('/font.woff2', _Site.requested)
        self.assertFalse(any(p.endswith(('.woff', '.woff2', '.ttf', '.otf')) for p in _Site.requested))

    def test_the_theme_leaves_out_tailwind_resets_and_transparent_colours(self):
        css = ['*{--tw-ring-color:#3b82f6;--tw-shadow:#0000;color:#00000000}'
               'body{background:#c8d5c1;color:#1a1a1a;--brand:#c8d5c1}']
        theme = gather.theme('https://a.example/', css)
        self.assertNotIn('--tw-', theme)
        self.assertNotIn('#3b82f6', theme)
        self.assertNotIn('#00000000', theme)
        self.assertIn('- #c8d5c1 (2 uses)', theme)
        self.assertIn('- --brand: #c8d5c1', theme)

    def test_a_page_with_no_styles_has_no_theme(self):
        page = gather.crawl([self.url('/about')], max_pages=1, allow_loopback=True, chromium=None)[0][0]
        self.assertIsNone(page['theme'])
        self.assertEqual(page['images'], [])

    def test_follow_false_reads_only_the_linked_pages(self):
        pages, _ = gather.crawl([self.url('/')], max_pages=5, follow=False, allow_loopback=True, chromium=None)
        self.assertEqual([p['url'] for p in pages], [self.url('/')])


class ImageTypes(unittest.TestCase):
    def test_every_gathered_image_type_is_one_the_attachment_store_accepts(self):
        from videobuilder.attachments import MAGIC, TYPES
        for ctype, ext in gather.IMAGE_TYPES.items():
            self.assertIn(ext, MAGIC)
            self.assertEqual(TYPES[ext], ctype)


class WriteAttachments(unittest.TestCase):
    class FakeStore:
        def __init__(self, max_file=None, max_files=None, max_message=None):
            self.uploads = []
            if max_file is not None:
                self.max_file = max_file
            if max_files is not None:
                self.max_files = max_files
            if max_message is not None:
                self.max_message = max_message

        def upload(self, video, name, ctype, data, allow_oversize=False):
            if not allow_oversize and getattr(self, 'max_file', None) is not None and len(data) > self.max_file:
                raise ValueError('attachment exceeds file size limit')
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

    def test_oversize_file_has_its_limit_raised_and_said_so(self):
        store = self.FakeStore(max_file=200)
        pages = [dict(url='http://x/1', title='One', text='hello', desktop_png=b'd' * 300, phone_png=None)]
        ids = gather.write_attachments(store, 'film', pages, [])
        names = [u[1] for u in store.uploads]
        self.assertIn('page-1.txt', names)
        self.assertIn('page-1-desktop.png', names)  # over max_file, but uploaded anyway
        index_body = store.uploads[-1][3].decode()
        self.assertIn('file size limit raised to fit', index_body)

    def test_stays_within_the_stores_file_count_budget(self):
        store = self.FakeStore(max_files=3)
        pages = [dict(url=f'http://x/{n}', title=f'P{n}', text='hi', desktop_png=b'd', phone_png=b'p')
                 for n in range(1, 4)]
        # budget: 3 max_files - 1 reserved - 1 index slot = 1 page attachment fits
        ids = gather.write_attachments(store, 'film', pages, [], reserved_files=1)
        self.assertEqual(len(store.uploads), 2)  # one page attachment plus the index
        self.assertEqual(len(ids), 2)
        index_body = store.uploads[-1][3].decode()
        self.assertIn('attachment limit reached', index_body)
        self.assertIn('Some gathered attachments were skipped', index_body)

    def test_stays_within_the_stores_message_size_budget(self):
        # Large enough that the index (a couple hundred bytes) still fits after the
        # phone screenshot is skipped, so this exercises the skip message without
        # also tripping the "no room for the index itself" case below.
        store = self.FakeStore(max_message=2300)
        pages = [dict(url='http://x/1', title='One', text='hi', desktop_png=b'd' * 2000, phone_png=b'p' * 2000)]
        ids = gather.write_attachments(store, 'film', pages, [], reserved_bytes=0)
        self.assertLessEqual(sum(len(u[3]) for u in store.uploads), 2300)
        index_body = store.uploads[-1][3].decode()
        self.assertIn('attachment limit reached', index_body)

    def test_index_itself_skipped_rather_than_exceeding_max_files(self):
        # The director's own uploads already spent the whole file budget: there is no
        # slot left even for the index, so it must not be uploaded unconditionally.
        store = self.FakeStore(max_files=3)
        pages = [dict(url='http://x/1', title='One', text='hi', desktop_png=b'd', phone_png=b'p')]
        ids = gather.write_attachments(store, 'film', pages, [], reserved_files=3)
        self.assertEqual(store.uploads, [])
        self.assertEqual(ids, [])

    def test_explicit_max_files_and_max_message_override_the_stores_own_limit(self):
        # A caller sharing this note with a bigger budget than the store's ordinary
        # one (e.g. the first note from New video, which allows more files than an
        # ordinary note) must pass that budget in rather than being governed by the
        # store's own max_files/max_message, or a dozen reserved uploads leave no
        # room for anything gathered here.
        store = self.FakeStore(max_files=10, max_message=100)
        pages = [dict(url='http://x/1', title='One', text='hi', desktop_png=b'd', phone_png=b'p')]
        ids = gather.write_attachments(store, 'film', pages, [], reserved_files=12, reserved_bytes=90,
                                       max_files=50, max_message=1000)
        self.assertNotEqual(ids, [])
        names = [u[1] for u in store.uploads]
        self.assertIn('page-1.txt', names)
        self.assertIn('gathered-pages.md', names)

    def art_page(self):
        return dict(url='http://x/1', title='One', text='hi', desktop_png=b'd' * 10, phone_png=b'p' * 10,
                    theme='# Theme\n- #ff0000 (3 uses)',
                    images=[dict(url='http://x/a.png', type='image/png', data=b'a' * 50),
                            dict(url='http://x/b.gif', type='image/gif', data=b'GIF89a' + b'b' * 50)],
                    skipped=[('http://x/icon.png', 'image refused: too small (an icon or tracking pixel)')])

    def test_images_and_theme_are_uploaded_and_listed(self):
        store = self.FakeStore()
        gather.write_attachments(store, 'film', [self.art_page()], [])
        names = [u[1] for u in store.uploads]
        self.assertEqual(names[:-1], ['page-1-theme.md', 'page-1-desktop.png', 'page-1-phone.png', 'page-1.txt',
                                      'page-1-image-1.png', 'page-1-image-2.gif'])
        self.assertEqual(store.uploads[4][2], 'image/png')
        index = store.uploads[-1][3].decode()
        self.assertIn('theme: page-1-theme.md', index)
        self.assertIn('image http://x/a.png: page-1-image-1.png', index)
        self.assertIn('image http://x/b.gif: page-1-image-2.gif', index)
        self.assertIn('http://x/icon.png: image refused: too small', index)
        # listed text, screenshots, theme, images, whatever order they were uploaded in
        self.assertLess(index.index('text: page-1.txt'), index.index('theme: page-1-theme.md'))

    def test_a_tight_budget_keeps_the_theme_and_drops_images_first(self):
        store = self.FakeStore(max_files=4)
        gather.write_attachments(store, 'film', [self.art_page()], [])
        names = [u[1] for u in store.uploads]
        self.assertEqual(names, ['page-1-theme.md', 'page-1-desktop.png', 'page-1-phone.png', 'gathered-pages.md'])
        index = store.uploads[-1][3].decode()
        self.assertIn('image http://x/a.png: skipped (attachment limit reached)', index)
        self.assertIn('text: skipped (attachment limit reached)', index)

    def test_the_themes_of_every_page_go_before_any_pages_images(self):
        store = self.FakeStore(max_files=3)
        second = dict(self.art_page(), url='http://x/2', theme='# Theme 2')
        gather.write_attachments(store, 'film', [self.art_page(), second], [])
        self.assertEqual([u[1] for u in store.uploads], ['page-1-theme.md', 'page-2-theme.md', 'gathered-pages.md'])

    def test_index_itself_skipped_rather_than_exceeding_max_message(self):
        # Page attachments alone already spend the whole byte budget; the index
        # markdown itself must not be uploaded on top of that.
        store = self.FakeStore(max_message=8)
        pages = [dict(url='http://x/1', title='One', text='', desktop_png=b'd' * 8, phone_png=None)]
        ids = gather.write_attachments(store, 'film', pages, [], reserved_bytes=0)
        names = [u[1] for u in store.uploads]
        self.assertNotIn('gathered-pages.md', names)
        self.assertEqual(len(ids), len(store.uploads))


if __name__ == '__main__':
    unittest.main()
