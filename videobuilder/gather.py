"""Gathering: visiting the links in a chat note, so the builder never has
to -- the builder's sandbox stays offline. The editor fetches the linked
pages (for a video's first note, also same-site pages breadth-first from
them) through `guard.GuardProxy` before the note is queued, and keeps per
page: the final URL, the title, readable text, a desktop and a phone
screenshot, the page's artwork (its share image and content images) and its
theme (the colours and font stacks its CSS uses most). `write_attachments`
turns that into ordinary note attachments plus one index attachment listing
every page.
"""
import collections
import html.parser
import re
import shutil
import struct
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import urllib.error
import urllib.request

from . import browser, guard

MAX_PAGES = 10
TIME_BUDGET = 120
PAGE_TIMEOUT = 20
MAX_TEXT = 20_000
DESKTOP = (1440, 900)
PHONE = (390, 844)
USER_AGENT = 'Mozilla/5.0 (compatible; videobuilder-gatherer/1.0)'
_SKIP = re.compile(r'(?:^|[/._-])(log[-_]?(?:in|on|out|off)|sign[-_]?(?:in|up|out))(?:$|[/._?#-])', re.I)
_BOILERPLATE = ('script', 'style', 'nav', 'header', 'footer')
MAX_LINKS = 5
IMAGES_PER_PAGE = 8
IMAGES_PER_NOTE = 12
# Candidates tried per page: some turn out to be icons or the wrong type.
IMAGE_TRIES = 16
MAX_IMAGE = 5 * 1024 * 1024
MIN_IMAGE_SIDE = 64
MAX_STYLESHEETS = 3
MAX_STYLESHEET = 500 * 1024
THEME_COLOURS = 10
THEME_FONTS = 5
# Only types the attachment store accepts (attachments.TYPES), so nothing is
# fetched only to be turned away by upload.
IMAGE_TYPES = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif',
               'image/svg+xml': 'svg'}
_URL = re.compile(r'https?://[^\s<>"`]+', re.I)
_TRAILING = '.,;:!?)]}\'">'
_CLOSERS = {')': '(', ']': '[', '}': '{'}


def links_in(text):
    """The http(s) URLs in a note's text, in order, without the punctuation
    that usually follows a link in prose: `(see https://a.example/x).` gives
    https://a.example/x, while a balanced `https://a.example/x_(y)` keeps
    its parenthesis. Duplicates are dropped."""
    found = []
    for match in _URL.finditer(text or ''):
        url = match.group(0)
        while url and url[-1] in _TRAILING:
            opener = _CLOSERS.get(url[-1])
            if opener and url.count(opener) >= url.count(url[-1]):
                break
            url = url[:-1]
        try:
            if urlsplit(url).hostname:
                found.append(url)
        except ValueError:
            # A half-typed `http://[::1` is prose, not a link; the note still posts.
            continue
    return list(dict.fromkeys(found))


def _largest(srcset):
    """The URL of a `srcset`'s largest candidate (by its `w`, else its `x`
    descriptor; a bare URL counts as 1x), or None."""
    best, best_size = None, -1.0
    for candidate in re.split(r',\s+', srcset.strip()):
        parts = candidate.strip().split()
        if not parts:
            continue
        size = 1.0
        if len(parts) > 1:
            match = re.fullmatch(r'(\d+(?:\.\d+)?)([wx])', parts[1])
            if match:
                size = float(match.group(1)) * (1 if match.group(2) == 'w' else 1000)
        if size > best_size:
            best, best_size = parts[0].rstrip(','), size
    return best


class _PageParser(html.parser.HTMLParser):
    """Rendered-free: the `<title>`, visible text with script/style/nav/
    header/footer stripped, every `<a href>`, and what the page's look is
    made of -- its share image, its content images (none from nav or
    footer), inline `<style>` text, linked stylesheets and theme-color --
    from raw HTML."""

    def __init__(self):
        super().__init__()
        self.links = []
        self.share_images = []
        self.images = []
        self.stylesheets = []
        self.styles = []
        self.theme_color = None
        self._skip_depth = 0
        self._chrome_depth = 0
        self._in_title = False
        self._in_style = False
        self._title = []
        self._text = []

    def handle_starttag(self, tag, attrs):
        a = {k: v for k, v in attrs if v is not None}
        if tag in _BOILERPLATE:
            self._skip_depth += 1
            if tag in ('nav', 'footer'):
                self._chrome_depth += 1
            self._in_style = tag == 'style'
        elif tag == 'title':
            self._in_title = True
        elif tag == 'a':
            href = a.get('href')
            if href:
                self.links.append(href)
        elif tag == 'meta':
            key = (a.get('property') or a.get('name') or '').lower()
            content = a.get('content', '').strip()
            if key in ('og:image', 'og:image:url', 'og:image:secure_url', 'twitter:image') and content:
                self.share_images.append((key, content))
            elif key == 'theme-color' and content and self.theme_color is None:
                self.theme_color = content
        elif tag == 'link':
            rels = a.get('rel', '').lower().split()
            if 'stylesheet' in rels and a.get('href'):
                self.stylesheets.append(a['href'])
        elif tag in ('img', 'source') and not self._chrome_depth:
            url = _largest(a['srcset']) if a.get('srcset') else (a.get('src') if tag == 'img' else None)
            if url:
                self.images.append(url)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in _BOILERPLATE:
            self.handle_endtag(tag)
        elif tag == 'title':
            self._in_title = False

    def handle_endtag(self, tag):
        if tag in _BOILERPLATE and self._skip_depth:
            self._skip_depth -= 1
            if tag in ('nav', 'footer') and self._chrome_depth:
                self._chrome_depth -= 1
            if tag == 'style':
                self._in_style = False
        elif tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_style:
            self.styles.append(data)
        elif self._in_title:
            self._title.append(data)
        elif not self._skip_depth:
            stripped = ' '.join(data.split())
            if stripped:
                self._text.append(stripped)

    @property
    def title(self):
        return ' '.join(''.join(self._title).split())

    @property
    def text(self):
        return '\n'.join(self._text)

    @property
    def image_urls(self):
        """Share image first (og:image ahead of twitter:image, whichever order
        the page has them in), then content images in page order."""
        share = sorted(self.share_images, key=lambda item: not item[0].startswith('og:'))
        return [url for _, url in share] + self.images


def find_chromium():
    for name in ('chromium', 'chromium-browser', 'google-chrome'):
        path = shutil.which(name)
        if path:
            return path
    return '/usr/bin/chromium' if Path('/usr/bin/chromium').is_file() else None


def _registrable(host):
    host = (host or '').lower().rstrip('.')
    return host[4:] if host.startswith('www.') else host


def _same_site(url, site_hosts):
    host = _registrable(urlsplit(url).hostname)
    return bool(host) and host in site_hosts


def _looks_skippable(url):
    return bool(_SKIP.search(urlsplit(url).path))


def _get(opener, url, timeout, allow_loopback, accept, limit):
    """(final URL, content type, up to `limit`+1 body bytes) for `url`, through
    the guard proxy behind `opener` -- the one way anything here is fetched."""
    parts = urlsplit(url)
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    # A fast, explicit refusal for the link itself; the proxy behind `opener`
    # re-checks regardless, including every redirect this fetch follows.
    guard.resolve_and_check(parts.hostname, port, allow_loopback=allow_loopback)
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': accept})
    with opener.open(request, timeout=timeout) as response:
        ctype = response.headers.get_content_type().lower()
        if accept.startswith('image/') and ctype not in IMAGE_TYPES:
            raise ValueError(f'not an image type it accepts ({ctype})')
        if accept == 'text/css' and ctype != 'text/css':
            raise ValueError(f'not a stylesheet ({ctype})')
        length = response.headers.get('Content-Length', '')
        if length.isdigit() and int(length) > limit and not accept.startswith('text/'):
            raise ValueError('too large')
        return response.geturl(), ctype, response.read(limit + 1)


def _fetch(opener, url, timeout, allow_loopback):
    final_url, ctype, data = _get(opener, url, timeout, allow_loopback, 'text/html', MAX_TEXT * 8)
    if ctype != 'text/html':
        raise ValueError(f'not an HTML page ({ctype})')
    return final_url, data.decode('utf-8', 'replace')


def _sniff(data):
    """The image type `data` actually is, by its magic bytes, or None."""
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return None


def _image_size(data, ctype):
    """(width, height) read from a PNG/GIF/WebP/JPEG header, or None when it
    can't be read cheaply (a header this doesn't understand)."""
    try:
        if ctype == 'image/png' and data[12:16] == b'IHDR':
            return struct.unpack('>II', data[16:24])
        if ctype == 'image/gif':
            return struct.unpack('<HH', data[6:10])
        if ctype == 'image/webp':
            chunk = data[12:16]
            if chunk == b'VP8 ':
                w, h = struct.unpack('<HH', data[26:30])
                return w & 0x3fff, h & 0x3fff
            if chunk == b'VP8L':
                b = data[21:25]
                return 1 + (((b[1] & 0x3f) << 8) | b[0]), 1 + (((b[3] & 0xf) << 10) | (b[2] << 2) | (b[1] >> 6))
            if chunk == b'VP8X':
                return 1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')
        if ctype == 'image/jpeg':
            i = 2
            while i + 9 <= len(data):
                if data[i] != 0xff:
                    return None
                marker = data[i + 1]
                if marker == 0xff:
                    i += 1
                    continue
                if marker in (0xd8, 0x01) or 0xd0 <= marker <= 0xd7:
                    i += 2
                    continue
                if 0xc0 <= marker <= 0xcf and marker not in (0xc4, 0xc8, 0xcc):
                    h, w = struct.unpack('>HH', data[i + 5:i + 9])
                    return w, h
                i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
    except (struct.error, IndexError):
        return None
    return None


def _fetch_image(opener, url, timeout, allow_loopback):
    """An image's (content type, bytes), refused (ValueError) unless the
    response's Content-Type and its magic bytes agree on an accepted type,
    it is at most MAX_IMAGE bytes, and it is not icon-sized. An SVG must
    instead pass the attachment store's own SVG check."""
    _, ctype, data = _get(opener, url, timeout, allow_loopback, 'image/*', MAX_IMAGE)
    if len(data) > MAX_IMAGE:
        raise ValueError('too large')
    if ctype == 'image/svg+xml':
        # A vector logo has no pixel size worth judging, so no icon check.
        from .attachments import svg_problem
        problem = svg_problem(data)
        if problem:
            raise ValueError(problem)
        return ctype, data
    sniffed = _sniff(data)
    if sniffed != ctype:
        raise ValueError(f'its content is not the {ctype} it claims to be')
    size = _image_size(data, ctype)
    if size and min(size) < MIN_IMAGE_SIDE:
        raise ValueError('too small (an icon or tracking pixel)')
    return ctype, data


_COLOUR = re.compile(r'#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\([^()]*\)|\b(?:white|black)\b', re.I)
_DECLARATION = re.compile(r'([-\w]+)\s*:\s*([^;{}]+)')
_FONT_STACK = re.compile(r'[\w\s"\',.-]{1,120}')
_COLOUR_PROPERTIES = ('color', 'background', 'background-color')
_NAMED = {'white': '#ffffff', 'black': '#000000'}


def _colour(value):
    """A CSS colour normalised for counting: lowercase hex in 6 or 8 digits,
    and an opaque integer rgb() as hex; None for a malformed hex."""
    value = ' '.join(value.lower().split())
    if value in _NAMED:
        return _NAMED[value]
    if value.startswith('#'):
        digits = value[1:]
        if len(digits) in (3, 4):
            digits = ''.join(c * 2 for c in digits)
        return '#' + digits if len(digits) in (6, 8) else None
    match = re.fullmatch(r'rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)\s*(?:[,/]\s*(1|1\.0+|100%)\s*)?\)', value)
    if match and all(int(n) <= 255 for n in match.groups()[:3]):
        return '#' + ''.join(f'{int(n):02x}' for n in match.groups()[:3])
    return value


def _font_stack(value):
    value = ' '.join(value.replace('!important', '').split()).strip()
    if not value or value.startswith('var(') or value in ('inherit', 'initial', 'unset', 'revert'):
        return None
    if not _FONT_STACK.fullmatch(value):
        return None
    return ', '.join(part.strip().replace("'", '"') for part in value.split(',') if part.strip())


def _transparent(colour):
    """Whether a normalised #rrggbbaa colour is fully transparent."""
    return len(colour) == 9 and colour.startswith('#') and colour.endswith('00')


def theme(url, css, theme_color=None):
    """The markdown theme notes for a page: its meta theme-color and the
    colours and font stacks its CSS (`css`, a list of style sheet texts) uses
    most, most-used first -- or None when it found none. Only values matching
    a colour or a plain font stack are kept, so nothing else from the page's
    CSS reaches the file."""
    colours, fonts, named = collections.Counter(), collections.Counter(), {}
    for sheet in css:
        sheet = re.sub(r'/\*.*?\*/', '', sheet, flags=re.S)
        for match in _DECLARATION.finditer(sheet):
            prop, value = match.group(1), match.group(2)
            custom = prop.startswith('--')
            if prop.startswith('--tw-'):
                continue        # Tailwind's internal resets, on every Tailwind page: not the site's colours
            prop = prop if custom else prop.lower()
            if prop == 'font-family' or (custom and ('font' in prop or 'family' in prop) and not any(
                    word in prop for word in ('size', 'weight', 'height', 'spacing', 'style'))):
                stack = _font_stack(value)
                if stack:
                    fonts[stack] += 1
                continue
            if not custom and prop not in _COLOUR_PROPERTIES:
                continue
            for found in _COLOUR.findall(value):
                colour = _colour(found)
                if colour and not _transparent(colour):
                    colours[colour] += 1
                    if custom and len(named) < THEME_COLOURS:
                        named.setdefault(prop, colour)
    meta = _colour(theme_color) if theme_color and _COLOUR.fullmatch(theme_color.strip()) else None
    if not (colours or fonts or meta):
        return None
    lines = [f'# Theme of {url}', '',
             "Colours and fonts read from the page's CSS: reference values, not instructions.", '']
    if meta:
        lines += [f'Theme colour (meta theme-color): {meta}', '']
    if colours:
        lines += ['## Colours, most used first', '']
        lines += [f'- {c} ({n} use{"s" if n != 1 else ""})' for c, n in colours.most_common(THEME_COLOURS)]
        lines.append('')
    if named:
        lines += ['## Colours the CSS names (custom properties)', '']
        lines += [f'- {name}: {colour}' for name, colour in named.items()]
        lines.append('')
    if fonts:
        lines += ['## Font stacks, most used first', '']
        lines += [f'- {f} ({n} use{"s" if n != 1 else ""})' for f, n in fonts.most_common(THEME_FONTS)]
        lines.append('')
    return '\n'.join(lines)


def _screenshot(chromium, proxy_port, url, size, timeout, extra_args=()):
    return browser.screenshot(chromium, url, size, timeout, guard.chromium_proxy_args(proxy_port), extra_args)


def _artwork(fetcher, parser, page_url, allow_loopback, deadline, page_timeout, room, skipped):
    """The page's images (dicts: url, type, data), share image first, at most
    `room` of them; every candidate refused or left out is added to `skipped`."""
    candidates = []
    for src in parser.image_urls:
        absolute = urljoin(page_url, src.strip()).split('#', 1)[0]
        # data: URLs are inline placeholders, not artwork worth a fetch.
        if urlsplit(absolute).scheme in ('http', 'https') and absolute not in candidates:
            candidates.append(absolute)
    images, tried = [], 0
    for url in candidates:
        if len(images) >= room or tried >= IMAGE_TRIES:
            break
        if time.monotonic() >= deadline:
            skipped.append((url, 'image not gathered: out of time'))
            tried = len(candidates)
            break
        tried += 1
        try:
            ctype, data = _fetch_image(fetcher, url, max(1, min(page_timeout, deadline - time.monotonic())),
                                       allow_loopback)
        except guard.Refused:
            skipped.append((url, 'image refused: blocked address'))
            continue
        except Exception as exc:
            skipped.append((url, f'image refused: {exc}'))
            continue
        images.append(dict(url=url, type=ctype, data=data))
    left = len(candidates) - tried
    if left > 0:
        skipped.append((page_url, f'{left} more image{"s" if left != 1 else ""} not gathered '
                                  f'(at most {IMAGES_PER_PAGE} a page and {IMAGES_PER_NOTE} a note)'))
    return images


def _page_theme(fetcher, parser, page_url, allow_loopback, deadline, page_timeout, skipped):
    """The page's theme notes from its inline styles and its first
    MAX_STYLESHEETS stylesheets, from any public host (sites often serve CSS
    from a CDN). Nothing a stylesheet points at (@import, fonts,
    backgrounds) is ever fetched."""
    css = list(parser.styles)
    sheets = list(dict.fromkeys(urljoin(page_url, href.strip()).split('#', 1)[0] for href in parser.stylesheets))
    fetched = 0
    for url in sheets:
        if fetched >= MAX_STYLESHEETS or time.monotonic() >= deadline:
            break
        if urlsplit(url).scheme not in ('http', 'https'):
            continue
        fetched += 1
        try:
            _, _, data = _get(fetcher, url, max(1, min(page_timeout, deadline - time.monotonic())),
                              allow_loopback, 'text/css', MAX_STYLESHEET)
        except guard.Refused:
            skipped.append((url, 'stylesheet refused: blocked address'))
            continue
        except Exception as exc:
            skipped.append((url, f'stylesheet not read: {exc}'))
            continue
        css.append(data[:MAX_STYLESHEET].decode('utf-8', 'replace'))
    return theme(page_url, css, parser.theme_color)


_AUTO = object()


def crawl(links, max_pages=MAX_PAGES, time_budget=TIME_BUDGET, page_timeout=PAGE_TIMEOUT,
         allow_loopback=False, chromium=_AUTO, follow=True):
    """Visit `links` and (with `follow`), breadth-first, same-site pages
    reachable from them, up to `max_pages` pages in total within
    `time_budget` seconds. Returns (pages, errors): `pages` is a list of
    dicts (url, title, text, desktop_png, phone_png -- the last two None
    without a browser -- images, a list of {url, type, data}, theme, the
    page's theme notes or None, and skipped, (url, reason) for each image or
    stylesheet left out), and `errors` a list of (url, reason) for every link
    skipped or that failed, in the order encountered. Raises only for a bad
    call (no links)."""
    if not links:
        raise ValueError('no links to gather')
    chromium = find_chromium() if chromium is _AUTO else chromium
    site_hosts = {_registrable(urlsplit(link).hostname) for link in links}
    proxy = guard.GuardProxy(allow_loopback=allow_loopback)
    pages, errors, seen = [], [], set()
    queue = list(dict.fromkeys(url.split('#', 1)[0] for url in links))
    deadline = time.monotonic() + time_budget
    fetcher = guard.opener(proxy.port)
    image_count = 0
    try:
        while queue and len(pages) < max_pages and time.monotonic() < deadline:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            if urlsplit(url).scheme not in ('http', 'https'):
                errors.append((url, 'not an http or https link'))
                continue
            if _looks_skippable(url):
                errors.append((url, 'looks like a sign-in or sign-out page'))
                continue
            remaining = max(1, min(page_timeout, deadline - time.monotonic()))
            try:
                final_url, body = _fetch(fetcher, url, remaining, allow_loopback)
            except guard.Refused as exc:
                errors.append((url, 'blocked address'))
                continue
            except Exception as exc:
                errors.append((url, f'fetch failed: {exc}'))
                continue
            # A redirect can land on a page already gathered, or one still queued.
            final_url = final_url.split('#', 1)[0]
            if final_url != url and final_url in seen:
                continue
            seen.add(final_url)
            parser = _PageParser()
            try:
                parser.feed(body)
            except Exception:
                pass
            desktop = phone = None
            if chromium:
                try:
                    remaining = max(1, min(page_timeout, deadline - time.monotonic()))
                    desktop = _screenshot(chromium, proxy.port, final_url, DESKTOP, remaining)
                    remaining = max(1, min(page_timeout, deadline - time.monotonic()))
                    phone = _screenshot(chromium, proxy.port, final_url, PHONE, remaining)
                except Exception as exc:
                    errors.append((url, f'screenshot failed: {exc}'))
            else:
                errors.append((url, 'links not gathered: no browser'))
            skipped = []
            page_theme = _page_theme(fetcher, parser, final_url, allow_loopback, deadline, page_timeout, skipped)
            room = min(IMAGES_PER_PAGE, IMAGES_PER_NOTE - image_count)
            images = _artwork(fetcher, parser, final_url, allow_loopback, deadline, page_timeout, room, skipped)
            image_count += len(images)
            pages.append(dict(url=final_url, title=parser.title, text=parser.text[:MAX_TEXT],
                              desktop_png=desktop, phone_png=phone, images=images, theme=page_theme,
                              skipped=skipped))
            if not follow:
                continue
            for href in parser.links:
                absolute = urljoin(final_url, href).split('#', 1)[0]
                scheme = urlsplit(absolute).scheme
                if scheme in ('http', 'https') and absolute not in seen and _same_site(absolute, site_hosts):
                    queue.append(absolute)
    finally:
        # Refusals the proxy itself caught (a redirect or a Chromium subresource the
        # per-link pre-check above never saw) are reported too, not just top-level skips.
        errors.extend(proxy.log)
        proxy.close()
    return pages, errors


def write_attachments(store, video, pages, errors, reserved_files=0, reserved_bytes=0,
                      max_files=None, max_message=None):
    """Upload each page's theme notes, screenshots, text and images as
    ordinary note attachments plus one index attachment listing every page,
    and return the attachment ids (index first). A single oversized file
    (bigger than the store's own per-file limit -- not expected at these
    sizes) has that limit raised just for this upload, noted in the index:
    the one case the brief allows raising a limit for.

    `reserved_files`/`reserved_bytes` are the count and size of attachments
    the note already carries (e.g. the director's own uploads), so the
    `max_files`/`max_message` budget for this note -- defaulting to the
    store's ordinary limits, but overridable by a caller using a different
    budget for this note (e.g. the first note's higher limits) -- is
    honored for the combined set, not just the pages gathered here. Once
    that budget (minus one slot reserved for the index itself) is spent,
    remaining page attachments are skipped and noted rather than silently
    exceeding it. What is uploaded first when the budget is short, every
    page's before the next kind: the themes (tiny, and the hardest to guess),
    then the screenshots, then the text, then the images."""
    max_files = getattr(store, 'max_files', None) if max_files is None else max_files
    max_message = getattr(store, 'max_message', None) if max_message is None else max_message
    budget_files = None if max_files is None else max(0, max_files - reserved_files - 1)
    budget_bytes = None if max_message is None else max(0, max_message - reserved_bytes)
    tiers = ([], [], [], [])
    for n, page in enumerate(pages, 1):
        if page.get('theme'):
            tiers[0].append((n, 3, 'theme', f'page-{n}-theme.md', 'text/plain', page['theme'].encode('utf-8')))
        tiers[1].append((n, 1, 'desktop screenshot', f'page-{n}-desktop.png', 'image/png', page['desktop_png']))
        tiers[1].append((n, 2, 'phone screenshot', f'page-{n}-phone.png', 'image/png', page['phone_png']))
        tiers[2].append((n, 0, 'text', f'page-{n}.txt', 'text/plain', page['text'].encode('utf-8')))
        for k, image in enumerate(page.get('images') or (), 1):
            tiers[3].append((n, 3 + k, f"image {image['url']}", f"page-{n}-image-{k}.{IMAGE_TYPES[image['type']]}",
                             image['type'], image['data']))
    ids = []
    results = collections.defaultdict(list)
    spent_files = spent_bytes = 0
    limit_hit = False
    max_file = getattr(store, 'max_file', None)
    for n, rank, label, name, ctype, data in (item for tier in tiers for item in tier):
        if not data:
            continue
        if ((budget_files is not None and spent_files >= budget_files) or
                (budget_bytes is not None and spent_bytes + len(data) > budget_bytes)):
            results[n].append((rank, f'   {label}: skipped (attachment limit reached)'))
            limit_hit = True
            continue
        oversize = max_file is not None and len(data) > max_file
        try:
            record = store.upload(video, name, ctype, data, allow_oversize=oversize)
        except ValueError as exc:
            results[n].append((rank, f'   {label}: skipped ({exc})'))
            continue
        spent_files += 1
        spent_bytes += record['size']
        suffix = ' (file size limit raised to fit)' if oversize else ''
        ids.append(record['id'])
        results[n].append((rank, f"   {label}: {record['name']}{suffix}"))
    lines = ['# Gathered pages', '']
    for n, page in enumerate(pages, 1):
        lines.append(f"{n}. {page['title'] or '(untitled)'} -- {page['url']}")
        # Listed in a fixed order (text, screenshots, theme, images), however the budget ordered the uploads.
        lines += [line for _, line in sorted(results[n])]
        for url, reason in page.get('skipped') or ():
            lines.append(f'   - {url}: {reason}')
    for url, reason in errors:
        lines.append(f'- skipped {url}: {reason}')
    if limit_hit:
        lines.append('')
        lines.append('Some gathered attachments were skipped: the note attachment limit was reached.')
    index_data = '\n'.join(lines).encode('utf-8')
    # The index is itself an attachment: it must fit the same combined-set budget as
    # everything else, or the note ends up with max_files+1 attachments (or over
    # max_message) despite every check above passing.
    fits_files = max_files is None or reserved_files + spent_files + 1 <= max_files
    fits_bytes = max_message is None or reserved_bytes + spent_bytes + len(index_data) <= max_message
    if not (fits_files and fits_bytes):
        return ids
    index = store.upload(video, 'gathered-pages.md', 'text/plain', index_data)
    return [index['id'], *ids]
