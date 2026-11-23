"""Step 08: get_expense_by_id(), update_expense() and /expenses/<id>/edit."""

import re
import sqlite3
import sys

import pytest

from database.db import CATEGORIES, get_db
from database.queries import (
    get_expense_by_id,
    get_recent_transactions,
    update_expense,
)

NEW_VALUES = {
    "amount": "99.0",
    "category": "Bills",
    "date": "2026-03-21",
    "description": "Updated",
}


@pytest.fixture
def owner(make_user):
    """The user who owns the expense under test."""
    return make_user(name="Owner", email="owner@example.com")


@pytest.fixture
def stranger(make_user):
    """A second real user, for the 'someone else's expense' cases."""
    return make_user(name="Stranger", email="stranger@example.com")


@pytest.fixture
def expense_id(owner, add_expense):
    return add_expense(owner, 50.0, "Food", "2026-03-20", "Lunch")


def row(expense_id):
    conn = get_db()
    try:
        found = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        return dict(found) if found else None
    finally:
        conn.close()


def post_edit(client, expense_id, **overrides):
    """POST new values. A value of None omits that field."""
    data = {**NEW_VALUES, **overrides}
    data = {key: value for key, value in data.items() if value is not None}
    return client.post(f"/expenses/{expense_id}/edit", data=data)


def error_message(html):
    match = re.search(r'<div class="auth-error">([^<]*)</div>', html)
    return match.group(1) if match else None


# ------------------------------------------------------------------ #
# get_expense_by_id                                                   #
# ------------------------------------------------------------------ #

def test_get_expense_by_id_returns_the_owners_expense(owner, expense_id):
    assert get_expense_by_id(expense_id, owner) == {
        "id": expense_id,
        "user_id": owner,
        "amount": 50.0,
        "category": "Food",
        "date": "2026-03-20",
        "description": "Lunch",
    }


def test_get_expense_by_id_for_the_wrong_user_is_none(stranger, expense_id):
    assert get_expense_by_id(expense_id, stranger) is None


def test_get_expense_by_id_for_a_missing_expense_is_none(owner):
    assert get_expense_by_id(99999, owner) is None


# ------------------------------------------------------------------ #
# update_expense                                                      #
# ------------------------------------------------------------------ #

def test_update_expense_changes_the_row_and_reports_one(owner, expense_id):
    assert update_expense(expense_id, owner, 99.0, "Bills", "2026-03-21", "Updated") == 1
    saved = row(expense_id)
    assert (saved["amount"], saved["category"], saved["date"], saved["description"]) == (
        99.0, "Bills", "2026-03-21", "Updated",
    )


def test_update_expense_never_changes_the_owner_or_creation_time(owner, expense_id):
    before = row(expense_id)
    update_expense(expense_id, owner, 99.0, "Bills", "2026-03-21", None)
    after = row(expense_id)
    assert after["user_id"] == before["user_id"] == owner
    assert after["created_at"] == before["created_at"]
    assert after["description"] is None


def test_update_expense_for_the_wrong_user_changes_nothing(stranger, expense_id):
    before = row(expense_id)
    assert update_expense(expense_id, stranger, 99.0, "Bills", "2026-03-21", "Hacked") == 0
    assert row(expense_id) == before


def test_update_expense_for_a_missing_expense_reports_zero(owner):
    assert update_expense(99999, owner, 99.0, "Bills", "2026-03-21", "x") == 0


# ------------------------------------------------------------------ #
# get_recent_transactions carries the id                              #
# ------------------------------------------------------------------ #

def test_recent_transactions_include_the_expense_id(owner, add_expense):
    first = add_expense(owner, 1.0, "Food", "2026-03-01", "a")
    second = add_expense(owner, 2.0, "Food", "2026-03-02", "b")
    assert [item["id"] for item in get_recent_transactions(owner)] == [second, first]


# ------------------------------------------------------------------ #
# Access control                                                      #
# ------------------------------------------------------------------ #

def test_get_logged_out_redirects_to_login(client, expense_id):
    response = client.get(f"/expenses/{expense_id}/edit")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_post_logged_out_redirects_and_changes_nothing(client, expense_id):
    before = row(expense_id)
    response = post_edit(client, expense_id)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert row(expense_id) == before


@pytest.mark.parametrize("method", ["get", "post"])
def test_logged_out_request_for_a_missing_expense_still_redirects(client, method):
    """The login check comes first, so a logged-out visitor learns nothing."""
    response = getattr(client, method)("/expenses/99999/edit")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize("method", ["get", "post"])
def test_another_users_expense_is_a_404(client, login, stranger, expense_id, method):
    login(stranger)
    before = row(expense_id)
    response = getattr(client, method)(f"/expenses/{expense_id}/edit", data=NEW_VALUES if method == "post" else None)
    assert response.status_code == 404
    assert row(expense_id) == before


@pytest.mark.parametrize("method", ["get", "post"])
def test_a_missing_expense_is_a_404(client, login, owner, method):
    login(owner)
    response = getattr(client, method)("/expenses/99999/edit", data=NEW_VALUES if method == "post" else None)
    assert response.status_code == 404


@pytest.mark.parametrize("path", ["/expenses/abc/edit", "/expenses/-1/edit", "/expenses/0/edit"])
def test_unusable_ids_are_a_404(client, login, owner, path):
    login(owner)
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("method", ["get", "post"])
def test_a_session_for_a_deleted_user_gets_404_not_a_server_error(client, login, expense_id, method):
    login(99999)
    response = getattr(client, method)(f"/expenses/{expense_id}/edit", data=NEW_VALUES if method == "post" else None)
    assert response.status_code == 404


# ------------------------------------------------------------------ #
# The form page                                                       #
# ------------------------------------------------------------------ #

def test_get_shows_the_form_filled_with_the_current_values(client, login, owner, expense_id):
    login(owner)
    response = client.get(f"/expenses/{expense_id}/edit")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'value="50.00"' in html
    assert 'value="2026-03-20"' in html
    assert 'value="Lunch"' in html
    assert re.search(r'<form method="post" action="/expenses/%d/edit"' % expense_id, html)
    assert ">Save Changes</button>" in html
    assert 'href="/profile">Cancel</a>' in html


def test_get_preselects_the_current_category(client, login, owner, add_expense):
    for category in CATEGORIES:
        expense = add_expense(owner, 5.0, category, "2026-03-01", None)
        login(owner)
        html = client.get(f"/expenses/{expense}/edit").get_data(as_text=True)
        select = html.split('<select id="category"')[1].split("</select>")[0]
        assert re.findall(r'<option value="([^"]*)"', select) == CATEGORIES
        assert select.count(" selected>") == 1
        assert f'<option value="{category}" selected>' in select


def test_get_shows_an_empty_field_for_a_null_description(client, login, owner, add_expense):
    expense = add_expense(owner, 5.0, "Food", "2026-03-01", None)
    login(owner)
    html = client.get(f"/expenses/{expense}/edit").get_data(as_text=True)
    assert 'name="description"' in html
    assert re.search(r'name="description"[^>]*value=""', html, re.S)
    assert "None" not in html


# ------------------------------------------------------------------ #
# Saving                                                              #
# ------------------------------------------------------------------ #

def test_valid_post_redirects_to_profile_and_updates_the_row(client, login, owner, expense_id):
    login(owner)
    response = post_edit(client, expense_id)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    saved = row(expense_id)
    assert (saved["amount"], saved["category"], saved["date"], saved["description"]) == (
        99.0, "Bills", "2026-03-21", "Updated",
    )


def test_edit_replaces_the_row_it_does_not_add_one(client, login, owner, expense_id, add_expense):
    other_expense = add_expense(owner, 7.0, "Other", "2026-03-02", "untouched")
    login(owner)
    post_edit(client, expense_id)
    conn = get_db()
    try:
        assert conn.execute("SELECT COUNT(*) FROM expenses WHERE user_id = ?", (owner,)).fetchone()[0] == 2
    finally:
        conn.close()
    assert row(other_expense)["description"] == "untouched"


def test_edit_keeps_the_owner_and_creation_time(client, login, owner, expense_id):
    before = row(expense_id)
    login(owner)
    post_edit(client, expense_id)
    after = row(expense_id)
    assert after["user_id"] == before["user_id"]
    assert after["created_at"] == before["created_at"]


def test_updated_values_appear_on_the_profile_page(client, login, owner, expense_id):
    login(owner)
    html = client.post(f"/expenses/{expense_id}/edit", data=NEW_VALUES, follow_redirects=True).get_data(as_text=True)
    assert "Updated" in html and "₹99.00" in html
    assert "Lunch" not in html and "₹50.00" not in html


def test_future_date_is_accepted(client, login, owner, expense_id):
    login(owner)
    response = post_edit(client, expense_id, date="2031-01-01")
    assert response.status_code == 302
    assert row(expense_id)["date"] == "2031-01-01"


def test_unpadded_date_is_stored_in_iso_form(client, login, owner, expense_id):
    login(owner)
    post_edit(client, expense_id, date="2026-3-5")
    assert row(expense_id)["date"] == "2026-03-05"


@pytest.mark.parametrize("description", [None, "", "   "])
def test_missing_or_blank_description_becomes_null(client, login, owner, expense_id, description):
    login(owner)
    response = post_edit(client, expense_id, description=description)
    assert response.status_code == 302
    assert row(expense_id)["description"] is None


def test_description_is_stripped_and_limited(client, login, owner, expense_id):
    login(owner)
    post_edit(client, expense_id, description="  Trimmed  ")
    assert row(expense_id)["description"] == "Trimmed"
    assert post_edit(client, expense_id, description="x" * 200).status_code == 302
    assert post_edit(client, expense_id, description="x" * 201).status_code == 200
    assert len(row(expense_id)["description"]) == 200


def test_zero_rows_changed_is_a_404(client, login, owner, expense_id, monkeypatch):
    """If the row vanishes between the lookup and the update, the answer is 404."""
    monkeypatch.setattr(sys.modules["app"], "update_expense", lambda *args, **kwargs: 0)
    login(owner)
    assert post_edit(client, expense_id).status_code == 404


# ------------------------------------------------------------------ #
# Validation                                                          #
# ------------------------------------------------------------------ #

INVALID_CASES = [
    ("missing amount", {"amount": None}, "Amount is required."),
    ("zero amount", {"amount": "0"}, "greater than zero"),
    ("negative amount", {"amount": "-5"}, "greater than zero"),
    ("non-numeric amount", {"amount": "abc"}, "must be a number"),
    ("nan amount", {"amount": "nan"}, "must be a number"),
    ("infinite amount", {"amount": "inf"}, "must be a number"),
    ("three decimal places", {"amount": "10.555"}, "two decimal places"),
    ("category outside the list", {"category": "Gifts"}, "valid category"),
    ("lower-case category", {"category": "food"}, "valid category"),
    ("missing date", {"date": None}, "Date is required."),
    ("malformed date", {"date": "not-a-date"}, "valid date"),
    ("calendar-impossible date", {"date": "2026-02-30"}, "valid date"),
    ("description over 200 characters", {"description": "x" * 201}, "200 characters"),
]


@pytest.mark.parametrize("label, overrides, message", INVALID_CASES, ids=[c[0] for c in INVALID_CASES])
def test_invalid_submission_shows_an_error_and_changes_nothing(client, login, owner, expense_id, label, overrides, message):
    login(owner)
    before = row(expense_id)
    response = post_edit(client, expense_id, **overrides)
    assert response.status_code == 200
    assert message in (error_message(response.get_data(as_text=True)) or "")
    assert row(expense_id) == before


def test_failed_submission_shows_the_submitted_values_not_the_stored_ones(client, login, owner, expense_id):
    login(owner)
    response = post_edit(client, expense_id, amount="10.555", category="Health", date="2026-04-01", description="typed")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'value="10.555"' in html
    assert 'value="2026-04-01"' in html
    assert 'value="typed"' in html
    assert '<option value="Health" selected>' in html
    assert html.count(" selected>") == 1
    assert 'value="50.00"' not in html and 'value="Lunch"' not in html
    assert f'action="/expenses/{expense_id}/edit"' in html


# ------------------------------------------------------------------ #
# Edit links on the profile page                                      #
# ------------------------------------------------------------------ #

def edit_links(html):
    return re.findall(r'<a href="/expenses/(\d+)/edit" class="btn-edit">Edit</a>', html)


def test_profile_has_an_actions_column_with_one_edit_link_per_row(client, login, owner, add_expense):
    ids = [add_expense(owner, float(n), "Food", f"2026-03-0{n}", f"row{n}") for n in range(1, 5)]
    login(owner)
    html = client.get("/profile").get_data(as_text=True)

    assert '<th class="tx-actions">Actions</th>' in html
    # Newest date first, so the links run in reverse insertion order.
    assert edit_links(html) == [str(i) for i in reversed(ids)]


def test_each_edit_link_points_at_its_own_expense(client, login, owner, add_expense):
    expense = add_expense(owner, 5.0, "Food", "2026-03-01", "only row")
    login(owner)
    html = client.get("/profile").get_data(as_text=True)
    row_html = html.split("<tbody>")[1].split("</tbody>")[0]
    assert "only row" in row_html and f'href="/expenses/{expense}/edit"' in row_html


def test_a_user_with_no_expenses_has_no_edit_links(client, login, owner):
    login(owner)
    assert edit_links(client.get("/profile").get_data(as_text=True)) == []


def test_edit_links_follow_the_date_filter(client, login, owner, add_expense, fixed_today):
    inside = add_expense(owner, 5.0, "Food", "2026-03-10", "inside")
    outside = add_expense(owner, 6.0, "Food", "2025-01-10", "outside")
    login(owner)

    everything = edit_links(client.get("/profile").get_data(as_text=True))
    assert set(everything) == {str(inside), str(outside)}

    filtered = client.get("/profile?date_from=2026-03-01&date_to=2026-03-15").get_data(as_text=True)
    assert edit_links(filtered) == [str(inside)]
    assert "outside" not in filtered
