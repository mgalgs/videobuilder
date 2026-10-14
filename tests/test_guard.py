"""The address guard: refused ranges, port rule, DNS-rebinding-safe resolve,
and the forward proxy that enforces it for every connection the gatherer
makes."""
import ipaddress
import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

from videobuilder import guard


class CheckAddress(unittest.TestCase):
    def refused(self, ip):
        with self.assertRaises(guard.Refused):
            guard.check_address(ipaddress.ip_address(ip))

    def allowed(self, ip):
        guard.check_address(ipaddress.ip_address(ip))  # must not raise

    def test_ipv4_refused_ranges(self):
        for ip in ('127.0.0.1', '10.0.0.1', '172.16.0.5', '192.168.1.1', '169.254.1.1',
                  '100.64.0.1', '100.100.0.1', '224.0.0.1', '240.0.0.1', '0.0.0.0'):
            self.refused(ip)

    def test_ipv6_refused_ranges(self):
        for ip in ('::1', 'fe80::1', 'fc00::1', 'fd12:3456:789a::1', 'ff02::1', '::'):
            self.refused(ip)

    def test_public_addresses_allowed(self):
        for ip in ('93.184.216.34', '8.8.8.8', '2606:4700:4700::1111'):
            self.allowed(ip)

    def test_loopback_allowed_only_with_the_test_switch(self):
        self.refused('127.0.0.1')
        guard.check_address(ipaddress.ip_address('127.0.0.1'), allow_loopback=True)

    def test_cgnat_boundaries(self):
        self.allowed('100.63.255.255')
        self.refused('100.64.0.0')
        self.refused('100.127.255.255')
        self.allowed('100.128.0.0')

    def test_ipv4_mapped_ipv6_literals_classified_as_ipv4(self):
        self.refused('::ffff:100.64.0.1')  # CGNAT, mapped -- not caught by IPv6 is_private
        self.refused('::ffff:10.0.0.1')
        self.refused('::ffff:127.0.0.1')
        self.allowed('::ffff:93.184.216.34')


class CheckPort(unittest.TestCase):
    def test_only_80_and_443_allowed(self):
        guard.check_port(80)
        guard.check_port(443)
        for port in (22, 8080, 8443, 0, 65535):
            with self.assertRaises(guard.Refused):
                guard.check_port(port)


class ResolveAndCheck(unittest.TestCase):
    def test_hostname_resolving_to_a_private_address_is_refused(self):
        infos = [(socket.AF_INET, socket.SOCK_STREAM, 0, '', ('10.1.2.3', 443))]
        with mock.patch('socket.getaddrinfo', return_value=infos):
            with self.assertRaises(guard.Refused):
                guard.resolve_and_check('evil.example', 443)

    def test_public_address_is_returned(self):
        infos = [(socket.AF_INET, socket.SOCK_STREAM, 0, '', ('93.184.216.34', 443))]
        with mock.patch('socket.getaddrinfo', return_value=infos):
            family, sockaddr = guard.resolve_and_check('example.com', 443)
        self.assertEqual(sockaddr, ('93.184.216.34', 443))

    def test_disallowed_port_refused_before_any_lookup(self):
        with mock.patch('socket.getaddrinfo') as lookup:
            with self.assertRaises(guard.Refused):
                guard.resolve_and_check('example.com', 8080)
            lookup.assert_not_called()

    def test_every_resolved_address_is_checked_not_just_the_first(self):
        # A host that answers with one public and one private address: an attacker's
        # best shot at slipping a bad address past a guard that only checks the first.
        infos = [(socket.AF_INET, socket.SOCK_STREAM, 0, '', ('93.184.216.34', 443)),
                (socket.AF_INET, socket.SOCK_STREAM, 0, '', ('10.0.0.1', 443))]
        with mock.patch('socket.getaddrinfo', return_value=infos):
            with self.assertRaises(guard.Refused):
                guard.resolve_and_check('mixed.example', 443)

    def test_no_second_lookup_for_the_connect(self):
        # The guard resolves once; a second lookup at connect time is exactly what
        # DNS rebinding needs (a safe answer for the check, a private one to connect to).
        infos = [(socket.AF_INET, socket.SOCK_STREAM, 0, '', ('93.184.216.34', 443))]
        calls = []
        def fake_getaddrinfo(host, port, **kw):
            calls.append(host)
            return infos
        with mock.patch('socket.getaddrinfo', side_effect=fake_getaddrinfo):
            guard.resolve_and_check('example.com', 443)
        self.assertEqual(calls, ['example.com'])


class _OK(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'ok')

    def log_message(self, *a):
        pass


class _Redirect(BaseHTTPRequestHandler):
    """Answers every request with a redirect to a private address: the proxy,
    not just the first hostname check, must refuse the hop."""

    def do_GET(self):
        self.send_response(302)
        self.send_header('Location', 'http://10.1.2.3/secret')
        self.end_headers()

    def log_message(self, *a):
        pass


class _RedirectBadPort(BaseHTTPRequestHandler):
    """Redirects to a public address on a disallowed port: isolates the port
    rule from the address rule, both of which `allow_loopback` leaves alone
    for anything other than loopback itself."""

    def do_GET(self):
        self.send_response(302)
        self.send_header('Location', 'http://93.184.216.34:8080/')
        self.end_headers()

    def log_message(self, *a):
        pass


class GuardProxyTest(unittest.TestCase):
    def serve(self, handler_cls):
        server = HTTPServer(('127.0.0.1', 0), handler_cls)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        return server.server_address[1]

    def test_allowed_fetch_through_the_proxy(self):
        port = self.serve(_OK)
        proxy = guard.GuardProxy(allow_loopback=True)
        self.addCleanup(proxy.close)
        opener = guard.opener(proxy.port)
        with opener.open(f'http://127.0.0.1:{port}/', timeout=5) as response:
            self.assertEqual(response.read(), b'ok')

    def test_without_the_test_switch_loopback_is_refused_even_through_the_proxy(self):
        port = self.serve(_OK)
        proxy = guard.GuardProxy(allow_loopback=False)
        self.addCleanup(proxy.close)
        opener = guard.opener(proxy.port)
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            opener.open(f'http://127.0.0.1:{port}/', timeout=5)
        self.assertEqual(ctx.exception.code, 502)

    def test_a_redirect_to_a_private_address_is_refused_by_the_proxy(self):
        port = self.serve(_Redirect)
        proxy = guard.GuardProxy(allow_loopback=True)
        self.addCleanup(proxy.close)
        opener = guard.opener(proxy.port)
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            opener.open(f'http://127.0.0.1:{port}/', timeout=5)
        self.assertEqual(ctx.exception.code, 502)
        self.assertTrue(any('10.1.2.3' in host for host, _ in proxy.log))

    def test_disallowed_port_refused_on_a_non_loopback_address(self):
        # allow_loopback relaxes the port rule only for loopback itself (a test fixture
        # is necessarily on some ephemeral port); a non-loopback address, such as this
        # redirect's target, still needs an allowed port even in that mode.
        port = self.serve(_RedirectBadPort)
        proxy = guard.GuardProxy(allow_loopback=True)
        self.addCleanup(proxy.close)
        opener = guard.opener(proxy.port)
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            opener.open(f'http://127.0.0.1:{port}/', timeout=5)
        self.assertEqual(ctx.exception.code, 502)


class ChromiumArgs(unittest.TestCase):
    def test_proxy_server_and_bypass_list_route_everything_through_the_guard(self):
        args = guard.chromium_proxy_args(12345)
        self.assertIn('--proxy-server=127.0.0.1:12345', args)
        self.assertIn('--proxy-bypass-list=<-loopback>', args)


if __name__ == '__main__':
    unittest.main()
