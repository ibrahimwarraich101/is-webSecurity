"""CampusHub: local, deliberately vulnerable web-security teaching lab."""
import argparse
import hashlib
import hmac
import html
import json
import secrets
import sqlite3
from datetime import datetime
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
SESSIONS = {}


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200000).hex()


def initialize(reset=False):
    (ROOT / 'data').mkdir(exist_ok=True)
    for mode in ('vulnerable', 'safe'):
        path = ROOT / 'data' / (mode + '.db')
        if reset and path.exists():
            path.unlink()
        if path.exists():
            continue
        with sqlite3.connect(path) as db:
            db.executescript((ROOT / 'seed-data.sql').read_text())
            if mode == 'safe':
                for uid, password in db.execute('SELECT id,password FROM users').fetchall():
                    db.execute('UPDATE users SET password=? WHERE id=?', (password_hash(password), uid))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(datetime.now().isoformat(timespec='seconds'), fmt % args, flush=True)

    def send(self, body, status=200, headers=None, kind='text/html; charset=utf-8'):
        raw = body.encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Cache-Control', 'no-store')
        if getattr(self, 'mode', '') == 'safe':
            # Encoding is the primary XSS defense; CSP adds defense in depth.
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            self.send_header('X-Content-Type-Options', 'nosniff')
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def redirect(self, path, headers=None):
        self.send('', 303, {'Location': path, **(headers or {})})

    def page(self, title, content, status=200):
        mode = self.mode
        session = self.session
        user = html.escape(session['username']) if session else 'Guest'
        links = [('Dashboard', ''), ('Courses', '/courses'), ('Discussion', '/discussion'), ('Study planner', '/planner'), ('Enrollment', '/enrollment'), ('My profile', '/profile'), ('Login', '/login')]
        nav = ''.join(f'<a href="/{mode}{p}">{t}</a>' for t, p in links)
        opposite = 'safe' if mode == 'vulnerable' else 'vulnerable'
        self.send(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} | CampusHub</title><link rel="stylesheet" href="/static/style.css"><script defer src="/static/app.js"></script></head>
        <body data-mode="{mode}"><aside><div class="logo">C<span>CampusHub</span></div><p class="muted">Your learning workspace</p><nav>{nav}</nav><div class="aside-bottom">Information Security · Part 2<br>Local learning environment</div></aside><main><header><span>ACADEMIC PORTAL / {html.escape(title).upper()}</span><span>{user} <a class="switch" href="/{opposite}">Switch to {opposite}</a></span></header><div class="mode {mode}">{mode.upper()} VERSION · {'Deliberately insecure lab' if mode == 'vulnerable' else 'Defenses enabled'}</div><section><h1>{html.escape(title)}</h1>{content}</section><footer>CampusHub · Python + SQLite · <time id="clock"></time></footer></main></body></html>''', status)

    def connect(self):
        db = sqlite3.connect(ROOT / 'data' / (self.mode + '.db'))
        db.row_factory = sqlite3.Row
        return db

    def token(self):
        return f'<input type="hidden" name="csrf_token" value="{self.session["csrf"]}">' if self.session else ''

    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)

    def handle_request(self, post):
        parsed = urlparse(self.path)
        if parsed.path == '/favicon.ico':
            return self.send('', 204, kind='image/x-icon')
        if parsed.path.startswith('/static/'):
            name = parsed.path.split('/')[-1]
            if name not in ('style.css', 'app.js'):
                return self.send('Not found', 404)
            return self.send((ROOT / 'static' / name).read_text(), kind='text/css' if name.endswith('css') else 'text/javascript')
        parts = parsed.path.strip('/').split('/')
        if parts[0] not in ('safe', 'vulnerable'):
            return self.redirect('/safe')
        self.mode = parts[0]
        route = '/' + '/'.join(parts[1:])
        params = parse_qs(parsed.query, keep_blank_values=True)
        if post:
            length = int(self.headers.get('Content-Length', '0'))
            if length > 16384:
                return self.send('Request too large', 413)
            params = parse_qs(self.rfile.read(length).decode(), keep_blank_values=True)
        value = lambda key, default='': params.get(key, [default])[0]
        cookies = SimpleCookie()
        try:
            cookies.load(self.headers.get('Cookie', ''))
        except Exception:
            pass
        cookie = cookies.get('campus_' + self.mode)
        self.session = SESSIONS.get(cookie.value) if cookie else None
        if self.session and self.session['mode'] != self.mode:
            self.session = None
        with self.connect() as db:
            try:
                if route == '/login':
                    if post:
                        username, password = value('username'), value('password')
                        if self.mode == 'vulnerable':
                            # Deliberate mistake: input changes the SQL grammar.
                            user = db.execute(f"SELECT * FROM users WHERE username='{username}' AND password='{password}'").fetchone()
                        else:
                            user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
                            if user and not hmac.compare_digest(password_hash(password, user['password'].split(':')[0]), user['password']):
                                user = None
                        if user:
                            sid = secrets.token_urlsafe(32)
                            SESSIONS[sid] = {'id': user['id'], 'username': user['username'], 'mode': self.mode, 'csrf': secrets.token_urlsafe(32)}
                            # Local HTTP: safe cookies use Lax; production HTTPS must also use Secure.
                            extra = '; SameSite=Lax' if self.mode == 'safe' else ''
                            return self.redirect('/' + self.mode + '/profile', {'Set-Cookie': f'campus_{self.mode}={sid}; Path=/{self.mode}; HttpOnly{extra}'})
                        return self.page('Login', '<div class="notice error">Invalid credentials. Login blocked.</div>' + self.login_form(), 401)
                    return self.page('Login', '<p class="lead">Sign in to manage your courses and student profile.</p>' + self.login_form())
                if route == '/profile':
                    if not self.session:
                        return self.redirect('/' + self.mode + '/login')
                    message = ''
                    if post:
                        if self.mode == 'safe':
                            expected = f'http://{self.headers.get("Host")}'
                            origin = self.headers.get('Origin')
                            if origin != expected or not hmac.compare_digest(value('csrf_token'), self.session['csrf']):
                                return self.page('Request blocked', '<div class="notice error">CSRF protection rejected the request. No profile changes were made.</div>', 403)
                        email = value('email')
                        if len(email) > 120 or '@' not in email:
                            return self.page('My profile', '<div class="notice error">Enter a valid email address.</div>', 400)
                        db.execute('UPDATE users SET email=? WHERE id=?', (email, self.session['id']))
                        message = '<div class="notice">Email updated successfully.</div>'
                    user = db.execute('SELECT * FROM users WHERE id=?', (self.session['id'],)).fetchone()
                    return self.page('My profile', message + f'<div class="card"><h2>{html.escape(user["username"])}</h2><p>Role: {html.escape(user["role"])}</p><p id="current-email">Current email: {html.escape(user["email"])}</p><form method="post">{self.token()}<label>Contact email<input name="email" value="{html.escape(user["email"], quote=True)}" required></label><button>Save changes</button></form></div>')
                if route == '/discussion':
                    if post:
                        if not self.session:
                            return self.redirect('/' + self.mode + '/login')
                        if self.mode == 'safe' and not hmac.compare_digest(value('csrf_token'), self.session['csrf']):
                            return self.page('Request blocked', '<p>Invalid CSRF token.</p>', 403)
                        db.execute('INSERT INTO comments(author,body) VALUES (?,?)', (self.session['username'], value('body')[:4000]))
                        return self.redirect('/' + self.mode + '/discussion')
                    comments = db.execute('SELECT * FROM comments ORDER BY id DESC').fetchall()
                    cards = ''.join(f'<article class="card"><h3>{html.escape(c["author"])}</h3><div>{html.escape(c["body"]) if self.mode == "safe" else c["body"]}</div></article>' for c in comments)
                    form = f'<form method="post" class="card">{self.token()}<label>Share a course update<textarea name="body" required></textarea></label><button>Post message</button></form>' if self.session else f'<p><a href="/{self.mode}/login">Sign in</a> to post a message.</p>'
                    return self.page('Course discussion', '<p class="lead">Questions, resources and ideas from your classmates.</p>' + form + cards)
                if route == '/planner':
                    return self.page('Study planner', '<p class="lead">Preview your study note. Notes stay in your browser URL fragment.</p><div class="card"><label>Study note<input id="note-input" placeholder="Review chapter 3"></label><button id="preview-note">Preview note</button><h2>Your preview</h2><div id="note-preview"></div></div>')
                if route == '/enrollment':
                    ref = value('reference')
                    found = None
                    if ref:
                        if self.mode == 'vulnerable':
                            found = db.execute(f"SELECT id FROM enrollments WHERE reference='{ref}'").fetchone()
                        else:
                            found = db.execute('SELECT id FROM enrollments WHERE reference=?', (ref,)).fetchone()
                    result = '<div class="notice" id="lookup-result">Enrollment found</div>' if found else '<div class="notice error" id="lookup-result">No matching enrollment</div>'
                    return self.page('Enrollment lookup', '<p class="lead">Check the status of your course enrollment reference.</p><form class="card"><label>Reference<input name="reference" placeholder="ENR-2026-001"></label><button>Check enrollment</button></form>' + (result if ref else ''))
                if route == '/courses':
                    q = value('q')
                    if self.mode == 'vulnerable':
                        rows = db.execute(f"SELECT code,title,credits FROM courses WHERE title LIKE '%{q}%'").fetchall()
                        label = q
                    else:
                        rows = db.execute('SELECT code,title,credits FROM courses WHERE title LIKE ?', ('%' + q + '%',)).fetchall()
                        label = html.escape(q)
                    cards = ''.join(f'<article class="card"><div class="tag">{html.escape(str(r[0]))}</div><h2>{html.escape(str(r[1]))}</h2><p>{html.escape(str(r[2]))} credits</p></article>' for r in rows)
                    return self.page('Course catalogue', f'<p class="lead">Find your next learning opportunity.</p><form class="search"><input name="q" placeholder="Search courses" value="{html.escape(q, quote=True)}"><button>Search</button></form><p id="search-summary">Search results for: {label}</p><div class="grid">{cards or "<p>No courses found.</p>"}</div>')
                if route == '/':
                    return self.page('Welcome to CampusHub', '<p class="lead">A focused space to learn, connect and plan your semester.</p><div class="stats"><div class="card"><strong>4</strong><p>Available courses</p></div><div class="card"><strong>12</strong><p>Weekly study hours</p></div><div class="card"><strong>2026</strong><p>Fall semester</p></div></div><div class="hero"><div class="tag">THIS SEMESTER</div><h2>Build skills that matter.</h2><p>Explore security, databases and modern software engineering.</p><a class="button" href="/' + self.mode + '/courses">Browse courses →</a></div><div class="grid"><article class="card"><h2>Stay connected</h2><p>Ask questions and share ideas with your classmates.</p><a href="/' + self.mode + '/discussion">Open discussion →</a></article><article class="card"><h2>Plan your week</h2><p>Keep your learning goals within reach.</p><a href="/' + self.mode + '/planner">Open planner →</a></article></div>')
                return self.page('Not found', '<p>This page does not exist.</p>', 404)
            except sqlite3.Error as exc:
                return self.page('Database request failed', '<div class="notice error">' + (html.escape(str(exc)) if self.mode == 'vulnerable' else 'Unable to process request.') + '</div>', 400)

    def login_form(self):
        return '<form method="post" class="card narrow"><label>Username<input name="username" required></label><label>Password<input type="password" name="password" required></label><button>Sign in</button><p class="muted">Demo student: student / StudentPass!26</p></form>'


class Attacker(BaseHTTPRequestHandler):
    def do_GET(self):
        mode = 'safe' if 'safe' in self.path else 'vulnerable'
        # localhost:8001 is external to localhost:8000 (different origin).
        # Using the same site makes the demo independent of cookie grace periods.
        target = f'http://localhost:8000/{mode}/profile'
        auto_submit = '' if 'manual=1' in self.path else "<script>document.getElementById('attack').submit()</script>"
        body = f'''<!doctype html><html><head><title>External scholarship page</title></head><body><h1>Scholarship invitation</h1><p>This external page submits a forged email update to {html.escape(target)}.</p><form id="attack" method="post" action="{target}"><input type="hidden" name="email" value="attacker@lab.invalid"><button>Continue</button></form>{auto_submit}</body></html>'''.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true', help='Reset only the two generated lab databases')
    parser.add_argument('--attacker', action='store_true', help='Serve the external CSRF page on port 8001')
    args = parser.parse_args()
    if args.attacker:
        print('External CSRF page: http://localhost:8001/vulnerable (or /safe)', flush=True)
        ThreadingHTTPServer(('127.0.0.1', 8001), Attacker).serve_forever()
    else:
        initialize(args.reset)
        print('CampusHub: http://localhost:8000/safe and /vulnerable', flush=True)
        ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
