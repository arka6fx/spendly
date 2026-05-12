# Spec: Date Filter for Profile Page

## Overview

This step adds date-range filtering to the profile page. The existing query helpers in
`database/queries.py` and the `/profile` route were built in Step 5 without filter support.
Now we extend them so users can pass optional `date_from` and `date_to` query-string
parameters to narrow the transaction list and recompute all stats (total spent, transaction
count, top category, category breakdown) for that window. The filter form lives on the page
itself and re-populates after submission so the selected range stays visible.

## Depends on

- Step 1: Database setup (`expenses` table must exist with a `date` column)
- Step 3: Login + Logout (session must carry `user_id`)
- Step 4: Profile page UI (`profile.html` template must exist)
- Step 5: Backend connection (`database/queries.py` helpers and `/profile` real-data wiring
  must already be in place)

## Routes

- `GET /profile` — same route, extended to accept optional `date_from` and `date_to`
  query-string params (ISO date strings, e.g. `?date_from=2026-05-01&date_to=2026-05-31`) —
  logged-in only

No new routes.

## Database changes

No new tables or columns. Three existing helpers in `database/queries.py` gain optional
filter parameters:

| Helper | Old signature | New signature |
| --- | --- | --- |
| `get_summary_stats` | `(user_id)` | `(user_id, date_from=None, date_to=None)` |
| `get_recent_transactions` | `(user_id, limit=10)` | `(user_id, date_from=None, date_to=None)` |
| `get_category_breakdown` | `(user_id)` | `(user_id, date_from=None, date_to=None)` |

`get_user_by_id` is not filtered — user info is always shown in full.

For each helper that gains filter params:
- Build the `WHERE user_id = ?` clause first, then append `AND date >= ?` and/or
  `AND date <= ?` only when the corresponding param is a non-empty string
- Accumulate bind values in a list alongside the clause fragments — never use f-strings or
  `%` formatting in SQL
- Treat `None` and `""` identically — neither triggers a date filter

## Templates

- **Modify:** `templates/profile.html`
  - Add a date filter form above the transaction table:
    - `<form method="GET" action="{{ url_for('profile') }}">`
    - Two `<input type="date">` fields: `name="date_from"` and `name="date_to"`
    - A submit button labelled "Filter"
    - A plain `<a>` link labelled "Clear" pointing to `{{ url_for('profile') }}` (no params)
    - Repopulate both inputs using `value="{{ date_from or '' }}"` and
      `value="{{ date_to or '' }}"` so the selected range stays visible after submission

## Files to change

- `database/queries.py` — add `date_from` and `date_to` params to `get_summary_stats`,
  `get_recent_transactions`, and `get_category_breakdown`
- `app.py` — in the `profile` view:
  - Read `date_from = request.args.get("date_from", "").strip()`
  - Read `date_to = request.args.get("date_to", "").strip()`
  - Pass both values to each of the three filtered helpers
  - Pass `date_from` and `date_to` through to `render_template` so the form can repopulate
- `templates/profile.html` — add the date filter form (see Templates section)

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- DB logic stays in `database/queries.py` — the route only calls helpers, never writes SQL
- Empty string and `None` are both treated as "no filter" — do not add a `WHERE` fragment
  for either
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles

## Definition of done

- [ ] Visiting `/profile` with no query params shows all expenses (unfiltered)
- [ ] Passing `?date_from=2026-05-05` hides all expenses before that date from the table
- [ ] Passing `?date_to=2026-05-07` hides all expenses after that date from the table
- [ ] Passing both params filters to only expenses within the range (inclusive)
- [ ] Summary stats (total spent, count, top category) update to reflect only the filtered window
- [ ] Category breakdown updates to reflect only the filtered window
- [ ] After filtering, both date inputs are repopulated with the submitted values
- [ ] Clicking "Clear" removes all query params and shows the full unfiltered profile
- [ ] A user with no expenses in the selected range sees zeroed stats and an empty table (no crash)
- [ ] `get_user_by_id` is unchanged — user info is always shown regardless of filter
- [ ] App starts without errors and all existing routes continue to work
