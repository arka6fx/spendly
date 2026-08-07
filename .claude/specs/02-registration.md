# Spec: Registration

## Overview

Implement the `POST /register` route so that new users can create a Spendly account.
The `GET /register` route and `register.html` template already exist; this step wires up
the form submission handler — validating input, hashing the password, inserting the user
row, and redirecting to the login page on success. Errors (missing fields, duplicate
email, short password) are re-rendered inline using the template's existing `{% if error %}`
block. No session is created here; that belongs to Step 3.

## Depends on

- Step 1 — Database setup (`get_db()`, `init_db()`, `users` table must exist)

## Routes

- `POST /register` — validates form data, creates user, redirects to `/login` — public

## Database changes

No new tables or columns. The `users` table from Step 1 is sufficient:
`id`, `name`, `email` (UNIQUE), `password_hash`, `created_at`.

## Templates

- **Modify:** `templates/register.html` — form `action` must use `url_for('register')`
  instead of the hardcoded `/register` string. No other template changes needed.

## Files to change

- `app.py` — add `POST` method to the `/register` route; import `request`, `redirect`,
  `url_for` from Flask; import `generate_password_hash` from `werkzeug.security`
- `templates/register.html` — replace `action="/register"` with `action="{{ url_for('register') }}"`

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use `get_db()` from `database/db.py` with raw SQL
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` — never stored plain
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic stays in `database/db.py` — route only calls helpers, never writes SQL inline
- Catch `sqlite3.IntegrityError` for duplicate email; re-render with a user-friendly error
- Always close the DB connection (use try/finally or a context manager pattern)
- Validation order: name present → email present → password ≥ 8 chars → DB insert
- On success, redirect to `url_for('login')` — do not log the user in (session is Step 3)
- Use `abort(400)` only for truly malformed requests; prefer re-rendering with `error=` for
  form validation failures so the user sees a helpful message

## Definition of done

- [ ] Submitting the form with all valid fields creates a new row in `users` with a hashed password
- [ ] Submitting with a blank name shows "Name is required" (or equivalent) on the form
- [ ] Submitting with a blank email shows an error on the form
- [ ] Submitting with a password shorter than 8 characters shows an error on the form
- [ ] Submitting with an email that already exists shows "Email already registered" (or equivalent)
- [ ] Successful registration redirects to `/login`
- [ ] The password stored in the DB is a hash, not the plain-text value
- [ ] The form `action` uses `url_for('register')` — no hardcoded URLs
- [ ] App starts and all existing routes continue to work without errors

---

**Repository:** [https://github.com/arka6fx/spendly](https://github.com/arka6fx/spendly)
