-- Migration 0001: initial schema + demo data

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    description TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
);

-- Demo user (password: demo123)
INSERT INTO users (name, email, password_hash)
VALUES ('Demo User', 'demo@spendly.com', 'pbkdf2_sha256$260000$743a18df085e0c527033fc3780f7df94$54abfa5d1a720e3208219487a901aaf52fa68350de98e50a9c86213e7531a700');

INSERT INTO expenses (user_id, amount, category, date, description) VALUES
    (1, 12.50,  'Food',          '2026-05-01', 'Lunch at cafe'),
    (1, 45.00,  'Transport',     '2026-05-03', 'Monthly bus pass'),
    (1, 120.00, 'Bills',         '2026-05-05', 'Internet bill'),
    (1, 30.00,  'Health',        '2026-05-07', 'Pharmacy'),
    (1, 25.00,  'Entertainment', '2026-05-10', 'Movie tickets'),
    (1, 60.00,  'Shopping',      '2026-05-12', 'New shoes'),
    (1, 15.00,  'Other',         '2026-05-14', 'Miscellaneous'),
    (1, 8.75,   'Food',          '2026-05-16', 'Coffee and snacks');
