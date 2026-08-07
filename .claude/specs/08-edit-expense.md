# Spec: Edit Expense

## Overview

This step implements the edit expense feature. Logged-in users can update any of their own
expenses via a pre-populated form. The route fetches the existing row, renders a form with
current values, validates the submitted data, updates the database, and redirects back to
the profile page. Ownership is enforced — a user cannot edit another user's expense.

## Depends on

- Step 1: Database setup (`expenses` table must exist with `user_id`, `amount`, `category`,
  `date`, and `description` columns)
- Step 3: Login + Logout (session must carry `user_id`)
- Step 4: Profile page (`profile.html` must exist so the redirect target renders correctly)
- Step 5: Backend connection (query helpers and `get_db()` must be in place)
- Step 7: Add Expense (the `add_expense.html` template establishes the form UI pattern this
  step mirrors; the categories list must already be defined)

## Routes

- `GET /expenses/<int:id>/edit` — render a pre-populated edit form for the expense — logged-in only
- `POST /expenses/<int:id>/edit` — validate and save changes, then redirect to `/profile` — logged-in only

## Database changes

No new tables or columns. Two new helper functions are needed in `database/queries.py`:

| Helper | Signature | Description |
| --- | --- | --- |
| `get_expense_by_id` | `(expense_id)` | Returns a single expense row as a dict, or `None` if not found |
| `update_expense` | `(expense_id, amount, category, date, description)` | Updates all editable fields for the given expense id |

`update_expense` SQL:
```sql
UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ?
```

Both helpers follow the same open/close pattern as existing helpers in `queries.py`:
open a connection, execute, commit if writing, close in `finally`.

## Templates

- **Create:** `templates/edit_expense.html`
  - Extends `base.html`
  - Shows a heading "Edit Expense"
  - A `<form method="POST" action="{{ url_for('edit_expense', id=expense.id) }}">`
  - Four fields (pre-populated with current values):
    - `<input type="number" name="amount" step="0.01" min="0.01" required>` — current `expense.amount`
    - `<select name="category" required>` — same fixed category list as the add form:
      Food, Transport, Bills, Health, Entertainment, Shopping, Other — current `expense.category` selected
    - `<input type="date" name="date" required>` — current `expense.date`
    - `<input type="text" name="description">` — current `expense.description` (optional)
  - A submit button labelled "Save Changes"
  - A plain `<a>` link labelled "Cancel" pointing to `{{ url_for('profile') }}`
  - Inline error display: `{% if error %}<p class="error">{{ error }}</p>{% endif %}`
  - Use existing CSS classes and design tokens (`--ink`, `--accent`, `--paper`, `--border`) —
    no new styles needed if the add form's classes already exist

## Files to change

- `app.py` — implement the `edit_expense` route (replaces the stub):
  - Both GET and POST: check `session.get("user_id")`, redirect to login if missing
  - Both GET and POST: call `get_expense_by_id(id)`, `abort(404)` if not found
  - Both GET and POST: compare `expense["user_id"]` with session `user_id`, `abort(403)` if mismatch
  - GET: render `edit_expense.html` with the expense data
  - POST: read and validate form fields; on error re-render form with error message; on success
    call `update_expense(...)` and redirect to `url_for("profile")`
- `database/queries.py` — add `get_expense_by_id` and `update_expense`

## Files to create

- `templates/edit_expense.html`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- DB logic stays in `database/queries.py` — the route only calls helpers, never writes SQL
- Passwords hashed with werkzeug (not applicable here, but the pattern remains)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Use `abort(404)` for a missing expense, `abort(403)` for an ownership violation — never return a raw string
- Redirect to `url_for("profile")` on successful save — do not render the form again

## Definition of done

- [ ] `GET /expenses/<id>/edit` redirects to `/login` when the user is not logged in
- [ ] `GET /expenses/<id>/edit` returns 404 for an expense that does not exist
- [ ] `GET /expenses/<id>/edit` returns 403 when the logged-in user does not own the expense
- [ ] `GET /expenses/<id>/edit` renders the edit form with all fields pre-populated with the
      existing expense values
- [ ] The category `<select>` has the correct category pre-selected
- [ ] `POST /expenses/<id>/edit` with a missing amount shows a validation error and re-renders the form
- [ ] `POST /expenses/<id>/edit` with a non-positive amount shows a validation error and re-renders the form
- [ ] `POST /expenses/<id>/edit` with a missing date shows a validation error and re-renders the form
- [ ] `POST /expenses/<id>/edit` with an invalid category shows a validation error and re-renders the form
- [ ] A valid POST updates the expense in the database and redirects to `/profile`
- [ ] The updated values are visible on the profile page after the redirect
- [ ] An ownership check applies on POST as well — a crafted POST to another user's expense id returns 403
- [ ] App starts without errors and all existing routes continue to work

---

**Repository:** [https://github.com/arka6fx/spendly](https://github.com/arka6fx/spendly)
