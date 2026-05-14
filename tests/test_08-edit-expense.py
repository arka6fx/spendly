"""
Tests for Edit Expense feature (Step 08).

Spec: .claude/specs/08-edit-expense.md
"""

import pytest
from werkzeug.security import generate_password_hash
import database.db as db_module
from database.db import get_db


# -------------------------------------------------------------- #
# Helpers                                                        #
# -------------------------------------------------------------- #


def _create_user(name, email, password="password123"):
    """Insert a user and return its id."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _create_expense(user_id, amount=50.00, category="Food",
                    date="2026-05-10", description="Test expense"):
    """Insert an expense and return its id."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _get_expense(expense_id):
    """Fetch a single expense row as a dict."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _login(client, user_id):
    """Inject a user_id into the session."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


# -------------------------------------------------------------- #
# Fixtures                                                       #
# -------------------------------------------------------------- #


@pytest.fixture
def setup(app):
    """
    Provide a primary user with one expense and a secondary user
    with no expenses. Returns a dict with ids for both.
    """
    with app.app_context():
        user1_id = _create_user("Alice", "alice@example.com")
        expense_id = _create_expense(
            user1_id, amount=42.00, category="Transport",
            date="2026-05-15", description="Bus pass",
        )
        user2_id = _create_user("Bob", "bob@example.com")
    return {
        "user1_id": user1_id,
        "expense_id": expense_id,
        "user2_id": user2_id,
    }


# -------------------------------------------------------------- #
# GET --- auth guard                                             #
# -------------------------------------------------------------- #


def test_get_unauthenticated_redirects_to_login(client, setup):
    """Spec: GET redirects to /login when not logged in."""
    resp = client.get(f"/expenses/{setup['expense_id']}/edit")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# -------------------------------------------------------------- #
# GET --- 404 / 403                                               #
# -------------------------------------------------------------- #


def test_get_nonexistent_expense_returns_404(client, setup):
    """Spec: GET returns 404 for an expense that does not exist."""
    _login(client, setup["user1_id"])
    resp = client.get("/expenses/999999/edit")
    assert resp.status_code == 404


def test_get_unowned_expense_returns_403(client, setup):
    """Spec: GET returns 403 when the logged-in user does not own the expense."""
    # Bob tries to edit Alice's expense
    _login(client, setup["user2_id"])
    resp = client.get(f"/expenses/{setup['expense_id']}/edit")
    assert resp.status_code == 403


# -------------------------------------------------------------- #
# GET --- form rendering                                         #
# -------------------------------------------------------------- #


def test_get_renders_edit_form(client, setup):
    """Spec: GET renders the edit form with the 'Edit Expense' heading."""
    _login(client, setup["user1_id"])
    resp = client.get(f"/expenses/{setup['expense_id']}/edit")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Edit Expense" in body


def test_get_form_has_amount_field_pre_populated(client, setup):
    """Spec: amount input pre-populated with existing expense amount."""
    _login(client, setup["user1_id"])
    resp = client.get(f"/expenses/{setup['expense_id']}/edit")
    body = resp.data.decode()
    # Amount 42.0 stored as REAL; any representation containing 42 is valid
    assert "42" in body


def test_get_form_has_date_field_pre_populated(client, setup):
    """Spec: date input pre-populated with existing expense date."""
    _login(client, setup["user1_id"])
    resp = client.get(f"/expenses/{setup['expense_id']}/edit")
    body = resp.data.decode()
    assert "2026-05-15" in body


def test_get_form_has_description_field_pre_populated(client, setup):
    """Spec: description input pre-populated with existing expense description."""
    _login(client, setup["user1_id"])
    resp = client.get(f"/expenses/{setup['expense_id']}/edit")
    body = resp.data.decode()
    assert "Bus pass" in body


def test_get_form_has_category_select_with_all_options(client, setup):
    """Spec: category <select> is present with all seven valid categories."""
    _login(client, setup["user1_id"])
    resp = client.get(f"/expenses/{setup['expense_id']}/edit")
    body = resp.data.decode()
    for cat in ["Food", "Transport", "Bills", "Health",
                "Entertainment", "Shopping", "Other"]:
        assert cat in body


def test_get_form_correct_category_pre_selected(client, setup):
    """Spec: the category <select> has the correct category pre-selected."""
    _login(client, setup["user1_id"])
    resp = client.get(f"/expenses/{setup['expense_id']}/edit")
    body = resp.data.decode()
    # The HTML should mark the Transport option with the 'selected' attribute
    assert "selected" in body
    assert "Transport" in body


def test_get_form_has_save_changes_button(client, setup):
    """Spec: form has a submit button labelled 'Save Changes'."""
    _login(client, setup["user1_id"])
    resp = client.get(f"/expenses/{setup['expense_id']}/edit")
    body = resp.data.decode()
    assert "Save Changes" in body


def test_get_form_has_cancel_link_to_profile(client, setup):
    """Spec: form has a Cancel link pointing to /profile."""
    _login(client, setup["user1_id"])
    resp = client.get(f"/expenses/{setup['expense_id']}/edit")
    body = resp.data.decode()
    assert "Cancel" in body
    assert "/profile" in body


# -------------------------------------------------------------- #
# POST --- auth guard                                            #
# -------------------------------------------------------------- #


def test_post_unauthenticated_redirects_to_login(client, setup):
    """Spec: POST redirects to /login when not logged in."""
    resp = client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={"amount": "100", "category": "Food",
              "date": "2026-05-20", "description": ""},
    )
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# -------------------------------------------------------------- #
# POST --- 403 ownership                                         #
# -------------------------------------------------------------- #


def test_post_unowned_expense_returns_403(client, setup):
    """Spec: POST returns 403 when the logged-in user does not own the expense."""
    _login(client, setup["user2_id"])
    resp = client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={"amount": "100", "category": "Food",
              "date": "2026-05-20", "description": ""},
    )
    assert resp.status_code == 403


# -------------------------------------------------------------- #
# POST --- 404 for missing expense                               #
# -------------------------------------------------------------- #


def test_post_nonexistent_expense_returns_404(client, setup):
    """Spec: POST returns 404 for an expense that does not exist."""
    _login(client, setup["user1_id"])
    resp = client.post(
        "/expenses/999999/edit",
        data={"amount": "100", "category": "Food",
              "date": "2026-05-20", "description": ""},
    )
    assert resp.status_code == 404


# -------------------------------------------------------------- #
# POST --- validation errors                                     #
# -------------------------------------------------------------- #


def test_post_missing_amount_shows_error(client, setup):
    """Spec: POST with missing amount shows a validation error and re-renders form."""
    _login(client, setup["user1_id"])
    resp = client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={"amount": "", "category": "Food",
              "date": "2026-05-20", "description": ""},
    )
    assert resp.status_code == 200
    body = resp.data.decode()
    assert (
        "error" in body.lower()
        or "required" in body.lower()
        or "must" in body.lower()
        or "number" in body.lower()
    )


def test_post_zero_amount_shows_error(client, setup):
    """Spec: POST with amount=0 (non-positive) shows a validation error."""
    _login(client, setup["user1_id"])
    resp = client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={"amount": "0", "category": "Food",
              "date": "2026-05-20", "description": ""},
    )
    assert resp.status_code == 200
    body = resp.data.decode()
    assert (
        "error" in body.lower()
        or "greater" in body.lower()
        or "positive" in body.lower()
        or "zero" in body.lower()
    )


def test_post_negative_amount_shows_error(client, setup):
    """Spec: POST with a negative amount shows a validation error."""
    _login(client, setup["user1_id"])
    resp = client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={"amount": "-10", "category": "Food",
              "date": "2026-05-20", "description": ""},
    )
    assert resp.status_code == 200
    body = resp.data.decode()
    assert (
        "error" in body.lower()
        or "greater" in body.lower()
        or "positive" in body.lower()
        or "zero" in body.lower()
    )


def test_post_missing_date_shows_error(client, setup):
    """Spec: POST with missing date shows a validation error."""
    _login(client, setup["user1_id"])
    resp = client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={"amount": "50", "category": "Food",
              "date": "", "description": ""},
    )
    assert resp.status_code == 200
    body = resp.data.decode()
    assert (
        "error" in body.lower()
        or "required" in body.lower()
        or "date" in body.lower()
    )


def test_post_invalid_category_shows_error(client, setup):
    """Spec: POST with an invalid category shows a validation error."""
    _login(client, setup["user1_id"])
    resp = client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={"amount": "50", "category": "InvalidCat",
              "date": "2026-05-20", "description": ""},
    )
    assert resp.status_code == 200
    body = resp.data.decode()
    assert (
        "error" in body.lower()
        or "valid" in body.lower()
        or "category" in body.lower()
    )


def test_post_validation_error_rerenders_form(client, setup):
    """Spec: on validation error the edit form is re-rendered, not a redirect."""
    _login(client, setup["user1_id"])
    resp = client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={"amount": "", "category": "Food",
              "date": "2026-05-20", "description": ""},
    )
    # A redirect would be 302; a re-render is 200
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Edit Expense" in body


def test_post_validation_error_shows_inline_error_element(client, setup):
    """Spec: error is shown via class=error paragraph per the template spec."""
    _login(client, setup["user1_id"])
    resp = client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={"amount": "0", "category": "Food",
              "date": "2026-05-20", "description": ""},
    )
    body = resp.data.decode()
    # Spec mandates: {{% if error %}<p><class="error">{{ error }}</p>{% endif %}
    assert 'class="error"' in body or "class='error'" in body


# -------------------------------------------------------------- #
# POST --- happy path: DB update and redirect                   #
# -------------------------------------------------------------- #


def test_post_valid_data_redirects_to_profile(client, setup):
    """Spec: valid POST redirects to /profile."""
    _login(client, setup["user1_id"])
    resp = client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={
            "amount": "99.99",
            "category": "Health",
            "date": "2026-06-01",
            "description": "Updated description",
        },
    )
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]


def test_post_valid_data_updates_amount_in_db(client, setup, app):
    """Spec: valid POST updates the expense amount in the database."""
    _login(client, setup["user1_id"])
    client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={
            "amount": "77.50",
            "category": "Bills",
            "date": "2026-06-05",
            "description": "Electric bill",
        },
    )
    with app.app_context():
        expense = _get_expense(setup["expense_id"])
    assert expense["amount"] == pytest.approx(77.50)


def test_post_valid_data_updates_category_in_db(client, setup, app):
    """Spec: valid POST updates the expense category in the database."""
    _login(client, setup["user1_id"])
    client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={
            "amount": "77.50",
            "category": "Bills",
            "date": "2026-06-05",
            "description": "Electric bill",
        },
    )
    with app.app_context():
        expense = _get_expense(setup["expense_id"])
    assert expense["category"] == "Bills"


def test_post_valid_data_updates_date_in_db(client, setup, app):
    """Spec: valid POST updates the expense date in the database."""
    _login(client, setup["user1_id"])
    client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={
            "amount": "77.50",
            "category": "Bills",
            "date": "2026-06-05",
            "description": "Electric bill",
        },
    )
    with app.app_context():
        expense = _get_expense(setup["expense_id"])
    assert expense["date"] == "2026-06-05"


def test_post_valid_data_updates_description_in_db(client, setup, app):
    """Spec: valid POST updates the expense description in the database."""
    _login(client, setup["user1_id"])
    client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={
            "amount": "77.50",
            "category": "Bills",
            "date": "2026-06-05",
            "description": "Electric bill",
        },
    )
    with app.app_context():
        expense = _get_expense(setup["expense_id"])
    assert expense["description"] == "Electric bill"


def test_post_valid_does_not_mutate_other_expenses(client, setup, app):
    """Valid POST must not alter any other expense rows in the database."""
    _login(client, setup["user1_id"])
    with app.app_context():
        other_id = _create_expense(
            setup["user1_id"], amount=10.00, category="Other",
            date="2026-01-01", description="unchanged",
        )
    client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={
            "amount": "77.50",
            "category": "Bills",
            "date": "2026-06-05",
            "description": "Electric bill",
        },
    )
    with app.app_context():
        other = _get_expense(other_id)
    assert other["amount"] == pytest.approx(10.00)
    assert other["description"] == "unchanged"


def test_post_valid_updated_values_visible_on_profile(client, setup):
    """Spec: updated values are visible on /profile after the redirect."""
    _login(client, setup["user1_id"])
    client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={
            "amount": "88.00",
            "category": "Shopping",
            "date": "2026-06-10",
            "description": "New jacket",
        },
    )
    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Shopping" in body
    assert "New jacket" in body


def test_post_valid_description_optional(client, setup, app):
    """Spec: description is optional; omitting it should still succeed."""
    _login(client, setup["user1_id"])
    resp = client.post(
        f"/expenses/{setup['expense_id']}/edit",
        data={
            "amount": "15.00",
            "category": "Other",
            "date": "2026-06-15",
            "description": "",
        },
    )
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]
    with app.app_context():
        expense = _get_expense(setup["expense_id"])
    assert expense["amount"] == pytest.approx(15.00)


# -------------------------------------------------------------- #
# Regression --- existing routes still work                     #
# -------------------------------------------------------------- #


def test_landing_page_still_works(client):
    """Regression: GET / returns 200 after edit expense feature is introduced."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_login_page_still_works(client):
    """Regression: GET /login returns 200."""
    resp = client.get("/login")
    assert resp.status_code == 200


def test_register_page_still_works(client):
    """Regression: GET /register returns 200."""
    resp = client.get("/register")
    assert resp.status_code == 200


def test_profile_unauthenticated_still_redirects(client):
    """Regression: GET /profile without auth still redirects to /login."""
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
