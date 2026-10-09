"""Build an editable Word RTF report with embedded, unmodified browser screenshots."""
import html
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'submission'
(ROOT / 'tmp').mkdir(exist_ok=True)
evidence = json.loads((OUT / 'verification.json').read_text())
assert evidence['status'] == 'passed'


def escape(text):
    result = ''
    for char in str(text):
        code = ord(char)
        if char in '\\{}':
            result += '\\' + char
        elif char == '\n':
            result += '\\line '
        elif code > 127:
            result += '\\u' + str(code if code < 32768 else code - 65536) + '?'
        else:
            result += char
    return result


pages = []


def page(title, paragraphs, screenshot=None):
    pages.append((title, paragraphs, screenshot))


page('CampusHub Web Security Project', [
    'Information Security Practical Assignment 2 | Part 2',
    'Muhammad Ibrahim | 23F-0590',
    'Muhammad Siddique | 23F-0669',
    '9 October 2026',
    'CampusHub demonstrates seven web-security requirements in a real database-backed education portal. Its vulnerable and safe versions share the same workflows but use independent SQLite databases. All documented attacks were submitted through the running application and checked in Chromium.',
    'The vulnerable version permits reflected, stored and DOM XSS, an authenticated cross-site email update, SQL login bypass, boolean inference and a complete SQL metadata-to-credentials extraction chain. The safe version blocks the same attacks while normal login, search, discussion and email updates continue to work.',
    'Evidence summary: ' + str(evidence['checks']) + ' browser captures and six live HTTP regression test methods passed. Each evidence page records the exact input and observed result, followed by the original browser screenshot. The app footer shows the capture date and time in Pakistan Standard Time.',
    'GitHub submission URL: https://github.com/ibrahimwarraich101/is-webSecurity. Local Git development commits accompany the project. This report covers Part 2 only; Parts 1 and 3 can be added to the final combined Word submission.'
])
page('Architecture and Reproduction', [
    'Frontend: semantic HTML, responsive CSS and browser JavaScript. Backend: Python standard-library HTTP server. Database: SQLite, accessed through real SQL queries. No application dependencies need to be installed.',
    'Start: python app.py. On the configured Windows computer, run ./run.ps1 or invoke the installed Python interpreter shown in README.md. Open http://localhost:8000/vulnerable and http://localhost:8000/safe. The header links switch versions; session cookies and databases are separate.',
    'Start the attacker in another terminal: python app.py --attacker. It listens at http://127.0.0.1:8001. Main and attacker servers bind only to loopback. All accounts and extracted credentials are synthetic lab records.',
    'Demo accounts: student / StudentPass!26 and admin / AdminPass!26. The safe database hashes seeded passwords with independent random salts and PBKDF2-HMAC-SHA256. Vulnerable plaintext passwords make the extraction impact visible.',
    'Tables: users(id, username, password, email, role); courses(code, title, credits); comments(id, author, body); enrollments(id, reference, user_id, course_code). The populated seed-data.sql creates both databases; safe initialization hashes its passwords before serving requests.',
    'Re-run live HTTP tests: python tests/test_security.py. Browser evidence: install the development-only Playwright package, then node tests/browser_evidence.cjs. tests/build_report.py builds the report from the original PNG images. tests/export_word.ps1 converts its temporary RTF to native DOCX through Microsoft Word. The submitted DOCX is editable and can be merged into the final combined report.',
    'Reset: stop the main server, then python app.py --reset. Only generated lab databases are replaced. Source files and screenshots are preserved. Restarting clears in-memory sessions.'
])
page('Vulnerability Analysis and Defenses', [
    'Reflected XSS: the vulnerable course-search summary interpolates request text directly into HTML. The browser interprets the injected SVG onload handler. Safe mode uses HTML output encoding; Content Security Policy is an additional layer.',
    'Stored XSS: discussion input is stored in SQLite with a parameterized INSERT, but the vulnerable output emits its body as raw HTML. A separate guest visitor loads that saved input and executes it. Safe mode encodes the body at output, preserving the original text without executing it.',
    'DOM XSS: the planner reads location.hash and assigns decoded input to innerHTML. The fragment never appears in an HTTP request, but its image error handler executes in the browser. Safe mode assigns the value to textContent.',
    'CSRF: the vulnerable email update trusts the session cookie without verifying a token or Origin. The external page submits an automatic POST without consent. Safe mode uses a random session-bound token, constant-time comparison, exact Origin validation and explicit SameSite=Lax cookies. The two screenshots after each attack verify the database-backed profile state.',
    'Easy SQL injection: raw username and password are concatenated into the vulnerable login query. A quote closes the username literal; a SQL comment removes the password condition. Safe mode binds the username parameter and separately verifies the password hash.',
    'Intermediate SQL injection: the enrollment lookup exposes only found or not found. Appending true and false predicates confirms injection; testing the first character of the admin password reveals A without printing the password. Safe mode binds the reference as data.',
    'Advanced SQL injection: ORDER BY 3 succeeds and ORDER BY 4 fails, establishing three result columns. UNION queries enumerate the database, tables and users columns before extracting demo credentials. SQLite schema introspection through pragma_database_list, sqlite_master and pragma_table_info is the equivalent of information_schema. Safe mode parameterizes the LIKE value.'
])
page('CSRF Conditions and Viva Guide', [
    'The cross-site attacker is http://127.0.0.1:8001 and the target is http://localhost:8000. These are different origins and different sites. A newly issued vulnerable cookie omits SameSite. Chromium allows its top-level cross-site POST during the short default-cookie grace period. Therefore run the vulnerable attack immediately after login. The browser evidence script does this automatically without adding cookies manually.',
    'Safe mode explicitly sets SameSite=Lax, so the cross-site POST does not carry the authenticated cookie. To exercise server-side protection too, an additional attacker request comes from http://localhost:8001: it is same-site but cross-origin, carries the session cookie, and receives HTTP 403 because its token and Origin are invalid. The profile remains unchanged.',
    'For the viva, first browse the dashboard and demonstrate normal login, course search, posting and email changes. For each XSS type, submit the payload through its actual UI, explain its source and sink, then repeat on safe mode. For stored XSS use a different unauthenticated browser context to establish persistence.',
    'For SQL injection, explain how quotes, comments and UNION alter the query structure. Demonstrate true/false inference, then follow the advanced chain in order. The final cards contain actual synthetic records queried from SQLite, rather than a scripted success message.',
    'For CSRF, sign in immediately before visiting the external page. Show the before and after profile emails in both versions, and explain why a cookie alone cannot establish user intent. Different ports alone change origins, not sites.',
    'The safe version addresses the assignment attack set. Production use would additionally require HTTPS and Secure cookies, session expiry, rate limiting, access-control policy and operational monitoring.',
    'References: OWASP Cross Site Scripting Prevention Cheat Sheet; OWASP Cross Site Request Forgery Prevention Cheat Sheet; OWASP SQL Injection Prevention Cheat Sheet. Direct links are included in README.md.'
])
for item in evidence['evidence']:
    title = item['mode'].title() + ' ' + item['name'].replace('-', ' ').title()
    paragraphs = []
    if item['payload']:
        paragraphs.append('Input or attack setup: ' + item['payload'])
    paragraphs.append('Observed result: ' + item['observation'])
    paragraphs.append('Capture timestamp UTC: ' + item['capturedAt'] + '. The screenshot footer displays PKT.')
    paragraphs.append('Target URL: ' + item['url'])
    page(title, paragraphs, OUT / item['screenshot'])

rtf = [r'{\rtf1\ansi\deff0{\fonttbl{\f0 Calibri;}{\f1 Consolas;}}\paperw11906\paperh16838\margl1000\margr1000\margt800\margb800\fs22']
preview = ['<!doctype html><meta charset="utf-8"><title>Part 2 report layout check</title><style>body{background:#ddd;margin:0;font:14px/1.45 Arial;color:#222}.page{box-sizing:border-box;width:794px;height:1123px;background:white;padding:48px 55px;margin:20px auto;overflow:hidden}h1{font-size:24px;color:black;margin:0 0 22px}p{overflow-wrap:anywhere;margin:0 0 16px}img{display:block;max-width:100%;max-height:560px;margin:16px auto;object-fit:contain}.number{margin-top:16px;color:#666;font-size:11px}</style>']
for index, (title, paragraphs, screenshot) in enumerate(pages):
    if index:
        rtf.append(r'\page ')
    rtf.append(r'\pard\keepn\sb0\sa240\b\fs32 ' + escape(title) + r'\b0\fs22\par ')
    preview.append('<article class="page"><h1>' + html.escape(title) + '</h1>')
    for paragraph in paragraphs:
        # Long URLs duplicate the exact payload; keep them in JSON rather than overflow the document.
        if paragraph.startswith('Target URL:') and len(paragraph) > 150:
            paragraph = 'Target endpoint: ' + paragraph.split('?', 1)[0].split('#', 1)[0].replace('Target URL: ', '') + '. Exact encoded URL is in verification.json.'
        rtf.append(r'\pard\sa180\sl280\slmult1 ' + escape(paragraph) + r'\par ')
        preview.append('<p>' + html.escape(paragraph) + '</p>')
    if screenshot:
        raw = screenshot.read_bytes()
        width, height = struct.unpack('>II', raw[16:24])
        factor = min(9906 / width, 7900 / height)
        rtf.append(r'\pard\qc {\pict\pngblip\picw' + str(width) + r'\pich' + str(height) + r'\picwgoal' + str(int(width*factor)) + r'\pichgoal' + str(int(height*factor)) + '\n' + raw.hex() + r'}\par ')
        preview.append('<img src="' + screenshot.as_uri() + '" alt="' + html.escape(title) + '">')
    rtf.append(r'\pard\qr\fs18 Page ' + str(index+1) + ' of ' + str(len(pages)) + r'\fs22\par ')
    preview.append('<div class="number">Page ' + str(index+1) + ' of ' + str(len(pages)) + '</div></article>')
rtf.append('}')
(ROOT / 'tmp' / 'Part_2_Report.rtf').write_text(''.join(rtf), encoding='ascii')
(ROOT / 'tmp' / 'report-preview.html').write_text(''.join(preview), encoding='utf-8')
print('Built editable Word RTF:', len(pages), 'pages with', evidence['checks'], 'embedded screenshots.')
