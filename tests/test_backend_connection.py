import pytest
from werkzeug.security import generate_password_hash
import database.db as db_module
from database.db import get_db
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _seed_user_id():
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()
        return row["id"]
    finally:
        conn.close()


def _new_user_id():
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("New User", "new@example.com", generate_password_hash("password1")),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# get_user_by_id                                                      #
# ------------------------------------------------------------------ #

def test_get_user_by_id_returns_correct_fields(app):
    uid = _seed_user_id()
    user = get_user_by_id(uid)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert "created_at" in user
    # formatted as "Month YYYY"
    parts = user["created_at"].split()
    assert len(parts) == 2
    assert parts[1].isdigit()


def test_get_user_by_id_nonexistent_returns_none(app):
    assert get_user_by_id(99999) is None


# ------------------------------------------------------------------ #
# get_summary_stats                                                   #
# ------------------------------------------------------------------ #

def test_get_summary_stats_seed_user(app):
    uid = _seed_user_id()
    stats = get_summary_stats(uid)
    assert stats["total_spent"] == pytest.approx(316.25)
    assert stats["total_count"] == 8
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(app):
    uid = _new_user_id()
    stats = get_summary_stats(uid)
    assert stats["total_spent"] == 0.0
    assert stats["total_count"] == 0
    assert stats["top_category"] is None


# ------------------------------------------------------------------ #
# get_recent_transactions                                             #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_seed_user(app):
    uid = _seed_user_id()
    txns = get_recent_transactions(uid)
    assert len(txns) == 8
    # ordered newest-first
    dates = [t["date"] for t in txns]
    assert dates == sorted(dates, reverse=True)
    # each row has required keys
    for t in txns:
        assert {"date", "description", "category", "amount"} <= t.keys()


def test_get_recent_transactions_no_expenses(app):
    uid = _new_user_id()
    assert get_recent_transactions(uid) == []


def test_get_recent_transactions_limit(app):
    uid = _seed_user_id()
    txns = get_recent_transactions(uid, limit=3)
    assert len(txns) == 3


# ------------------------------------------------------------------ #
# get_category_breakdown                                              #
# ------------------------------------------------------------------ #

def test_get_category_breakdown_seed_user(app):
    uid = _seed_user_id()
    cats = get_category_breakdown(uid)
    assert len(cats) == 7
    # ordered by total descending
    totals = [c["total"] for c in cats]
    assert totals == sorted(totals, reverse=True)
    # each row has required keys
    for c in cats:
        assert {"name", "total"} <= c.keys()
    # top category is Bills
    assert cats[0]["name"] == "Bills"


def test_get_category_breakdown_no_expenses(app):
    uid = _new_user_id()
    assert get_category_breakdown(uid) == []


# ------------------------------------------------------------------ #
# /profile route                                                      #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated_redirects(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_authenticated_returns_200(client):
    with client.session_transaction() as sess:
        sess["user_id"] = _seed_user_id()
    resp = client.get("/profile")
    assert resp.status_code == 200


def test_profile_shows_real_user_data(client):
    with client.session_transaction() as sess:
        sess["user_id"] = _seed_user_id()
    resp = client.get("/profile")
    body = resp.data.decode()
    assert "Demo User" in body
    assert "demo@spendly.com" in body


def test_profile_shows_rupee_symbol(client):
    with client.session_transaction() as sess:
        sess["user_id"] = _seed_user_id()
    resp = client.get("/profile")
    assert "₹" in resp.data.decode()


def test_profile_new_user_no_crash(client, app):
    uid = _new_user_id()
    with client.session_transaction() as sess:
        sess["user_id"] = uid
    resp = client.get("/profile")
    assert resp.status_code == 200
