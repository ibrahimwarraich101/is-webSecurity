"""Live HTTP regression checks. Start app.py before running this file."""
import html
import re
import unittest
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE = 'http://localhost:8000'


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(self, mode, path, data=None, origin=None):
        headers = {'Origin': origin or BASE} if data is not None else {}
        req = Request(BASE + '/' + mode + path, urlencode(data).encode() if data is not None else None, headers)
        try:
            response = self.client.open(req)
        except HTTPError as exc:
            response = exc
        return response.status, response.read().decode()

    def login(self, mode):
        status, body = self.request(mode, '/login', {'username': 'student', 'password': 'StudentPass!26'})
        self.assertEqual(status, 200)
        return re.search(r'name="csrf_token" value="([^"]+)"', body)[1]

    def test_login_injection(self):
        for mode, status in [('vulnerable', 200), ('safe', 401)]:
            code, body = self.request(mode, '/login', {'username': "admin' -- ", 'password': 'wrong'})
            self.assertEqual(code, status)
            if mode == 'vulnerable':
                self.assertIn('administrator', body)

    def test_boolean_inference(self):
        for mode in ('vulnerable', 'safe'):
            for predicate, found in [('1=1', True), ('1=2', False), ("substr((SELECT password FROM users WHERE username='admin'),1,1)='A'", True), ("substr((SELECT password FROM users WHERE username='admin'),1,1)='Z'", False)]:
                payload = "ENR-2026-001' AND " + predicate + ' -- '
                code, body = self.request(mode, '/enrollment?' + urlencode({'reference': payload}))
                self.assertEqual(code, 200)
                self.assertEqual('Enrollment found' in body, found and mode == 'vulnerable')

    def test_advanced_chain(self):
        stages = [
            ("' ORDER BY 3 -- ", 200, None),
            ("' ORDER BY 4 -- ", 400, 'ORDER BY'),
            ("' UNION SELECT 'DATABASE',name,file FROM pragma_database_list -- ", 200, 'main'),
            ("' UNION SELECT 'TABLE',name,sql FROM sqlite_master WHERE type='table' -- ", 200, 'users'),
            ("' UNION SELECT 'COLUMN',name,type FROM pragma_table_info('users') -- ", 200, 'password'),
            ("' UNION SELECT username,password,email FROM users -- ", 200, 'AdminPass!26'),
        ]
        for payload, status, marker in stages:
            code, body = self.request('vulnerable', '/courses?' + urlencode({'q': payload}))
            self.assertEqual(code, status)
            if marker:
                self.assertIn(marker, body)
            code, body = self.request('safe', '/courses?' + urlencode({'q': payload}))
            self.assertEqual(code, 200)
            self.assertIn('No courses found.', body)
            self.assertNotIn('<h2>AdminPass!26</h2>', body)

    def test_reflected_encoding(self):
        payload = '<img src=x onerror="document.body.dataset.xss=1">'
        for mode in ('vulnerable', 'safe'):
            code, body = self.request(mode, '/courses?' + urlencode({'q': payload}))
            self.assertEqual(code, 200)
            self.assertIn('Search results for: ' + (payload if mode == 'vulnerable' else html.escape(payload)), body)

    def test_stored_encoding(self):
        payload = '<img src=x onerror="document.body.dataset.stored=1">'
        for mode in ('vulnerable', 'safe'):
            token = self.login(mode)
            self.request(mode, '/discussion', {'body': payload, 'csrf_token': token})
            _, body = self.request(mode, '/discussion')
            self.assertIn(payload if mode == 'vulnerable' else html.escape(payload), body)

    def test_csrf_and_normal_update(self):
        for mode in ('vulnerable', 'safe'):
            token = self.login(mode)
            code, body = self.request(mode, '/profile', {'email': 'student@campushub.invalid', 'csrf_token': token})
            self.assertEqual(code, 200)
            code, body = self.request(mode, '/profile', {'email': 'attacker@lab.invalid'}, 'http://127.0.0.1:8001')
            self.assertEqual(code, 200 if mode == 'vulnerable' else 403)
            _, body = self.request(mode, '/profile')
            self.assertIn('Current email: ' + ('attacker@lab.invalid' if mode == 'vulnerable' else 'student@campushub.invalid'), body)
            if mode == 'safe':
                code, _ = self.request(mode, '/profile', {'email': 'attacker@lab.invalid', 'csrf_token': token}, 'http://127.0.0.1:8001')
                self.assertEqual(code, 403)
                code, _ = self.request(mode, '/profile', {'email': 'attacker@lab.invalid'})
                self.assertEqual(code, 403)


if __name__ == '__main__':
    unittest.main(verbosity=2)
