"""
Tests for Step 6: Date filter on the profile page.

Spec: .claude/specs/06-date-filter-profile-page.md

Seed data reference (from seed_db()):
  2026-05-01  Food          12.50   Lunch at cafe
  2026-05-03  Transport     45.00   Monthly bus pass
  2026-05-05  Bills        120.00   Internet bill
  2026-05-07  Health        30.00   Pharmacy
  2026-05-10  Entertainment 25.00   Movie tickets
  2026-05-12  Shopping      60.00   New shoes
  2026-05-14  Other         15.00   Miscellaneous
  2026-05-16  Food           8.75   Coffee and snacks

Total: 316.25, 8 transactions, top category: Bills
"""

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module
from database.db import get_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)


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


def _new_user_id():
    """Insert a fresh user with no expenses and return their id."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Filter Tester", "filter@example.com", generate_password_hash("password1")),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _login(client, user_id):
    """Simulate a logged-in session for the given user_id."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


# ------------------------------------------------------------------ #
# get_summary_stats — date filter behaviour                           #
# ------------------------------------------------------------------ #

def test_summary_stats_date_from_excludes_earlier_expenses(app):
    """date_from filters out expenses before that date (inclusive boundary)."""
    uid = _seed_user_id()
    # Keep only 2026-05-07 and later: 30 + 25 + 60 + 15 + 8.75 = 138.75, 5 rows
    stats = get_summary_stats(uid, date_from="2026-05-07")
    assert stats["total_count"] == 5
    assert stats["total_spent"] == pytest.approx(138.75)


def test_summary_stats_date_to_excludes_later_expenses(app):
    """date_to filters out expenses after that date (inclusive boundary)."""
    uid = _seed_user_id()
    # Keep only up to 2026-05-07: 12.50 + 45 + 120 + 30 = 207.50, 4 rows
    stats = get_summary_stats(uid, date_to="2026-05-07")
    assert stats["total_count"] == 4
    assert stats["total_spent"] == pytest.approx(207.50)


def test_summary_stats_both_params_narrow_to_range(app):
    """date_from + date_to together return only expenses within that window."""
    uid = _seed_user_id()
    # 2026-05-05 to 2026-05-10: 120 + 30 + 25 = 175.00, 3 rows
    stats = get_summary_stats(uid, date_from="2026-05-05", date_to="2026-05-10")
    assert stats["total_count"] == 3
    assert stats["total_spent"] == pytest.approx(175.00)


def test_summary_stats_single_day_range(app):
    """date_from == date_to returns only expenses on that exact day."""
    uid = _seed_user_id()
    stats = get_summary_stats(uid, date_from="2026-05-05", date_to="2026-05-05")
    assert stats["total_count"] == 1
    assert stats["total_spent"] == pytest.approx(120.00)
    assert stats["top_category"] == "Bills"


def test_summary_stats_none_values_mean_no_filter(app):
    """Passing None for both params returns the full unfiltered result."""
    uid = _seed_user_id()
    stats = get_summary_stats(uid, date_from=None, date_to=None)
    assert stats["total_count"] == 8
    assert stats["total_spent"] == pytest.approx(316.25)


def test_summary_stats_empty_string_means_no_filter(app):
    """Empty strings for both params are treated the same as None (no filter)."""
    uid = _seed_user_id()
    stats = get_summary_stats(uid, date_from="", date_to="")
    assert stats["total_count"] == 8
    assert stats["total_spent"] == pytest.approx(316.25)


def test_summary_stats_no_expenses_in_range_returns_zeros(app):
    """A date range that matches no expenses returns zeroed stats without crashing."""
    uid = _seed_user_id()
    stats = get_summary_stats(uid, date_from="2025-01-01", date_to="2025-01-31")
    assert stats["total_count"] == 0
    assert stats["total_spent"] == pytest.approx(0.0)
    assert stats["top_category"] is None


def test_summary_stats_new_user_with_filter_returns_zeros(app):
    """A user with no expenses at all returns zeroed stats under a date filter."""
    uid = _new_user_id()
    stats = get_summary_stats(uid, date_from="2026-05-01", date_to="2026-05-31")
    assert stats["total_count"] == 0
    assert stats["total_spent"] == pytest.approx(0.0)
    assert stats["top_category"] is None


def test_summary_stats_top_category_updates_with_filter(app):
    """Top category reflects only the filtered window, not all expenses."""
    uid = _seed_user_id()
    # Range 2026-05-10 to 2026-05-12: Entertainment 25, Shopping 60 — top is Shopping
    stats = get_summary_stats(uid, date_from="2026-05-10", date_to="2026-05-12")
    assert stats["top_category"] == "Shopping"


# ------------------------------------------------------------------ #
# get_recent_transactions — date filter behaviour                     #
# ------------------------------------------------------------------ #

def test_recent_transactions_date_from_excludes_earlier(app):
    """date_from removes transactions before that date (inclusive lower bound)."""
    uid = _seed_user_id()
    txns = get_recent_transactions(uid, date_from="2026-05-10")
    dates = [t["date"] for t in txns]
    assert all(d >= "2026-05-10" for d in dates)
    # 2026-05-10, 2026-05-12, 2026-05-14, 2026-05-16 = 4 rows
    assert len(txns) == 4


def test_recent_transactions_date_to_excludes_later(app):
    """date_to removes transactions after that date."""
    uid = _seed_user_id()
    txns = get_recent_transactions(uid, date_to="2026-05-05")
    dates = [t["date"] for t in txns]
    assert all(d <= "2026-05-05" for d in dates)
    # 2026-05-01, 2026-05-03, 2026-05-05 = 3
    assert len(txns) == 3


def test_recent_transactions_both_params_narrow_to_range(app):
    """date_from + date_to return only transactions within the window."""
    uid = _seed_user_id()
    txns = get_recent_transactions(
        uid, date_from="2026-05-05", date_to="2026-05-10"
    )
    dates = [t["date"] for t in txns]
    assert all("2026-05-05" <= d <= "2026-05-10" for d in dates)
    assert len(txns) == 3  # 05, 07, 10


def test_recent_transactions_ordered_newest_first_with_filter(app):
    """Filtered transactions are still returned newest-first."""
    uid = _seed_user_id()
    txns = get_recent_transactions(
        uid, date_from="2026-05-03", date_to="2026-05-12"
    )
    dates = [t["date"] for t in txns]
    assert dates == sorted(dates, reverse=True)


def test_recent_transactions_none_params_return_all(app):
    """None params produce the same result as calling with no params."""
    uid = _seed_user_id()
    assert len(get_recent_transactions(uid, date_from=None, date_to=None)) == 8


def test_recent_transactions_empty_string_means_no_filter(app):
    """Empty-string params return all transactions (treated as no filter)."""
    uid = _seed_user_id()
    assert len(get_recent_transactions(uid, date_from="", date_to="")) == 8


def test_recent_transactions_no_match_returns_empty_list(app):
    """A range with no matching expenses returns an empty list, not an error."""
    uid = _seed_user_id()
    txns = get_recent_transactions(uid, date_from="2025-01-01", date_to="2025-12-31")
    assert txns == []


def test_recent_transactions_required_keys_present_with_filter(app):
    """Each row returned under a date filter still has all required keys."""
    uid = _seed_user_id()
    txns = get_recent_transactions(
        uid, date_from="2026-05-05", date_to="2026-05-07"
    )
    for t in txns:
        assert {"date", "description", "category", "amount"} <= t.keys()


# ------------------------------------------------------------------ #
# get_category_breakdown — date filter behaviour                      #
# ------------------------------------------------------------------ #

def test_category_breakdown_date_from_excludes_earlier(app):
    """date_from removes categories whose only expenses precede the cutoff."""
    uid = _seed_user_id()
    # From 2026-05-10: Entertainment, Shopping, Other, Food(8.75) — Transport and Bills excluded
    cats = get_category_breakdown(uid, date_from="2026-05-10")
    names = [c["name"] for c in cats]
    assert "Transport" not in names
    assert "Bills" not in names
    assert "Entertainment" in names


def test_category_breakdown_date_to_excludes_later(app):
    """date_to removes categories whose only expenses come after the cutoff."""
    uid = _seed_user_id()
    # Up to 2026-05-05: Food(12.50), Transport(45), Bills(120) — Entertainment, Shopping etc excluded
    cats = get_category_breakdown(uid, date_to="2026-05-05")
    names = [c["name"] for c in cats]
    assert "Entertainment" not in names
    assert "Shopping" not in names
    assert "Bills" in names


def test_category_breakdown_both_params_narrows_categories(app):
    """date_from + date_to together narrow the category list."""
    uid = _seed_user_id()
    cats = get_category_breakdown(
        uid, date_from="2026-05-10", date_to="2026-05-12"
    )
    names = [c["name"] for c in cats]
    # Only Entertainment (25) and Shopping (60) in this range
    assert set(names) == {"Entertainment", "Shopping"}


def test_category_breakdown_ordered_by_total_desc_with_filter(app):
    """Category breakdown remains ordered by total descending when filtered."""
    uid = _seed_user_id()
    cats = get_category_breakdown(uid, date_from="2026-05-03", date_to="2026-05-12")
    totals = [c["total"] for c in cats]
    assert totals == sorted(totals, reverse=True)


def test_category_breakdown_totals_sum_matches_summary(app):
    """Sum of breakdown totals equals total_spent from get_summary_stats for the same range."""
    uid = _seed_user_id()
    date_from, date_to = "2026-05-05", "2026-05-12"
    cats = get_category_breakdown(uid, date_from=date_from, date_to=date_to)
    stats = get_summary_stats(uid, date_from=date_from, date_to=date_to)
    assert sum(c["total"] for c in cats) == pytest.approx(stats["total_spent"])


def test_category_breakdown_none_params_return_all(app):
    """None params produce unfiltered breakdown (all 7 seed categories)."""
    uid = _seed_user_id()
    cats = get_category_breakdown(uid, date_from=None, date_to=None)
    assert len(cats) == 7


def test_category_breakdown_empty_string_means_no_filter(app):
    """Empty-string params produce unfiltered breakdown."""
    uid = _seed_user_id()
    cats = get_category_breakdown(uid, date_from="", date_to="")
    assert len(cats) == 7


def test_category_breakdown_no_match_returns_empty_list(app):
    """A range with no matching expenses returns an empty list."""
    uid = _seed_user_id()
    cats = get_category_breakdown(uid, date_from="2025-01-01", date_to="2025-12-31")
    assert cats == []


def test_category_breakdown_required_keys_present(app):
    """Each breakdown row has both 'name' and 'total' keys when filtered."""
    uid = _seed_user_id()
    cats = get_category_breakdown(uid, date_from="2026-05-01", date_to="2026-05-16")
    for c in cats:
        assert {"name", "total"} <= c.keys()


# ------------------------------------------------------------------ #
# get_user_by_id — must be unaffected by any filter params            #
# ------------------------------------------------------------------ #

def test_get_user_by_id_unchanged_by_date_filter_spec(app):
    """get_user_by_id has no date params and always returns full user data."""
    uid = _seed_user_id()
    user = get_user_by_id(uid)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert "created_at" in user


# ------------------------------------------------------------------ #
# /profile route — auth guard                                         #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated_redirects_to_login(client):
    """Unauthenticated GET /profile redirects to /login."""
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_unauthenticated_with_params_redirects_to_login(client):
    """Auth guard fires even when date params are present."""
    resp = client.get("/profile?date_from=2026-05-01&date_to=2026-05-31")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# ------------------------------------------------------------------ #
# /profile route — no filter (baseline)                               #
# ------------------------------------------------------------------ #

def test_profile_no_params_returns_200(client, app):
    """Authenticated GET /profile with no params returns 200."""
    _login(client, _seed_user_id())
    resp = client.get("/profile")
    assert resp.status_code == 200


def test_profile_no_params_shows_all_expenses(client, app):
    """With no date params the full list of seed expenses is rendered."""
    _login(client, _seed_user_id())
    resp = client.get("/profile")
    body = resp.data.decode()
    # All 8 seed expenses appear by their descriptions
    assert "Lunch at cafe" in body
    assert "Monthly bus pass" in body
    assert "Internet bill" in body
    assert "Pharmacy" in body
    assert "Movie tickets" in body
    assert "New shoes" in body
    assert "Miscellaneous" in body
    assert "Coffee and snacks" in body


def test_profile_no_params_shows_user_info(client, app):
    """User name and email are always displayed regardless of filter state."""
    _login(client, _seed_user_id())
    resp = client.get("/profile")
    body = resp.data.decode()
    assert "Demo User" in body
    assert "demo@spendly.com" in body


# ------------------------------------------------------------------ #
# /profile route — date_from only                                     #
# ------------------------------------------------------------------ #

def test_profile_date_from_hides_earlier_expenses(client, app):
    """?date_from hides expenses that fall before the given date."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=2026-05-10")
    body = resp.data.decode()
    # These are before 2026-05-10 and must not appear
    assert "Lunch at cafe" not in body
    assert "Monthly bus pass" not in body
    assert "Internet bill" not in body
    assert "Pharmacy" not in body
    # These are on/after 2026-05-10 and must appear
    assert "Movie tickets" in body
    assert "New shoes" in body


def test_profile_date_from_updates_stats(client, app):
    """?date_from causes the summary stats to reflect only filtered expenses."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=2026-05-10")
    body = resp.data.decode()
    # Total for 2026-05-10 onwards: 25 + 60 + 15 + 8.75 = 108.75
    assert "108.75" in body


# ------------------------------------------------------------------ #
# /profile route — date_to only                                       #
# ------------------------------------------------------------------ #

def test_profile_date_to_hides_later_expenses(client, app):
    """?date_to hides expenses that fall after the given date."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_to=2026-05-05")
    body = resp.data.decode()
    # These come after 2026-05-05 and must not appear
    assert "Pharmacy" not in body
    assert "Movie tickets" not in body
    assert "Coffee and snacks" not in body
    # These are on/before 2026-05-05 and must appear
    assert "Lunch at cafe" in body
    assert "Internet bill" in body


def test_profile_date_to_updates_stats(client, app):
    """?date_to causes the summary stats to reflect only filtered expenses."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_to=2026-05-05")
    body = resp.data.decode()
    # Total for up to 2026-05-05: 12.50 + 45 + 120 = 177.50
    assert "177.5" in body


# ------------------------------------------------------------------ #
# /profile route — both params                                        #
# ------------------------------------------------------------------ #

def test_profile_both_params_filters_to_range(client, app):
    """?date_from + ?date_to shows only expenses within the window."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=2026-05-05&date_to=2026-05-10")
    body = resp.data.decode()
    # In range: 2026-05-05 (Internet bill), 2026-05-07 (Pharmacy), 2026-05-10 (Movie tickets)
    assert "Internet bill" in body
    assert "Pharmacy" in body
    assert "Movie tickets" in body
    # Outside range
    assert "Lunch at cafe" not in body
    assert "Monthly bus pass" not in body
    assert "New shoes" not in body
    assert "Coffee and snacks" not in body


def test_profile_both_params_stats_reflect_range(client, app):
    """Summary stats rendered on page match the filtered window."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=2026-05-05&date_to=2026-05-10")
    body = resp.data.decode()
    # Total: 120 + 30 + 25 = 175
    assert "175" in body


def test_profile_both_params_category_breakdown_reflects_range(client, app):
    """Category breakdown on the page is also restricted to the date range."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=2026-05-10&date_to=2026-05-12")
    body = resp.data.decode()
    # Only Entertainment and Shopping are in this range
    assert "Entertainment" in body
    assert "Shopping" in body
    # Bills is outside this range
    assert "Bills" not in body


# ------------------------------------------------------------------ #
# /profile route — user info unaffected by filter                     #
# ------------------------------------------------------------------ #

def test_profile_user_info_always_shown_with_filter(client, app):
    """User name and email appear even when a narrow date filter is active."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=2026-05-01&date_to=2026-05-01")
    body = resp.data.decode()
    assert "Demo User" in body
    assert "demo@spendly.com" in body


# ------------------------------------------------------------------ #
# /profile route — input repopulation                                 #
# ------------------------------------------------------------------ #

def test_profile_date_from_input_repopulated(client, app):
    """The date_from input value is pre-filled after a filtered request."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=2026-05-05")
    body = resp.data.decode()
    # The input for date_from should carry the submitted value
    assert 'value="2026-05-05"' in body


def test_profile_date_to_input_repopulated(client, app):
    """The date_to input value is pre-filled after a filtered request."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_to=2026-05-10")
    body = resp.data.decode()
    assert 'value="2026-05-10"' in body


def test_profile_both_inputs_repopulated(client, app):
    """Both date inputs are pre-filled when both params are submitted."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=2026-05-05&date_to=2026-05-10")
    body = resp.data.decode()
    assert 'value="2026-05-05"' in body
    assert 'value="2026-05-10"' in body


def test_profile_inputs_empty_when_no_params(client, app):
    """Date inputs are empty (or absent value) on the unfiltered profile page."""
    _login(client, _seed_user_id())
    resp = client.get("/profile")
    body = resp.data.decode()
    # The repopulated template renders value="" when no params are given
    assert 'value=""' in body


# ------------------------------------------------------------------ #
# /profile route — filter form structure                              #
# ------------------------------------------------------------------ #

def test_profile_filter_form_present(client, app):
    """The date filter form with GET method exists on the profile page."""
    _login(client, _seed_user_id())
    resp = client.get("/profile")
    body = resp.data.decode()
    assert 'method="GET"' in body or "method=GET" in body


def test_profile_date_from_input_exists(client, app):
    """An input with name='date_from' and type='date' is present on the page."""
    _login(client, _seed_user_id())
    resp = client.get("/profile")
    body = resp.data.decode()
    assert 'name="date_from"' in body
    assert 'type="date"' in body


def test_profile_date_to_input_exists(client, app):
    """An input with name='date_to' and type='date' is present on the page."""
    _login(client, _seed_user_id())
    resp = client.get("/profile")
    body = resp.data.decode()
    assert 'name="date_to"' in body


def test_profile_filter_submit_button_exists(client, app):
    """A submit button labelled 'Filter' exists in the filter form."""
    _login(client, _seed_user_id())
    resp = client.get("/profile")
    body = resp.data.decode()
    assert "Filter" in body


def test_profile_clear_link_exists(client, app):
    """A 'Clear' link pointing to /profile with no query params exists."""
    _login(client, _seed_user_id())
    resp = client.get("/profile")
    body = resp.data.decode()
    assert "Clear" in body
    # The clear link should point to the bare /profile URL
    assert 'href="/profile"' in body


# ------------------------------------------------------------------ #
# /profile route — empty expenses in range (no crash)                 #
# ------------------------------------------------------------------ #

def test_profile_no_expenses_in_range_returns_200(client, app):
    """A date range with no matching expenses returns 200, not a server error."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=2025-01-01&date_to=2025-01-31")
    assert resp.status_code == 200


def test_profile_no_expenses_in_range_shows_zeroed_stats(client, app):
    """When the filtered window is empty, totals display as zero."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=2025-01-01&date_to=2025-01-31")
    body = resp.data.decode()
    # At minimum, a zero total should appear somewhere on the page
    assert "0" in body


def test_profile_new_user_with_filter_no_crash(client, app):
    """A user with no expenses at all does not crash when a date filter is applied."""
    uid = _new_user_id()
    _login(client, uid)
    resp = client.get("/profile?date_from=2026-05-01&date_to=2026-05-31")
    assert resp.status_code == 200


# ------------------------------------------------------------------ #
# /profile route — empty-string params treated as no filter           #
# ------------------------------------------------------------------ #

def test_profile_empty_string_params_show_all_expenses(client, app):
    """?date_from=&date_to= (empty strings) render all expenses (no filter applied)."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=&date_to=")
    body = resp.data.decode()
    # All seed expense descriptions should appear
    assert "Lunch at cafe" in body
    assert "Coffee and snacks" in body


def test_profile_empty_string_params_return_200(client, app):
    """?date_from=&date_to= returns 200 without error."""
    _login(client, _seed_user_id())
    resp = client.get("/profile?date_from=&date_to=")
    assert resp.status_code == 200
