"""HTTP-level tests for the community-capabilities feature: the reserved
namespace end to end (commit 2), then submission, drafts/publish and the
builder context in later commits. Every test that sends an X post URL mocks
videobuilder.xpost._open -- no test here touches the network."""
import unittest

from tests import fixtures


class Reserved(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def test_videos_new_refuses_reserved_names(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        headers = {'Content-Type': 'application/json', 'Cookie': admin}
        for name, start in (('capabilities', 'blank'), ('capabilities/x', 'blank'),
                            ('capabilities', 'copy'), ('capabilities/x', 'copy')):
            with self.subTest(name=name, start=start):
                body = {'name': name, 'start': start}
                if start == 'copy':
                    body['from'] = 'acme/launch'
                code, data, _ = self.request_full('/api/videos/new', body, headers=headers)
                self.assertEqual(code, 400, data)
                self.assertIn('reserved', data['error'])
                self.assertFalse(self.library.path(name).exists())

    def test_library_new_refuses_reserved_target(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        code, data, _ = self.request_full('/api/library/new', {'from': 'acme/launch', 'name': 'capabilities/copy1'},
                                          headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 400, data)
        self.assertIn('reserved', data['error'])
        self.assertFalse(self.library.path('capabilities/copy1').exists())

    def test_git_push_create_refused_in_reserved_namespace(self):
        work = self.root / 'push-source'
        self.git('init', '-b', 'main', str(work))
        (work / 'README.md').write_text('hi\n')
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'first', cwd=work)
        self.git('remote', 'add', 'origin', self.url('capabilities/pushed'), cwd=work)
        result = self.git('push', '-u', 'origin', 'main', cwd=work, ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.library.path('capabilities/pushed').exists())

    def test_signup_refuses_capabilities_username(self):
        for name in ('capabilities', 'Capabilities'):
            with self.subTest(name=name):
                code, data, cookie = self.signup(name, 'longenoughpassword')
                self.assertEqual(code, 400, data)
                self.assertIn('reserved', data['error'])


if __name__ == '__main__':
    unittest.main()
