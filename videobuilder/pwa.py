"""Home-screen install: the web app manifest, its icons, the service worker
(sw.js, the app shell only) and the head tags every top-level page carries.
All of it is served signed-out (editor.OPEN_ROUTES): a browser fetches the
manifest without cookies, and install has to work from the sign-in page."""
import hashlib
import json
import re
from importlib import resources

from . import __version__

THEME = '#0d0d10'  # director.css --bg

ICONS = {'/icons/icon-192.png': 'icon-192.png', '/icons/icon-512.png': 'icon-512.png',
         '/icons/icon-maskable-512.png': 'icon-maskable-512.png',
         '/icons/apple-touch-icon.png': 'apple-touch-icon.png'}
ROUTES = ('/manifest.webmanifest', '/sw.js', *ICONS)
SHELL = ('director.js', 'director.css', 'suggest.js', 'suggest.css', 'settings_card.js', 'settings_card.css')

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
        '.register("/sw.js").catch(e=>console.warn("service worker not registered",e)));'
        # An installed iOS app has its own cookie jar, and a new-window link leaves the app for
        # Safari: signing in there never signs the app in. So a signed-out banner's link stays in
        # this window when installed, and the sign-in page comes back here (AUTH_RETURN).
        'document.addEventListener("click",e=>{const a=e.target.closest&&e.target.closest("a[data-sign-in]");'
        'if(!a||!(matchMedia("(display-mode: standalone)").matches||navigator.standalone))return;'
        'e.preventDefault();try{sessionStorage.setItem("vb-after-login",location.pathname+location.search)}'
        'catch(_){}location.href=a.href})</script>')

# The sign-in page's way back to where HEAD's banner link left: same-origin paths only.
AUTH_RETURN = ('let n="/";try{n=sessionStorage.getItem("vb-after-login")||"/";'
               'sessionStorage.removeItem("vb-after-login")}catch(_){}'
               'location.href=/^\\/(?![\\/\\\\])/.test(n)?n:"/"')


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


def shell_version():
    """The version plus a hash of the cached files' bytes. Commits land between
    version bumps, and a checkout's director.js changes under a running worker:
    keyed by the bare version, the worker's cache-first answer would keep
    serving the old script with nothing but a hard reload to clear it."""
    files = resources.files(__package__)
    digest = hashlib.sha256()
    for name in (*SHELL, *(f'icons/{icon}' for icon in ICONS.values())):
        digest.update(files.joinpath(name).read_bytes())
    return f'{__version__}-{digest.hexdigest()[:12]}'


def worker():
    # The shell version in the script's own bytes is what makes a deploy (or an edited
    # asset) install a new worker, whose activate step then deletes the previous cache.
    return (resources.files(__package__).joinpath('sw.js').read_text()
            .replace('__VERSION__', json.dumps(shell_version()))).encode()


def editor_html(page):
    """editor.html with the install tags, and its own scripts and styles
    stamped with the shell version: the worker caches those by URL, so a new
    page can never pick up a cached copy of a script that has since changed."""
    version = shell_version()
    page = re.sub(r'((?:href|src)="(?:director|suggest|settings_card)\.(?:js|css))"',
                  rf'\1?v={version}"', page)
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
