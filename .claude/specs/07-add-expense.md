# Spec: Add Expense

## Overview

This step implements the expense submission form, allowing logged-in users to record a new
expense with an amount, category, date, and optional description. The stub route at
`GET /expenses/add` is replaced with a full GET + POST handler. On GET it renders an empty
form; on POST it validates the input, writes the record via a new DB helper, and redirects
the user back to their profile. This is the first route that writes user data to the
`expenses` table.

## Depends on

- Step 1: Database setup (`expenses` table must exist with `user_id`, `amount`, `category`,
  `date`, and `description` columns)
- Step 3: Login + Logout (session must carry `user_id` so the expense is attributed to the
  correct user)
- Step 4: Profile page (`/profile` must exist as the post-submission redirect target)

## Routes

- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the new expense, then redirect to `/profile` —
  logged-in only

## Database changes

No new tables or columns. One new helper function in `database/db.py`:

- `add_expense(user_id, amount, category, date, description)` — inserts a single row into
  the `expenses` table using a parameterised `INSERT` statement and commits.

## Templates

- **Create:** `templates/add_expense.html`
  - Extends `base.html`
  - Contains a form with `method="POST"` and `action="{{ url_for('add_expense') }}"`
  - Fields:
    - `amount` — `<input type="number" step="0.01" min="0.01" name="amount">` (required)
    - `category` — `<select name="category">` with options: Food, Transport, Bills, Health,
      Entertainment, Shopping, Other (required)
    - `date` — `<input type="date" name="date">` (required)
    - `description` — `<input type="text" name="description">` (optional, max 200 chars)
  - A submit button labelled "Add Expense"
  - If the route passes an `error` variable, display it above the form
  - Re-populate all fields on validation error using the submitted values passed back from
    the route

## Files to change

- `app.py` — replace the stub `add_expense` route with a GET + POST implementation:
  - Redirect to login if `session.get("user_id")` is falsy
  - `GET`: render `add_expense.html` with empty field values
  - `POST`:
    - Read and strip `amount`, `category`, `date`, `description` from `request.form`
    - Validate: `amount` must be a positive number; `category` must be one of the seven
      allowed values; `date` must be non-empty
    - On validation failure: re-render `add_expense.html` with the error message and the
      submitted values so the user does not have to retype everything
    - On success: call `add_expense(...)` from `database/db.py`, then
      `redirect(url_for("profile"))`
  - Change the route decorator to `methods=["GET", "POST"]`
- `database/db.py` — add `add_expense(user_id, amount, category, date, description)`

## Files to create

- `templates/add_expense.html`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- DB logic stays in `database/db.py` — the route never writes SQL directly
- Passwords hashed with werkzeug (not applicable here, but keep the pattern in mind)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline `<style>` tags
- Category must be validated server-side against the fixed allowed list — do not trust the
  client's `<select>` value alone
- `amount` must be cast to `float` with error handling — never pass a raw string to the DB

## Definition of done

- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in renders a form with amount, category, date,
  and description fields
- [ ] Submitting the form with valid data inserts a row in the `expenses` table and redirects
  to `/profile`
- [ ] The new expense appears in the transaction list on the profile page immediately after
  redirect
- [ ] Submitting with a missing or non-positive amount re-renders the form with an error
  message
- [ ] Submitting with a missing date re-renders the form with an error message
- [ ] Submitting with an invalid category (e.g. a tampered POST body) re-renders the form
  with an error message
- [ ] On validation error, all previously entered field values are repopulated in the form
- [ ] The profile page summary stats (total spent, count) reflect the newly added expense
- [ ] App starts without errors and all existing routes continue to work
