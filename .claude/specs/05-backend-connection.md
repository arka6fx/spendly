# Spec: Backend Connection

## Overview

This step replaces every hardcoded value in the `/profile` route with real data pulled from
the SQLite database. It also adds a date-range filter so users can narrow their transaction
history and recalculate stats for any period. The template contract (variable names, structure)
established in Step 4 stays the same — only the data source changes.

## Depends on

- Step 1: Database setup (`get_db()`, `users` and `expenses` tables must exist)
- Step 2: Registration (real users must be in the DB)
- Step 3: Login + Logout (session must carry `user_id`)
- Step 4: Profile page UI (template already built; this step wires it to the DB)

## Routes

- `GET /profile` — render the profile page with live DB data; accept optional `date_from` and
  `date_to` query-string params (ISO date strings, e.g. `?date_from=2026-05-01&date_to=2026-05-31`)
  to filter the transaction list and recalculate stats for that window

## Database changes

No new tables or columns. Four new helper functions are needed in `database/db.py`:

| Helper | Signature | Returns |
| --- | --- | --- |
| `get_user_by_id` | `(user_id)` | single `sqlite3.Row` or `None` |
| `get_expenses_by_user` | `(user_id, date_from=None, date_to=None)` | list of `sqlite3.Row` ordered by `date DESC` |
| `get_expense_summary` | `(user_id, date_from=None, date_to=None)` | dict with keys `total_spent`, `total_count`, `top_category` |
| `get_category_totals` | `(user_id, date_from=None, date_to=None)` | list of dicts `{"name": str, "total": float}` ordered by `total DESC` |

For all helpers that accept `date_from` / `date_to`:
- Both are optional; omit the `WHERE` clause fragment when `None`
- When one or both are provided, add `AND date >= ?` / `AND date <= ?` as appropriate
- Never use f-strings or `%` in SQL — build the clause with a params list

## Templates

- **Modify:** `templates/profile.html`
  - Add a date filter form above the transaction table:
    - `<form method="GET" action="{{ url_for('profile') }}">`
    - Two `<input type="date">` fields: `name="date_from"` and `name="date_to"`
    - A submit button labelled "Filter"
    - A "Clear" link pointing to `url_for('profile')` (no params)
    - Re-populate inputs with current filter values via `value="{{ date_from or '' }}"`
  - No other template changes needed — the variable names (`user`, `summary`, `transactions`,
    `categories`) are identical to Step 4

## Files to change

- `app.py` — replace hardcoded dicts in `/profile` with calls to the new DB helpers:
  - Read `date_from` and `date_to` from `request.args` (`.get("date_from")`, `.get("date_to")`)
  - Pass them to each helper
  - Pass them back to the template so the filter form can re-populate
  - Import the four new helpers from `database.db`

- `database/db.py` — add the four helpers listed above

- `templates/profile.html` — add the date filter form (see Templates section)

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- DB logic stays in `database/db.py` — the route only calls helpers, never writes SQL
- `get_expense_summary` must compute `top_category` with SQL (`GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1`), not Python
- Filter dates are optional strings — treat empty string the same as `None` (do not filter)
- Use CSS variables — never hardcode hex values
- No inline styles

## Definition of done

- [ ] `/profile` returns HTTP 200 with real data (not hardcoded dicts)
- [ ] The user info card shows the actual logged-in user's name, email, and `created_at` date
- [ ] Summary stats (total spent, transaction count, top category) reflect real expenses in the DB
- [ ] The transaction table shows all expenses for the logged-in user, newest first
- [ ] The category breakdown reflects real per-category totals for the logged-in user
- [ ] A date filter form is visible above the transaction table
- [ ] Submitting `date_from` and/or `date_to` filters the transaction list and recalculates all stats
- [ ] After filtering, the date inputs are re-populated with the submitted values
- [ ] The "Clear" link resets the filter and shows all expenses again
- [ ] A user with no expenses sees zeroed stats and an empty transaction table (no crash)
- [ ] All four DB helpers use parameterised queries — no inline SQL in `app.py`
- [ ] App starts without errors and all existing routes continue to work
