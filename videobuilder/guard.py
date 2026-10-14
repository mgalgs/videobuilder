"""The address guard: the gatherer's one security boundary.

A link given to "start a video from scratch" is fetched from the editor's own
pod, which usually sits on a home network. Nothing a link points at -- the
page itself, a redirect, a subresource Chromium loads on its own, or a
rebound DNS answer -- may reach anywhere on that network. `check_address`
and `resolve_and_check` are the policy; `GuardProxy` is a tiny HTTP/HTTPS
forward proxy that enforces it for every connection the gatherer makes,
whether from Chromium (via --proxy-server) or from Python's own fetches (via
an opener built with `opener()`), so there is exactly one place this is
decided.

Resolving a host and connecting to it are kept as one step on purpose:
checking the hostname and then letting the OS resolve it again for the
connect is exactly what a DNS-rebinding attack needs (a first, innocuous
answer for the check, a second, private one for the real connection).
`resolve_and_check` resolves once, validates every address it got back, and
hands back the address to connect to; nothing downstream resolves again.
"""
import ipaddress
import re
import socket
import threading
import time

ALLOWED_PORTS = (80, 443)
CGNAT = ipaddress.ip_network('100.64.0.0/10')


class Refused(ValueError):
    """An address, port or host the guard will not let the gatherer reach."""


def check_address(ip, allow_loopback=False):
    """Raise Refused unless `ip` (an ipaddress.IPv4Address/IPv6Address) is a
    public, routable address. `allow_loopback` is a test-only escape hatch for
    exercising the guard against a fixture server on 127.0.0.1; production
    code must never pass it."""
    # An IPv4-mapped IPv6 literal (::ffff:a.b.c.d) is the same address as
    # a.b.c.d; classify it as IPv4 so the CGNAT check below (which Python's
    # own is_private does not cover, mapped or not) actually sees it.
    mapped = getattr(ip, 'ipv4_mapped', None)
    if mapped is not None:
        ip = mapped
    if ip.is_loopback:
        if allow_loopback:
            return ip
        raise Refused(f'{ip} is a loopback address')
    if ip.is_link_local:
        raise Refused(f'{ip} is a link-local address')
    if ip.is_multicast:
        raise Refused(f'{ip} is a multicast address')
    if ip.is_reserved:
        raise Refused(f'{ip} is a reserved address')
    if ip.is_unspecified:
        raise Refused(f'{ip} is unspecified')
    if isinstance(ip, ipaddress.IPv4Address):
        if ip.is_private:
            raise Refused(f'{ip} is a private address')
        if ip in CGNAT:
            raise Refused(f'{ip} is a CGNAT address')
    elif ip.is_private:  # IPv6: unique-local (fc00::/7) and friends
        raise Refused(f'{ip} is a unique-local address')
    return ip


def check_port(port):
    if port not in ALLOWED_PORTS:
        raise Refused(f'port {port} is not allowed (only 80 and 443)')
    return port


def resolve_and_check(host, port, allow_loopback=False):
    """Resolve `host` once, check every address it resolves to, and return
    one (family, sockaddr) to connect to -- never resolving `host` again.

    The port rule is skipped for an address `allow_loopback` admits: a test
    fixture a crawl test serves on 127.0.0.1 is necessarily on some ephemeral
    port, not 80 or 443, and there is no other way to exercise the gatherer
    against it. Any address that is not itself loopback -- in particular a
    redirect's target, however `allow_loopback` is set -- still needs an
    allowed port."""
    if not allow_loopback:
        check_port(port)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise Refused(f'could not resolve {host}: {exc}') from None
    if not infos:
        raise Refused(f'{host} did not resolve to any address')
    checked = []
    for family, socktype, proto, canonname, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0].split('%')[0])
        check_address(ip, allow_loopback=allow_loopback)
        if not (allow_loopback and ip.is_loopback):
            check_port(port)
        checked.append((family, sockaddr))
    return checked[0]


def _recv_line(conn, limit=8192):
    data = b''
    while not data.endswith(b'\r\n'):
        chunk = conn.recv(1)
        if not chunk:
            break
        data += chunk
        if len(data) > limit:
            raise ValueError('request line too long')
    return data


def _recv_headers(conn):
    headers = {}
    while True:
        line = _recv_line(conn).rstrip(b'\r\n')
        if not line:
            return headers
        key, _, value = line.decode('latin-1').partition(':')
        headers[key.strip().lower()] = value.strip()


class GuardProxy:
    """A loopback-only HTTP/HTTPS forward proxy enforcing the address guard
    on every connection it makes, for Chromium (via --proxy-server) and for
    Python's own fetches (via `opener`) alike. `log` collects refusals as
    (host, reason) pairs for the gatherer to report."""

    def __init__(self, allow_loopback=False, timeout=20):
        self.allow_loopback = allow_loopback
        self.timeout = timeout
        self.log = []
        self._lock = threading.Lock()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(('127.0.0.1', 0))
        self._socket.listen(128)
        self.port = self._socket.getsockname()[1]
        self._stopping = False
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def close(self):
        self._stopping = True
        try:
            self._socket.close()
        except OSError:
            pass
        self._thread.join(timeout=5)

    def _refuse(self, host):
        with self._lock:
            self.log.append((host, 'blocked address'))

    def _serve(self):
        while not self._stopping:
            try:
                self._socket.settimeout(0.5)
                conn, _ = self._socket.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        try:
            conn.settimeout(self.timeout)
            request_line = _recv_line(conn)
            if not request_line:
                return
            parts = request_line.decode('latin-1', 'replace').strip().split(' ')
            if len(parts) != 3:
                return
            method, target, _version = parts
            headers = _recv_headers(conn)
            if method.upper() == 'CONNECT':
                self._tunnel(conn, target)
            else:
                self._forward(conn, method, target, headers)
        except (Refused, ValueError, OSError, socket.timeout):
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _dial(self, host, port):
        family, sockaddr = resolve_and_check(host, port, self.allow_loopback)
        upstream = socket.socket(family, socket.SOCK_STREAM)
        upstream.settimeout(self.timeout)
        upstream.connect(sockaddr)
        return upstream

    def _tunnel(self, conn, target):
        host, _, port = target.partition(':')
        try:
            upstream = self._dial(host, int(port or 443))
        except Refused:
            self._refuse(target)
            conn.sendall(b'HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n')
            return
        try:
            conn.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            _splice(conn, upstream)
        finally:
            upstream.close()

    def _forward(self, conn, method, target, headers):
        from urllib.parse import urlsplit
        split = urlsplit(target)
        host = split.hostname
        port = split.port or (443 if split.scheme == 'https' else 80)
        if not host:
            conn.sendall(b'HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n')
            return
        length = int(headers.get('content-length') or 0)
        body = conn.recv(length) if length else b''
        try:
            upstream = self._dial(host, port)
        except Refused:
            self._refuse(target)
            conn.sendall(b'HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n')
            return
        try:
            path = split.path or '/'
            if split.query:
                path += '?' + split.query
            out = [f'{method} {path} HTTP/1.1'.encode()]
            sent_host = False
            for key, value in headers.items():
                if key in ('proxy-connection', 'connection'):
                    continue
                if key == 'host':
                    sent_host = True
                out.append(f'{key}: {value}'.encode())
            if not sent_host:
                out.append(f'Host: {host}'.encode())
            out.append(b'Connection: close')
            request = b'\r\n'.join(out) + b'\r\n\r\n' + body
            upstream.sendall(request)
            while True:
                chunk = upstream.recv(65536)
                if not chunk:
                    break
                conn.sendall(chunk)
        finally:
            upstream.close()


def _splice(a, b, bufsize=65536):
    """Relay bytes both ways between two connected sockets until either side
    closes."""
    done = threading.Event()

    def pump(src, dst):
        try:
            while True:
                chunk = src.recv(bufsize)
                if not chunk:
                    break
                dst.sendall(chunk)
        except OSError:
            pass
        finally:
            done.set()
            try:
                dst.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    t = threading.Thread(target=pump, args=(a, b), daemon=True)
    t.start()
    pump(b, a)
    t.join(timeout=5)


def opener(proxy_port):
    """A urllib opener routing both http and https through the guard proxy at
    `proxy_port` -- the same instance Chromium is launched against, so a
    fetch made from Python answers to the same guard."""
    import urllib.request
    proxy = f'127.0.0.1:{proxy_port}'
    return urllib.request.build_opener(urllib.request.ProxyHandler({'http': proxy, 'https': proxy}))


def chromium_proxy_args(proxy_port):
    """The --proxy-server/--proxy-bypass-list flags that route every request
    Chromium makes -- navigation, redirects and subresources alike -- through
    the guard, with the bypass list disabled so nothing goes direct. WebRTC
    ignores --proxy-server by default and sends UDP (STUN/ICE) straight to
    whatever address a page names, so it is disabled separately."""
    return [f'--proxy-server=127.0.0.1:{proxy_port}', '--proxy-bypass-list=<-loopback>',
            '--force-webrtc-ip-handling-policy=disable_non_proxied_udp']
