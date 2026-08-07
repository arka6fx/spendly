# Spendly

Spendly is a lightweight personal expense tracker, deployed as a Cloudflare
Python Worker (FastAPI + Jinja2) backed by a D1 database.

## Architecture

```text
spendly/
├── src/
│   ├── worker.py      # Entry point — bridges the FastAPI app into a Worker
│   ├── app.py         # All routes (FastAPI)
│   ├── database.py    # D1 query helpers (SQLite-compatible SQL)
│   ├── auth.py        # pbkdf2 password hashing + signed session cookies
│   └── templates/     # Jinja2 templates (adapted from the Flask project)
├── assets/
│   └── static/        # Static files served by Cloudflare's assets feature
├── migrations/        # D1 migrations (schema + demo data)
├── pyproject.toml     # Python packages (fastapi, jinja2) + pywrangler tooling
└── wrangler.jsonc     # Worker configuration (name, D1 binding, assets)
```

## Commands

```bash
# Local dev (starts workerd at http://localhost:8787)
uv run pywrangler dev

# Deploy to Cloudflare
uv run pywrangler deploy

# Apply database migrations to the remote D1 database
npx wrangler d1 migrations apply spendly --remote
```

## Notes

- Storage uses **D1**, Cloudflare's serverless SQLite. The schema is a
  1:1 port of the Flask app's `users`/`expenses` tables.
- Sessions are stateless signed cookies (`spendly_session`) — no server-side
  session store. `SESSION_SECRET` is stored as a Worker secret
  (`npx wrangler secret put SESSION_SECRET`); local dev reads it from
  `.dev.vars`.
- Passwords are hashed with `pbkdf2_sha256` (Werkzeug's format is not
  available on the Workers runtime).
- The demo account is seeded by the migration: `demo@spendly.com` / `demo123`.
