# Spec: Login and Logout

## Overview

Implement the `POST /login` route and the `GET /logout` route so users can authenticate
and end their session. Login validates email and password against the database, sets a
Flask session on success, and re-renders the form with an error on failure. Logout clears
the session and redirects to the landing page. This step also adds a Flask `SECRET_KEY`
(required for signed cookies) and updates `base.html` to show context-appropriate nav
links (Sign in / Get started for guests; a logout link for authenticated users).

## Depends on

- Step 1 — Database setup (`get_db()`, `users` table must exist)
- Step 2 — Registration (users must exist in the DB to log in)

## Routes

- `POST /login` — validates credentials, sets `session['user_id']`, redirects to `/profile` on success — public
- `GET /logout` — clears the session, redirects to `/` — public (no login guard needed)

## Database changes

No new tables or columns. The existing `users` table (`id`, `email`, `password_hash`) is sufficient.

A new helper is needed in `database/db.py`:
- `get_user_by_email(email)` — returns a single `sqlite3.Row` or `None`

## Templates

- **Modify:** `templates/login.html` — change `action="/login"` to `action="{{ url_for('login') }}"`
- **Modify:** `templates/base.html` — update nav to branch on `session.get('user_id')`:
  - Guest: show "Sign in" and "Get started" links (current behaviour)
  - Logged-in: show "Sign out" link pointing to `url_for('logout')`

## Files to change

- `app.py` — add `POST` to `/login` route; implement `/logout`; import `session` and
  `check_password_hash`; set `app.secret_key`
- `database/db.py` — add `get_user_by_email(email)` helper
- `templates/login.html` — fix hardcoded `action` URL
- `templates/base.html` — conditional nav links based on session

## Files to create

None.

## New dependencies

No new dependencies. `flask.session` and `werkzeug.security.check_password_hash` are
already available.

## Rules for implementation

- No SQLAlchemy or ORMs — use `get_db()` with raw SQL
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- Passwords checked with `werkzeug.security.check_password_hash` — never compare plain text
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic stays in `database/db.py` — routes only call helpers, never write SQL inline
- `app.secret_key` must be set before any `session` usage; use a hard-coded dev string
  (e.g. `"dev-secret-change-in-prod"`) — document that it must be replaced in production
- Store only `user_id` (integer) in the session — never store the password or full user row
- On bad credentials show a single vague error ("Invalid email or password") — do not
  distinguish between "email not found" and "wrong password" (security best practice)
- `GET /logout` clears the session with `session.clear()` and redirects to `url_for('landing')`
- `/profile` is still a stub (Step 4); after login, redirect there anyway — the stub
  response is acceptable for now

## Definition of done

- [ ] Submitting valid credentials sets a session and redirects to `/profile`
- [ ] Submitting an unknown email shows "Invalid email or password" on the login form
- [ ] Submitting a correct email with a wrong password shows "Invalid email or password"
- [ ] Submitting with blank fields shows a validation error on the form
- [ ] Visiting `/logout` clears the session and redirects to the landing page
- [ ] After logout, visiting `/logout` again redirects cleanly (no error)
- [ ] Logged-in navbar shows "Sign out" instead of "Sign in" / "Get started"
- [ ] Guest navbar still shows "Sign in" and "Get started"
- [ ] The login form `action` uses `url_for('login')` — no hardcoded URLs
- [ ] App starts without errors and all existing routes continue to work
