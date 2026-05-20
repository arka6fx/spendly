# Spec: Delete Expense

## Overview

Lets a logged-in user permanently remove one of their own expenses. The route enforces ownership (403 if the expense belongs to someone else, 404 if it doesn't exist) and uses a POST-only action to prevent accidental deletion via GET requests. After deletion the user is redirected back to their profile. A lightweight confirmation step is surfaced directly in the existing `profile.html` transaction list via a JavaScript `confirm()` dialog, keeping the feature small with no new template required.

## Depends on

- Step 01 — Database setup (expenses table exists)
- Step 04 — Profile page (transaction list renders expense rows with IDs)
- Step 07 — Add Expense (expenses can be created)
- Step 08 — Edit Expense (`get_expense_by_id` already in `database/queries.py`)

## Routes

- `POST /expenses/<int:id>/delete` — deletes the expense owned by the current user — logged-in only

The existing `GET /expenses/<int:id>/delete` stub must be **converted** to POST-only. Accept the form submission and redirect; do not render a dedicated confirmation page.

## Database changes

No new tables or columns. A new helper function `delete_expense(expense_id)` is added to `database/db.py`.

## Templates

- **Modify:** `templates/profile.html` — add a small `<form method="POST">` delete button per transaction row in the expense list; include a `confirm()` call via `onsubmit` to prevent accidental clicks.

No new templates.

## Files to change

- `app.py` — replace the stub `delete_expense` route with a working `POST`-only implementation
- `database/db.py` — add `delete_expense(expense_id)` helper
- `templates/profile.html` — add delete form/button to each transaction row

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders) — never f-strings in SQL
- Route must be `methods=["POST"]` only — GET must not delete data
- Ownership check: load the expense with `get_expense_by_id`, `abort(403)` if `expense["user_id"] != session["user_id"]`, `abort(404)` if expense is `None`
- Redirect to `url_for("profile")` on success — never hardcode URLs
- Delete helper belongs in `database/db.py`, not inline in the route
- Export `delete_expense` from `database/db.py` and import it in `app.py`
- Use CSS variables — never hardcode hex values in new styles
- All templates extend `base.html`
- The confirmation dialog must use vanilla JS only — no libraries

## Definition of done

- [ ] Visiting `/expenses/<id>/delete` via GET returns 405 Method Not Allowed
- [ ] POSTing to `/expenses/<id>/delete` for an expense the logged-in user owns deletes it and redirects to `/profile`
- [ ] The deleted expense no longer appears in the profile transaction list after deletion
- [ ] POSTing to `/expenses/<id>/delete` for an expense belonging to a different user returns 403
- [ ] POSTing to `/expenses/<id>/delete` for a non-existent expense ID returns 404
- [ ] POSTing while not logged in redirects to `/login`
- [ ] A delete button appears on each expense row in `profile.html` with a JS confirmation dialog
- [ ] Clicking "Cancel" in the confirmation dialog does not submit the form
