"""Home-screen install: the web app manifest, its icons, the service worker
(sw.js, the app shell only) and the head tags every top-level page carries.
All of it is served signed-out (editor.OPEN_ROUTES): a browser fetches the
manifest without cookies, and install has to work from the sign-in page."""
import json
import re
from importlib import resources

from . import __version__

THEME = '#0d0d10'  # director.css --bg

ICONS = {'/icons/icon-192.png': 'icon-192.png', '/icons/icon-512.png': 'icon-512.png',
         '/icons/icon-maskable-512.png': 'icon-maskable-512.png',
         '/icons/apple-touch-icon.png': 'apple-touch-icon.png'}
ROUTES = ('/manifest.webmanifest', '/sw.js', *ICONS)

# `black`, not `black-translucent`: translucent would slide every page's top bar under the
# status bar, and only the editor's phone layout pads for a top inset.
HEAD = ('<link rel="manifest" href="/manifest.webmanifest">'
        f'<meta name="theme-color" content="{THEME}">'
        '<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">'
        '<meta name="apple-mobile-web-app-capable" content="yes">'
        '<meta name="mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-title" content="videobuilder">'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black">'
        '<script>if("serviceWorker"in navigator)addEventListener("load",()=>navigator.serviceWorker'
        '.register("/sw.js").catch(e=>console.warn("service worker not registered",e)))</script>')


def manifest():
    return json.dumps({
        'name': 'videobuilder', 'short_name': 'videobuilder',
        # Relative, so the manifest never names the host it is served from.
        'start_url': './', 'scope': './', 'display': 'standalone',
        'theme_color': THEME, 'background_color': THEME,
        'icons': [{'src': '/icons/icon-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
                  {'src': '/icons/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
                  {'src': '/icons/icon-maskable-512.png', 'sizes': '512x512', 'type': 'image/png',
                   'purpose': 'maskable'}],
    }).encode()


def worker():
    # The version in the script's own bytes is what makes a deploy install a new worker,
    # whose activate step then deletes the previous version's cache.
    return (resources.files(__package__).joinpath('sw.js').read_text()
            .replace('__VERSION__', json.dumps(__version__))).encode()


def editor_html(page):
    """editor.html with the install tags, and its own scripts and styles
    stamped with the version: the worker caches those by URL, so a deploy's
    new page can never pick up the previous deploy's cached script."""
    page = re.sub(r'((?:href|src)="(?:director|suggest|settings_card)\.(?:js|css))"',
                  rf'\1?v={__version__}"', page)
    return page.replace('</head>', HEAD + '</head>', 1)


def serve(handler, route):
    if route == '/manifest.webmanifest':
        return handler._send(200, manifest(), 'application/manifest+json',
                             {'Cache-Control': 'no-cache'})
    if route == '/sw.js':
        return handler._send(200, worker(), 'text/javascript; charset=utf-8',
                             {'Cache-Control': 'no-cache'})
    return handler._send(200, resources.files(__package__).joinpath('icons', ICONS[route]).read_bytes(),
                         'image/png', {'Cache-Control': 'no-cache'})
