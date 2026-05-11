# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Spendly is a lightweight personal expense tracker built with Flask and SQLite.

## Architecture

```text
spendly/
├── app.py                 # All routes — single file, no blueprints
├── database/
│   └── db.py              # SQLite helpers: get_db(), init_db(), seed_db()
├── templates/
│   ├── base.html          # Shared layout — all templates must extend this
│   └── *.html             # One template per page
├── static/
│   ├── css/
│   │   ├── style.css      # Global styles
│   │   └── landing.css    # Landing-page-only styles
│   └── js/
│       └── main.js        # Vanilla JS only
└── requirements.txt
```

This is a Flask + SQLite expense tracking app built as a step-by-step student project. Features are added incrementally — many routes in `app.py` are stubs returning placeholder strings, and `database/db.py` is not yet implemented.

**Entry point:** `app.py` — all routes live here. No blueprints.

**Database layer:** `database/db.py` (stub). When implemented it will expose three functions:
- `get_db()` — SQLite connection with `row_factory` and foreign keys enabled
- `init_db()` — creates tables using `CREATE TABLE IF NOT EXISTS`
- `seed_db()` — inserts sample data for development

**Templates:** Jinja2. All pages extend `templates/base.html`, which provides the navbar, footer (with Terms/Privacy links), and shared script/style blocks. Auth pages (`login.html`, `register.html`) use the `.auth-section` / `.auth-card` layout pattern.

**CSS split:**
- `static/css/style.css` — global styles, design tokens (CSS variables), navbar, footer, auth pages, buttons
- `static/css/landing.css` — landing page only; linked via `{% block head %}` in `landing.html`. Contains all hero styles and the video modal.

**Design tokens** are defined as CSS variables in `style.css` under `:root` — use these (`--ink`, `--accent`, `--paper`, `--border`, etc.) rather than raw colour values when adding new styles.

**Video modal** on the landing page (`landing.html`) is driven by vanilla JS in `{% block scripts %}`. It stops the YouTube video on close by resetting `iframe.src = ''`.

## Where things belong

- New routes → `app.py` only, no blueprints
- DB logic → `database/db.py` only, never inline in routes
- New pages → new `.html` file extending `base.html`
- Page-specific styles → new `.css` file, not inline `<style>` tags

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run dev server (port 5001)
python app.py

# Run all tests
pytest

# Run a specific test file
pytest tests/test_foo.py

# Run a specific test by name
pytest -k "test_name"

# Run tests with output visible
pytest -s
```

## Code style

- Python: PEP 8, snake_case for all variables and functions
- Templates: Jinja2 with `url_for()` for every internal link — never hardcode URLs
- Route functions: one responsibility only — fetch data, render template, done
- DB queries: always use parameterized queries (`?` placeholders) — never f-strings in SQL
- Error handling: use `abort()` for HTTP errors, not bare `return "error string"`

## Tech constraints

- Flask only — no FastAPI, no Django, no other web frameworks
- SQLite only — no PostgreSQL, no SQLAlchemy ORM, no external DB
- Vanilla JS only — no React, no jQuery, no npm packages
- No new pip packages — work within `requirements.txt` unless explicitly told otherwise
- Python 3.10+ assumed — f-strings and `match` statements are fine

## Warnings and things to avoid

- Never use raw string returns for stub routes once a step is implemented — always render a template
- Never hardcode URLs in templates — always use `url_for()`
- Never put DB logic in route functions — it belongs in `database/db.py`
- Never install new packages mid-feature without flagging it — keep `requirements.txt` in sync
- Never use JS frameworks — the frontend is intentionally vanilla
- `database/db.py` is currently empty — do not assume helpers exist until the step that implements them
- FK enforcement is manual — SQLite foreign keys are OFF by default; `get_db()` must run `PRAGMA foreign_keys = ON` on every connection
- The app runs on port `5001`, not Flask's default `5000` — do not change this

## Implemented vs stub routes

| Route                       | Status                                |
| --------------------------- | ------------------------------------- |
| `GET /`                     | Implemented — renders `landing.html`  |
| `GET /register`             | Implemented — renders `register.html` |
| `GET /login`                | Implemented — renders `login.html`    |
| `GET /logout`               | Stub — Step 3                         |
| `GET /profile`              | Stub — Step 4                         |
| `GET /expenses/add`         | Stub — Step 7                         |
| `GET /expenses/<id>/edit`   | Stub — Step 8                         |
| `GET /expenses/<id>/delete` | Stub — Step 9                         |

**Do not implement a stub route unless the active task explicitly targets that step.**
