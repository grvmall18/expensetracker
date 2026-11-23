"""Step 09: delete_expense() and the POST-only /expenses/<id>/delete route."""

import re
import sys
from pathlib import Path

import pytest

from database.db import get_db
from database.queries import delete_expense

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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


def exists(expense_id):
    conn = get_db()
    try:
        return conn.execute("SELECT 1 FROM expenses WHERE id = ?", (expense_id,)).fetchone() is not None
    finally:
        conn.close()


def row(expense_id):
    conn = get_db()
    try:
        found = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        return dict(found) if found else None
    finally:
        conn.close()


def total_rows():
    conn = get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# delete_expense                                                      #
# ------------------------------------------------------------------ #

def test_delete_expense_removes_the_row_and_reports_one(owner, expense_id):
    assert delete_expense(expense_id, owner) == 1
    assert not exists(expense_id)


def test_delete_expense_for_the_wrong_user_deletes_nothing(stranger, expense_id):
    before = row(expense_id)
    assert delete_expense(expense_id, stranger) == 0
    assert row(expense_id) == before


def test_delete_expense_for_a_missing_expense_reports_zero(owner, expense_id):
    before = total_rows()
    assert delete_expense(99999, owner) == 0
    assert total_rows() == before


def test_delete_expense_removes_only_the_named_row(owner, expense_id, add_expense):
    keep = add_expense(owner, 7.0, "Other", "2026-03-02", "keep me")
    delete_expense(expense_id, owner)
    assert exists(keep) and not exists(expense_id)


# ------------------------------------------------------------------ #
# Access control                                                      #
# ------------------------------------------------------------------ #

def test_post_logged_out_redirects_and_deletes_nothing(client, expense_id):
    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert exists(expense_id)


def test_logged_out_request_for_a_missing_expense_still_redirects(client):
    """The login check comes first, so a logged-out visitor learns nothing."""
    response = client.post("/expenses/99999/delete")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_another_users_expense_is_a_404_and_stays(client, login, stranger, expense_id):
    login(stranger)
    before = row(expense_id)
    assert client.post(f"/expenses/{expense_id}/delete").status_code == 404
    assert row(expense_id) == before


def test_a_missing_expense_is_a_404(client, login, owner):
    login(owner)
    assert client.post("/expenses/99999/delete").status_code == 404


@pytest.mark.parametrize("path", ["/expenses/abc/delete", "/expenses/-1/delete", "/expenses/0/delete"])
def test_unusable_ids_are_a_404(client, login, owner, path):
    login(owner)
    assert client.post(path).status_code == 404


@pytest.mark.parametrize("big_id", ["9" * 20, str(2**63), "9" * 40])
def test_an_id_too_large_for_sqlite_is_a_404_not_a_server_error(client, login, owner, big_id):
    """SQLite integers are 8 bytes. A larger id cannot match any row, so it is a plain 404."""
    login(owner)
    assert client.post(f"/expenses/{big_id}/delete").status_code == 404


def test_the_largest_id_sqlite_can_hold_is_a_normal_404(client, login, owner):
    login(owner)
    assert client.post(f"/expenses/{2**63 - 1}/delete").status_code == 404


def test_delete_expense_treats_an_oversized_id_as_not_found(owner, expense_id):
    before = total_rows()
    assert delete_expense(2**63, owner) == 0
    assert total_rows() == before


def test_a_session_for_a_deleted_user_gets_404_not_a_server_error(client, login, expense_id):
    login(99999)
    assert client.post(f"/expenses/{expense_id}/delete").status_code == 404
    assert exists(expense_id)


def test_zero_rows_deleted_is_a_404(client, login, owner, expense_id, monkeypatch):
    """If the row vanishes between the lookup and the delete, the answer is 404."""
    monkeypatch.setattr(sys.modules["app"], "remove_expense", lambda *args, **kwargs: 0)
    login(owner)
    assert client.post(f"/expenses/{expense_id}/delete").status_code == 404


# ------------------------------------------------------------------ #
# POST only                                                           #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("logged_in", [False, True], ids=["logged out", "logged in"])
def test_get_is_405(client, login, owner, expense_id, logged_in):
    if logged_in:
        login(owner)
    assert client.get(f"/expenses/{expense_id}/delete").status_code == 405


def test_a_get_never_deletes_even_for_the_owner(client, login, owner, expense_id):
    login(owner)
    client.get(f"/expenses/{expense_id}/delete")
    assert exists(expense_id)


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_other_methods_are_405_and_delete_nothing(client, login, owner, expense_id, method):
    login(owner)
    assert getattr(client, method)(f"/expenses/{expense_id}/delete").status_code == 405
    assert exists(expense_id)


# ------------------------------------------------------------------ #
# Deleting                                                            #
# ------------------------------------------------------------------ #

def test_post_own_expense_redirects_to_profile_and_removes_it(client, login, owner, expense_id):
    login(owner)
    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    assert not exists(expense_id)


def test_only_the_chosen_expense_goes(client, login, owner, stranger, expense_id, add_expense):
    own_other = add_expense(owner, 7.0, "Other", "2026-03-02", "keep me")
    their = add_expense(stranger, 9.0, "Food", "2026-03-03", "not yours")
    login(owner)
    client.post(f"/expenses/{expense_id}/delete")
    assert exists(own_other) and exists(their) and not exists(expense_id)


def test_a_second_delete_of_the_same_expense_is_a_404(client, login, owner, expense_id):
    login(owner)
    assert client.post(f"/expenses/{expense_id}/delete").status_code == 302
    assert client.post(f"/expenses/{expense_id}/delete").status_code == 404


def test_deleted_expense_disappears_from_the_profile_and_the_totals_change(client, login, owner, expense_id, add_expense):
    add_expense(owner, 10.0, "Bills", "2026-03-01", "stays")
    login(owner)
    before = client.get("/profile").get_data(as_text=True)
    assert "Lunch" in before and "₹60.00" in before

    html = client.post(f"/expenses/{expense_id}/delete", follow_redirects=True).get_data(as_text=True)
    assert "Lunch" not in html
    assert "stays" in html
    assert "₹10.00" in html and "₹60.00" not in html


def test_deleting_the_last_expense_leaves_an_empty_page_not_an_error(client, login, owner, expense_id):
    login(owner)
    response = client.post(f"/expenses/{expense_id}/delete", follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "₹0.00" in html and "<progress" not in html


# ------------------------------------------------------------------ #
# The Delete button on the profile page                               #
# ------------------------------------------------------------------ #

def delete_forms(html):
    return re.findall(r"<form [^>]*/expenses/(\d+)/delete[^>]*>", html, re.S)


def test_every_row_has_a_delete_form_with_a_confirmation(client, login, owner, add_expense):
    ids = [add_expense(owner, float(n), "Food", f"2026-03-0{n}", f"row{n}") for n in range(1, 5)]
    login(owner)
    html = client.get("/profile").get_data(as_text=True)

    assert delete_forms(html) == [str(i) for i in reversed(ids)]
    for form in re.findall(r"<form [^>]*/delete[^>]*>", html, re.S):
        assert 'method="post"' in form
        assert "onsubmit=\"return confirm('Delete this expense?')\"" in form
        assert 'style="display:inline"' in form
    assert html.count('<button type="submit" class="btn-delete">Delete</button>') == 4


def test_every_row_shows_both_edit_and_delete_for_the_same_expense(client, login, owner, add_expense):
    add_expense(owner, 5.0, "Food", "2026-03-01", "a")
    add_expense(owner, 6.0, "Food", "2026-03-02", "b")
    login(owner)
    html = client.get("/profile").get_data(as_text=True)
    edit_ids = re.findall(r'href="/expenses/(\d+)/edit" class="btn-edit"', html)
    assert edit_ids == delete_forms(html) and len(edit_ids) == 2


def test_display_inline_is_the_only_inline_style_on_the_page(client, login, owner, add_expense):
    add_expense(owner, 5.0, "Food", "2026-03-01", "a")
    login(owner)
    html = client.get("/profile").get_data(as_text=True)
    assert re.findall(r'style="([^"]*)"', html) == ["display:inline"]


def test_a_user_with_no_expenses_has_no_delete_forms(client, login, owner):
    login(owner)
    assert delete_forms(client.get("/profile").get_data(as_text=True)) == []


def test_delete_forms_follow_the_date_filter(client, login, owner, add_expense, fixed_today):
    inside = add_expense(owner, 5.0, "Food", "2026-03-10", "inside")
    outside = add_expense(owner, 6.0, "Food", "2025-01-10", "outside")
    login(owner)
    assert set(delete_forms(client.get("/profile").get_data(as_text=True))) == {str(inside), str(outside)}
    filtered = client.get("/profile?date_from=2026-03-01&date_to=2026-03-15").get_data(as_text=True)
    assert delete_forms(filtered) == [str(inside)]


# ------------------------------------------------------------------ #
# The .btn-delete style                                               #
# ------------------------------------------------------------------ #

def test_btn_delete_uses_the_danger_variables_and_no_hex():
    css = (PROJECT_ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")
    rules = re.findall(r"\.btn-delete(?::hover)?\s*\{([^}]*)\}", css)
    assert len(rules) == 2
    joined = " ".join(rules)
    assert "var(--danger)" in joined and "var(--danger-light)" in joined
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", joined)
