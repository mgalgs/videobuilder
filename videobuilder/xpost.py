"""Reads a single X (Twitter) post from the public syndication JSON, for the
capability-submission dialog's optional "I saw this on X" URL. This is the
only module in videobuilder that reaches the network on a creator's behalf,
so every network call is capped and allowlisted:

- `parse_url` accepts only `https://(x.com|twitter.com|mobile.twitter.com)
  /<user>/status/<id>` (optionally `www.`-prefixed, a trailing slash, and a
  query/fragment); anything else is refused before any network call.
- The post itself is read from `syndication_url` -- `token` is a faithful
  port of V8's `DoubleToRadixCString` (radix 36), verified against a real
  `node` for the pair id=1585341984679469056 -> token=3uchycv2wqc (see
  test_verified_token_pair) and against hundreds of random ids.
- Media is only ever fetched from MEDIA_HOSTS (`pbs.twimg.com`,
  `video.twimg.com`); a redirect that leaves SYNDICATION_HOST or
  MEDIA_HOSTS is refused (`_AllowlistRedirect`), and the final URL is
  re-checked after any redirect in case a mocked response disagrees.
- Every fetch is capped in bytes (checked from Content-Length before the
  body is read, and again as bytes actually arrive) and the whole read --
  the syndication JSON plus every media download -- is capped in wall time
  (`read_post`'s `now`, injectable for tests).

`_open` is the single seam every test here patches: this sandbox has no
network, and CI must not depend on X being reachable.
"""
import json
import math
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .attachments import TYPES

URL_RE = re.compile(
    r'\Ahttps://(?:www\.)?(?:x\.com|twitter\.com|mobile\.twitter\.com)'
    r'/(?P<user>[A-Za-z0-9_]{1,15})/status/(?P<id>\d{1,19})/?(?:[?#].*)?\Z', re.I)

SYNDICATION_HOST = 'cdn.syndication.twimg.com'
MEDIA_HOSTS = ('pbs.twimg.com', 'video.twimg.com')

JSON_MAX_BYTES = 1 << 20
PHOTO_MAX_BYTES = 10 * (1 << 20)
PHOTO_MAX_COUNT = 4
VIDEO_MAX_BYTES = 50_000_000
TOTAL_TIME_BUDGET = 60.0
SOCKET_TIMEOUT = 15.0
MAX_REDIRECTS = 3
CHUNK = 1 << 16

_PHOTO_EXTS = {'jpg', 'jpeg', 'png', 'webp'}
_WH_RE = re.compile(r'/(\d+)x(\d+)/')


def parse_url(url):
    """(user, id) for an accepted X/Twitter post URL; raises ValueError for
    anything else, including a non-string, before any network call."""
    if not isinstance(url, str):
        raise ValueError('url must be a string')
    m = URL_RE.match(url)
    if not m:
        raise ValueError('not a recognized X post URL')
    return m.group('user'), m.group('id')


_CHARS = '0123456789abcdefghijklmnopqrstuvwxyz'


def _radix36(value):
    """A faithful port of V8's DoubleToRadixCString for radix 36: `value`
    (a positive float) as V8's `Number.prototype.toString(36)` would render
    it, integer and fractional part, with the same round-half-even and
    carry-back rules a binary-to-decimal-ish radix conversion needs to stop
    at the double's own precision. Verified against a real `node` for the
    brief's pair and hundreds of random ids (see test_verified_token_pair)."""
    integer = int(value)  # value is always small and positive here (a few thousand at most)
    fraction = value - integer
    delta = 0.5 * (math.nextafter(value, math.inf) - value)
    delta = max(math.nextafter(0.0, 1.0), delta)
    frac_digits = []
    if fraction >= delta:
        while True:
            fraction *= 36
            delta *= 36
            digit = int(fraction)
            frac_digits.append(digit)
            fraction -= digit
            if fraction > 0.5 or (fraction == 0.5 and (digit & 1)):
                if fraction + delta > 1:
                    while True:
                        if not frac_digits:
                            integer += 1
                            break
                        last = frac_digits.pop()
                        if last + 1 < 36:
                            frac_digits.append(last + 1)
                            break
                    break
            if not (fraction >= delta):
                break
    int_digits = []
    n = integer
    if n == 0:
        int_digits.append(0)
    else:
        while n > 0:
            n, rem = divmod(n, 36)
            int_digits.append(rem)
        int_digits.reverse()
    s = ''.join(_CHARS[d] for d in int_digits)
    if frac_digits:
        s += '.' + ''.join(_CHARS[d] for d in frac_digits)
    return s


def token(id):
    """The syndication endpoint's per-id token, as the embed widget's own
    JavaScript computes it: `((Number(id) / 1e15) * Math.PI).toString(36)`
    with every '0' and '.' stripped."""
    value = (float(int(id)) / 1e15) * math.pi
    return re.sub(r'(0+|\.)', '', _radix36(value))


def syndication_url(id):
    return f'https://{SYNDICATION_HOST}/tweet-result?id={id}&token={token(id)}'


def _video_rank(item, index):
    bitrate = item.get('bitrate')
    if isinstance(bitrate, (int, float)) and not isinstance(bitrate, bool):
        return (2, bitrate, -index)
    m = _WH_RE.search(item.get('url') or '')
    if m:
        return (1, int(m.group(1)) * int(m.group(2)), -index)
    return (0, 0, -index)


def _variants_from_video_info(info):
    out = []
    for v in (info.get('variants') or []):
        if not isinstance(v, dict):
            continue
        ctype, url = v.get('content_type'), v.get('url')
        if isinstance(ctype, str) and isinstance(url, str):
            out.append({'content_type': ctype, 'url': url, 'bitrate': v.get('bitrate')})
    return out


def parse(data):
    """{text, handle, photos:[url], videos:[url, best mp4 first]} from the
    syndication JSON: text and user.screen_name verbatim (handle dropped
    unless it looks like a real username); photos from mediaDetails[] where
    type == 'photo' (media_url_https); mp4 video variants (HLS skipped)
    from both mediaDetails[].video_info.variants and a top-level
    video.variants, ranked by bitrate if given, else by width*height read
    from a `/<w>x<h>/` path segment, else by listed order."""
    text = data.get('text')
    text = text if isinstance(text, str) else None
    user = data.get('user')
    handle = user.get('screen_name') if isinstance(user, dict) else None
    if not (isinstance(handle, str) and re.fullmatch(r'[A-Za-z0-9_]{1,15}', handle)):
        handle = None
    photos = []
    candidates = []
    media_details = data.get('mediaDetails')
    if isinstance(media_details, list):
        for item in media_details:
            if not isinstance(item, dict):
                continue
            if item.get('type') == 'photo':
                url = item.get('media_url_https')
                if isinstance(url, str):
                    photos.append(url)
            elif item.get('type') in ('video', 'animated_gif'):
                info = item.get('video_info')
                if isinstance(info, dict):
                    candidates += _variants_from_video_info(info)
    top_video = data.get('video')
    if isinstance(top_video, dict):
        for v in (top_video.get('variants') or []):
            if not isinstance(v, dict):
                continue
            ctype, url = v.get('type'), v.get('src')
            if isinstance(ctype, str) and isinstance(url, str):
                candidates.append({'content_type': ctype, 'url': url, 'bitrate': None})
    seen = set()
    mp4 = []
    for item in candidates:
        if item['content_type'] != 'video/mp4' or item['url'] in seen:
            continue
        seen.add(item['url'])
        mp4.append(item)
    ranked = sorted(enumerate(mp4), key=lambda iv: _video_rank(iv[1], iv[0]), reverse=True)
    return {'text': text, 'handle': handle, 'photos': photos[:PHOTO_MAX_COUNT],
           'videos': [item['url'] for _, item in ranked]}


class _AllowlistRedirect(urllib.request.HTTPRedirectHandler):
    """Refuses to follow a redirect that leaves `hosts` (scheme must stay
    https too); raising HTTPError here is urllib's documented way for a
    redirect handler to refuse a redirect outright."""
    max_redirections = MAX_REDIRECTS

    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != 'https' or (parsed.hostname or '').lower() not in self.hosts:
            raise urllib.error.HTTPError(newurl, code, 'redirect host not allowed', headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(request, hosts, timeout):
    """The single network seam: every test here patches this. Builds an
    opener that refuses a redirect leaving `hosts` (see
    _AllowlistRedirect) and opens `request` with it."""
    opener = urllib.request.build_opener(_AllowlistRedirect(hosts))
    return opener.open(request, timeout=timeout)


def _fetch(url, hosts, max_bytes, deadline):
    """`url`'s bytes, refusing before any network call if it isn't https on
    one of `hosts`; refusing a Content-Length over `max_bytes` before the
    body is read, and the streamed body if it grows past it; refusing if
    `deadline` (a time.monotonic() value) passes first, mid-read or before
    starting. The final URL (after any redirect) is re-checked against
    `hosts` too, belt and braces over _AllowlistRedirect."""
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or (parsed.hostname or '').lower() not in hosts:
        raise ValueError('refusing to fetch from this host')
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('time budget exceeded')
    request = urllib.request.Request(url, headers={'User-Agent': 'videobuilder-capability-fetch/1'})
    response = _open(request, hosts, min(SOCKET_TIMEOUT, remaining))
    try:
        final = urlsplit(response.geturl())
        if final.scheme != 'https' or (final.hostname or '').lower() not in hosts:
            raise ValueError('redirected off the allowed hosts')
        length = response.headers.get('Content-Length')
        if length is not None and int(length) > max_bytes:
            raise ValueError('response exceeds the size cap')
        data = bytearray()
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError('time budget exceeded')
            chunk = response.read(CHUNK)
            if not chunk:
                break
            data += chunk
            if len(data) > max_bytes:
                raise ValueError('response exceeds the size cap')
        return bytes(data)
    finally:
        close = getattr(response, 'close', None)
        if close:
            close()


def _photo_ext(url):
    leaf = urlsplit(url).path.rsplit('/', 1)[-1]
    ext = leaf.rsplit('.', 1)[-1].lower() if '.' in leaf else ''
    return ext if ext in _PHOTO_EXTS else 'jpg'


@dataclass
class Post:
    ok: bool
    error: str | None = None
    text: str | None = None
    handle: str | None = None
    media: list = field(default_factory=list)  # [(name, content_type, bytes), ...]


def read_post(url, now=time.monotonic):
    """Reads one X post: the syndication JSON, then its photos (up to
    PHOTO_MAX_COUNT) and the single best mp4 video variant that fits under
    VIDEO_MAX_BYTES (falling back to the next-best variant if one is too
    big). Raises ValueError if `url` itself is malformed -- before any
    network call -- so the caller can tell that apart from a read that was
    attempted and failed (`ok=False`): a failure is the JSON fetch/parse
    failing outright, or the post having media but none of it downloading;
    whatever text/handle/media *did* come back is still returned either
    way. `now`, injectable for tests, bounds the whole read (JSON plus
    every media download) to TOTAL_TIME_BUDGET seconds from this call."""
    parse_url(url)
    deadline = now() + TOTAL_TIME_BUDGET
    user, id = parse_url(url)
    try:
        raw = _fetch(syndication_url(id), (SYNDICATION_HOST,), JSON_MAX_BYTES, deadline)
        data = json.loads(raw)
    except Exception:
        return Post(False, 'could not read the post')
    if not isinstance(data, dict):
        return Post(False, 'could not read the post')
    parsed = parse(data)
    media = []
    for n, photo_url in enumerate(parsed['photos'], 1):
        try:
            content = _fetch(photo_url, MEDIA_HOSTS, PHOTO_MAX_BYTES, deadline)
        except Exception:
            continue
        ext = _photo_ext(photo_url)
        media.append((f'x-photo-{n}.{ext}', TYPES[ext], content))
    for video_url in parsed['videos']:
        try:
            content = _fetch(video_url, MEDIA_HOSTS, VIDEO_MAX_BYTES, deadline)
        except Exception:
            continue
        media.append(('x-clip.mp4', 'video/mp4', content))
        break
    media_expected = bool(parsed['photos']) or bool(parsed['videos'])
    ok = not media_expected or bool(media)
    return Post(ok, None if ok else 'no media could be downloaded', parsed['text'], parsed['handle'], media)
