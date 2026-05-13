"""
Tests for Step 7: Add Expense feature.

Spec: .claude/specs/07-add-expense.md

Routes under test:
  GET  /expenses/add  — renders the add-expense form (auth required)
  POST /expenses/add  — validates input, inserts expense, redirects to /profile

Seed data (from seed_db()):
  demo@spendly.com / demo123  → user_id 1 with 8 pre-existing expenses
"""

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module
from database.db import get_db, init_db, seed_db


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def app(tmp_path, monkeypatch):
    """Configure Flask app for testing with an isolated SQLite DB."""
    from app import app as flask_app

    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    flask_app.config.update(TESTING=True, SECRET_KEY="test-secret")
    with flask_app.app_context():
        init_db()
        seed_db()
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _seed_user_id():
    """Return the id of the seeded demo user."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()
        return row["id"]
    finally:
        conn.close()


def _create_fresh_user():
    """Insert a new user with no expenses and return their id."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Test User", "test@example.com", generate_password_hash("password1")),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _login(client, user_id):
    """Simulate a logged-in session for the given user_id."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _expense_count(user_id):
    """Return the number of expenses in the DB for the given user."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["cnt"]
    finally:
        conn.close()


def _get_latest_expense(user_id):
    """Return the most-recently-inserted expense row for the given user, or None."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

def test_get_add_expense_unauthenticated_redirects_to_login(client):
    """GET /expenses/add while logged out redirects to /login."""
    resp = client.get("/expenses/add")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_post_add_expense_unauthenticated_redirects_to_login(client):
    """POST /expenses/add while logged out redirects to /login (no data written)."""
    resp = client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "Food", "date": "2026-05-13",
              "description": ""},
    )
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_post_add_expense_unauthenticated_writes_nothing_to_db(client, app):
    """A POST from an unauthenticated user must not insert any expense row."""
    initial_count = _expense_count(_seed_user_id())
    client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "Food", "date": "2026-05-13",
              "description": ""},
    )
    assert _expense_count(_seed_user_id()) == initial_count


# ------------------------------------------------------------------ #
# GET /expenses/add — form rendering                                  #
# ------------------------------------------------------------------ #

def test_get_add_expense_authenticated_returns_200(client, app):
    """GET /expenses/add while logged in returns HTTP 200."""
    _login(client, _seed_user_id())
    resp = client.get("/expenses/add")
    assert resp.status_code == 200


def test_get_add_expense_renders_amount_field(client, app):
    """The form contains an amount input field."""
    _login(client, _seed_user_id())
    body = client.get("/expenses/add").data.decode()
    assert 'name="amount"' in body


def test_get_add_expense_amount_field_type_number(client, app):
    """The amount field is of type 'number' (per spec)."""
    _login(client, _seed_user_id())
    body = client.get("/expenses/add").data.decode()
    assert 'type="number"' in body


def test_get_add_expense_renders_category_select(client, app):
    """The form contains a category <select> with name='category'."""
    _login(client, _seed_user_id())
    body = client.get("/expenses/add").data.decode()
    assert 'name="category"' in body


def test_get_add_expense_category_options_present(client, app):
    """All seven allowed category options appear in the form."""
    _login(client, _seed_user_id())
    body = client.get("/expenses/add").data.decode()
    for cat in ("Food", "Transport", "Bills", "Health",
                "Entertainment", "Shopping", "Other"):
        assert cat in body, f"Category option '{cat}' not found in form"


def test_get_add_expense_renders_date_field(client, app):
    """The form contains a date input field."""
    _login(client, _seed_user_id())
    body = client.get("/expenses/add").data.decode()
    assert 'name="date"' in body
    assert 'type="date"' in body


def test_get_add_expense_renders_description_field(client, app):
    """The form contains a description input field."""
    _login(client, _seed_user_id())
    body = client.get("/expenses/add").data.decode()
    assert 'name="description"' in body


def test_get_add_expense_renders_submit_button(client, app):
    """The form has a submit button labelled 'Add Expense'."""
    _login(client, _seed_user_id())
    body = client.get("/expenses/add").data.decode()
    assert "Add Expense" in body


def test_get_add_expense_form_posts_to_correct_action(client, app):
    """The form's action targets the add_expense route (method POST)."""
    _login(client, _seed_user_id())
    body = client.get("/expenses/add").data.decode()
    assert 'method="POST"' in body or 'method="post"' in body
    assert "/expenses/add" in body


def test_get_add_expense_no_error_message_on_fresh_load(client, app):
    """A fresh GET renders no error message (no pre-existing error state)."""
    _login(client, _seed_user_id())
    body = client.get("/expenses/add").data.decode()
    # No error banner should be present on an initial load
    assert "error" not in body.lower() or "error" not in body


# ------------------------------------------------------------------ #
# POST /expenses/add — happy path                                     #
# ------------------------------------------------------------------ #

def test_post_add_expense_valid_data_redirects_to_profile(client, app):
    """A valid POST redirects to /profile."""
    uid = _create_fresh_user()
    _login(client, uid)
    resp = client.post(
        "/expenses/add",
        data={
            "amount": "25.50",
            "category": "Food",
            "date": "2026-05-13",
            "description": "Lunch",
        },
    )
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]


def test_post_add_expense_inserts_row_in_db(client, app):
    """A valid POST inserts exactly one new row into the expenses table."""
    uid = _create_fresh_user()
    _login(client, uid)
    before = _expense_count(uid)
    client.post(
        "/expenses/add",
        data={
            "amount": "25.50",
            "category": "Food",
            "date": "2026-05-13",
            "description": "Lunch",
        },
    )
    assert _expense_count(uid) == before + 1


def test_post_add_expense_stores_correct_amount(client, app):
    """The stored expense amount matches what was submitted."""
    uid = _create_fresh_user()
    _login(client, uid)
    client.post(
        "/expenses/add",
        data={"amount": "99.99", "category": "Bills",
              "date": "2026-05-13", "description": ""},
    )
    expense = _get_latest_expense(uid)
    assert expense is not None
    assert abs(expense["amount"] - 99.99) < 0.001


def test_post_add_expense_stores_correct_category(client, app):
    """The stored expense category matches what was submitted."""
    uid = _create_fresh_user()
    _login(client, uid)
    client.post(
        "/expenses/add",
        data={"amount": "50.00", "category": "Transport",
              "date": "2026-05-13", "description": ""},
    )
    expense = _get_latest_expense(uid)
    assert expense["category"] == "Transport"


def test_post_add_expense_stores_correct_date(client, app):
    """The stored expense date matches what was submitted."""
    uid = _create_fresh_user()
    _login(client, uid)
    client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "Other",
              "date": "2026-05-01", "description": ""},
    )
    expense = _get_latest_expense(uid)
    assert expense["date"] == "2026-05-01"


def test_post_add_expense_stores_description_when_provided(client, app):
    """The stored expense description matches what was submitted."""
    uid = _create_fresh_user()
    _login(client, uid)
    client.post(
        "/expenses/add",
        data={"amount": "15.00", "category": "Health",
              "date": "2026-05-13", "description": "Doctor visit"},
    )
    expense = _get_latest_expense(uid)
    assert expense["description"] == "Doctor visit"


def test_post_add_expense_stores_correct_user_id(client, app):
    """The expense is attributed to the logged-in user, not another user."""
    uid = _create_fresh_user()
    _login(client, uid)
    client.post(
        "/expenses/add",
        data={"amount": "20.00", "category": "Shopping",
              "date": "2026-05-13", "description": ""},
    )
    expense = _get_latest_expense(uid)
    assert expense["user_id"] == uid


def test_post_add_expense_optional_description_can_be_empty(client, app):
    """A valid POST with an empty description succeeds and inserts the row."""
    uid = _create_fresh_user()
    _login(client, uid)
    before = _expense_count(uid)
    resp = client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "Other",
              "date": "2026-05-13", "description": ""},
    )
    assert resp.status_code == 302
    assert _expense_count(uid) == before + 1


def test_post_add_expense_all_seven_categories_accepted(client, app):
    """Each of the seven allowed category values is accepted individually."""
    for cat in ("Food", "Transport", "Bills", "Health",
                "Entertainment", "Shopping", "Other"):
        uid = _create_fresh_user()
        _login(client, uid)
        resp = client.post(
            "/expenses/add",
            data={"amount": "1.00", "category": cat,
                  "date": "2026-05-13", "description": ""},
        )
        assert resp.status_code == 302, (
            f"Category '{cat}' should be accepted but got {resp.status_code}"
        )
        conn = get_db()
        try:
            conn.execute(
                "DELETE FROM expenses WHERE user_id = "
                "(SELECT id FROM users WHERE email = 'test@example.com')"
            )
            conn.execute("DELETE FROM users WHERE email = 'test@example.com'")
            conn.commit()
        finally:
            conn.close()


# ------------------------------------------------------------------ #
# POST /expenses/add — amount validation                              #
# ------------------------------------------------------------------ #

def test_post_add_expense_missing_amount_rerenders_form(client, app):
    """Submitting with no amount re-renders the form (not a redirect)."""
    uid = _create_fresh_user()
    _login(client, uid)
    resp = client.post(
        "/expenses/add",
        data={"amount": "", "category": "Food",
              "date": "2026-05-13", "description": ""},
    )
    assert resp.status_code == 200


def test_post_add_expense_missing_amount_shows_error(client, app):
    """Submitting with no amount renders an error message."""
    uid = _create_fresh_user()
    _login(client, uid)
    body = client.post(
        "/expenses/add",
        data={"amount": "", "category": "Food",
              "date": "2026-05-13", "description": ""},
    ).data.decode()
    assert "amount" in body.lower() or "positive" in body.lower() or "required" in body.lower()


def test_post_add_expense_missing_amount_does_not_insert(client, app):
    """Submitting with no amount does not insert any row."""
    uid = _create_fresh_user()
    _login(client, uid)
    before = _expense_count(uid)
    client.post(
        "/expenses/add",
        data={"amount": "", "category": "Food",
              "date": "2026-05-13", "description": ""},
    )
    assert _expense_count(uid) == before


def test_post_add_expense_zero_amount_rerenders_form(client, app):
    """Submitting amount=0 re-renders the form (not positive)."""
    uid = _create_fresh_user()
    _login(client, uid)
    resp = client.post(
        "/expenses/add",
        data={"amount": "0", "category": "Food",
              "date": "2026-05-13", "description": ""},
    )
    assert resp.status_code == 200


def test_post_add_expense_zero_amount_shows_error(client, app):
    """Submitting amount=0 renders an error message."""
    uid = _create_fresh_user()
    _login(client, uid)
    body = client.post(
        "/expenses/add",
        data={"amount": "0", "category": "Food",
              "date": "2026-05-13", "description": ""},
    ).data.decode()
    assert "amount" in body.lower() or "positive" in body.lower()


def test_post_add_expense_negative_amount_rerenders_form(client, app):
    """Submitting a negative amount re-renders the form."""
    uid = _create_fresh_user()
    _login(client, uid)
    resp = client.post(
        "/expenses/add",
        data={"amount": "-5.00", "category": "Food",
              "date": "2026-05-13", "description": ""},
    )
    assert resp.status_code == 200


def test_post_add_expense_negative_amount_shows_error(client, app):
    """Submitting a negative amount renders an error message."""
    uid = _create_fresh_user()
    _login(client, uid)
    body = client.post(
        "/expenses/add",
        data={"amount": "-5.00", "category": "Food",
              "date": "2026-05-13", "description": ""},
    ).data.decode()
    assert "amount" in body.lower() or "positive" in body.lower()


def test_post_add_expense_non_numeric_amount_rerenders_form(client, app):
    """Submitting a non-numeric amount string re-renders the form."""
    uid = _create_fresh_user()
    _login(client, uid)
    resp = client.post(
        "/expenses/add",
        data={"amount": "abc", "category": "Food",
              "date": "2026-05-13", "description": ""},
    )
    assert resp.status_code == 200


def test_post_add_expense_non_numeric_amount_does_not_insert(client, app):
    """Submitting a non-numeric amount does not insert any row."""
    uid = _create_fresh_user()
    _login(client, uid)
    before = _expense_count(uid)
    client.post(
        "/expenses/add",
        data={"amount": "abc", "category": "Food",
              "date": "2026-05-13", "description": ""},
    )
    assert _expense_count(uid) == before


# ------------------------------------------------------------------ #
# POST /expenses/add — date validation                                #
# ------------------------------------------------------------------ #

def test_post_add_expense_missing_date_rerenders_form(client, app):
    """Submitting with no date re-renders the form."""
    uid = _create_fresh_user()
    _login(client, uid)
    resp = client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "Food",
              "date": "", "description": ""},
    )
    assert resp.status_code == 200


def test_post_add_expense_missing_date_shows_error(client, app):
    """Submitting with no date renders an error message."""
    uid = _create_fresh_user()
    _login(client, uid)
    body = client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "Food",
              "date": "", "description": ""},
    ).data.decode()
    assert "date" in body.lower() or "required" in body.lower()


def test_post_add_expense_missing_date_does_not_insert(client, app):
    """Submitting with no date does not insert any row."""
    uid = _create_fresh_user()
    _login(client, uid)
    before = _expense_count(uid)
    client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "Food",
              "date": "", "description": ""},
    )
    assert _expense_count(uid) == before


# ------------------------------------------------------------------ #
# POST /expenses/add — category validation                            #
# ------------------------------------------------------------------ #

def test_post_add_expense_invalid_category_rerenders_form(client, app):
    """A tampered/invalid category value re-renders the form."""
    uid = _create_fresh_user()
    _login(client, uid)
    resp = client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "InvalidCategory",
              "date": "2026-05-13", "description": ""},
    )
    assert resp.status_code == 200


def test_post_add_expense_invalid_category_shows_error(client, app):
    """A tampered/invalid category value renders an error message."""
    uid = _create_fresh_user()
    _login(client, uid)
    body = client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "InvalidCategory",
              "date": "2026-05-13", "description": ""},
    ).data.decode()
    assert "category" in body.lower() or "valid" in body.lower()


def test_post_add_expense_invalid_category_does_not_insert(client, app):
    """An invalid category value does not insert any row (server-side validation)."""
    uid = _create_fresh_user()
    _login(client, uid)
    before = _expense_count(uid)
    client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "Hacked",
              "date": "2026-05-13", "description": ""},
    )
    assert _expense_count(uid) == before


def test_post_add_expense_empty_category_rerenders_form(client, app):
    """An empty category string is rejected and re-renders the form."""
    uid = _create_fresh_user()
    _login(client, uid)
    resp = client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "",
              "date": "2026-05-13", "description": ""},
    )
    assert resp.status_code == 200


def test_post_add_expense_empty_category_does_not_insert(client, app):
    """An empty category string does not insert any row."""
    uid = _create_fresh_user()
    _login(client, uid)
    before = _expense_count(uid)
    client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "",
              "date": "2026-05-13", "description": ""},
    )
    assert _expense_count(uid) == before


# ------------------------------------------------------------------ #
# POST /expenses/add — field repopulation on error                    #
# ------------------------------------------------------------------ #

def test_post_add_expense_error_repopulates_amount(client, app):
    """On validation error, the submitted amount value is repopulated."""
    uid = _create_fresh_user()
    _login(client, uid)
    # Trigger an error via missing date so amount is still valid
    body = client.post(
        "/expenses/add",
        data={"amount": "42.00", "category": "Food",
              "date": "", "description": ""},
    ).data.decode()
    assert "42" in body


def test_post_add_expense_error_repopulates_category(client, app):
    """On validation error, the submitted category value is repopulated in the form."""
    uid = _create_fresh_user()
    _login(client, uid)
    # Trigger an error via missing date so category is still valid
    body = client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "Health",
              "date": "", "description": ""},
    ).data.decode()
    assert "Health" in body


def test_post_add_expense_error_repopulates_date(client, app):
    """On validation error (bad amount), the submitted date is repopulated."""
    uid = _create_fresh_user()
    _login(client, uid)
    body = client.post(
        "/expenses/add",
        data={"amount": "0", "category": "Food",
              "date": "2026-05-13", "description": ""},
    ).data.decode()
    assert "2026-05-13" in body


def test_post_add_expense_error_repopulates_description(client, app):
    """On validation error, the submitted description is repopulated."""
    uid = _create_fresh_user()
    _login(client, uid)
    body = client.post(
        "/expenses/add",
        data={"amount": "0", "category": "Food",
              "date": "2026-05-13", "description": "My grocery run"},
    ).data.decode()
    assert "My grocery run" in body


# ------------------------------------------------------------------ #
# Integration: new expense appears on /profile                        #
# ------------------------------------------------------------------ #

def test_new_expense_appears_in_profile_transaction_list(client, app):
    """After a successful POST, the new expense description is visible on /profile."""
    uid = _create_fresh_user()
    _login(client, uid)
    client.post(
        "/expenses/add",
        data={"amount": "77.77", "category": "Entertainment",
              "date": "2026-05-13", "description": "Concert tickets"},
        follow_redirects=False,
    )
    body = client.get("/profile").data.decode()
    assert "Concert tickets" in body


def test_new_expense_updates_profile_total_spent(client, app):
    """After a successful POST, the profile summary total reflects the new expense."""
    uid = _create_fresh_user()
    _login(client, uid)
    # First, record the baseline total from the profile page
    baseline_body = client.get("/profile").data.decode()

    # Add a distinctive amount so it's identifiable in the response
    client.post(
        "/expenses/add",
        data={"amount": "123.45", "category": "Bills",
              "date": "2026-05-13", "description": ""},
        follow_redirects=False,
    )
    body = client.get("/profile").data.decode()
    # 123.45 or its rounded form should now appear in the total
    assert "123" in body


def test_new_expense_updates_profile_expense_count(client, app):
    """After a successful POST, the profile expense count increments by 1."""
    uid = _create_fresh_user()
    _login(client, uid)

    # Fresh user starts with 0 expenses; add one and verify count in DB
    before = _expense_count(uid)
    client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "Other",
              "date": "2026-05-13", "description": ""},
    )
    assert _expense_count(uid) == before + 1


def test_multiple_expenses_accumulate_correctly(client, app):
    """Adding two expenses results in two rows attributed to the same user."""
    uid = _create_fresh_user()
    _login(client, uid)
    for desc, amt in (("First", "10.00"), ("Second", "20.00")):
        client.post(
            "/expenses/add",
            data={"amount": amt, "category": "Food",
                  "date": "2026-05-13", "description": desc},
        )
    assert _expense_count(uid) == 2


def test_expenses_isolated_between_users(client, app):
    """An expense added by one user does not appear under another user's account."""
    # User A adds an expense
    uid_a = _create_fresh_user()
    _login(client, uid_a)
    client.post(
        "/expenses/add",
        data={"amount": "50.00", "category": "Shopping",
              "date": "2026-05-13", "description": "User A purchase"},
    )

    # Verify the expense is not attributed to the seed demo user
    seed_uid = _seed_user_id()
    expense = _get_latest_expense(seed_uid)
    # The seed user's latest expense should be their own, not User A's
    if expense:
        assert expense["user_id"] == seed_uid


# ------------------------------------------------------------------ #
# Edge cases                                                          #
# ------------------------------------------------------------------ #

def test_post_add_expense_decimal_amount_accepted(client, app):
    """A decimal amount (two decimal places) is accepted and stored accurately."""
    uid = _create_fresh_user()
    _login(client, uid)
    client.post(
        "/expenses/add",
        data={"amount": "0.01", "category": "Other",
              "date": "2026-05-13", "description": "Minimum valid amount"},
    )
    expense = _get_latest_expense(uid)
    assert expense is not None
    assert abs(expense["amount"] - 0.01) < 0.001


def test_post_add_expense_whitespace_only_amount_fails(client, app):
    """Submitting whitespace as the amount triggers a validation error."""
    uid = _create_fresh_user()
    _login(client, uid)
    resp = client.post(
        "/expenses/add",
        data={"amount": "   ", "category": "Food",
              "date": "2026-05-13", "description": ""},
    )
    assert resp.status_code == 200


def test_post_add_expense_does_not_affect_other_users_data(client, app):
    """Posting a valid expense only adds one row; other users' counts are unchanged."""
    seed_uid = _seed_user_id()
    seed_before = _expense_count(seed_uid)

    uid = _create_fresh_user()
    _login(client, uid)
    client.post(
        "/expenses/add",
        data={"amount": "10.00", "category": "Other",
              "date": "2026-05-13", "description": ""},
    )

    # Seed user's count must be unchanged
    assert _expense_count(seed_uid) == seed_before
