"""Tests for Step 09 - Delete Expense, written from .claude/specs/09-delete-expense.md.

Covers the POST-only route /expenses/<id>/delete (auth guard, ownership, 404s,
405s, redirect target), the database side effects, the delete_expense query
helper, the Delete controls rendered on /profile, and the .btn-delete CSS rule.
Every test uses the temporary database from conftest.py, never spendly.db.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

from database.db import get_db
from database.queries import delete_expense as delete_expense_query

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STYLE_CSS = PROJECT_ROOT / "static" / "css" / "style.css"
PROFILE_CSS = PROJECT_ROOT / "static" / "css" / "profile.css"

SEED_COUNT = 8
SEED_TOTAL = "₹346.24"  # sum of the eight seed expenses
SEED_TOTAL_WITHOUT_ELECTRICITY = "₹226.24"  # after removing the 120.00 bill


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def fetch_expense(expense_id):
    """Return the expense row as a dict, or None if it does not exist."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def expense_ids(user_id=None):
    """Sorted ids of all expenses, or only those of one user."""
    conn = get_db()
    try:
        if user_id is None:
            rows = conn.execute("SELECT id FROM expenses ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT id FROM expenses WHERE user_id = ? ORDER BY id", (user_id,)
            ).fetchall()
    finally:
        conn.close()
    return [r["id"] for r in rows]


def all_expense_rows():
    """Every expense row as a list of dicts, ordered by id."""
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM expenses ORDER BY id").fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def expense_id_by_description(description):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM expenses WHERE description = ?", (description,)
        ).fetchone()
    finally:
        conn.close()
    return row["id"]


def delete_url(expense_id):
    return f"/expenses/{expense_id}/delete"


def redirect_target(response):
    """Path and query of a redirect response's Location header."""
    parsed = urlparse(response.headers["Location"])
    return parsed.path, parsed.query


def table_rows(html):
    """Inner HTML of every body row (rows without header cells) of the page."""
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", html, re.S)
    return [r for r in rows if "<th" not in r]


def delete_forms(html):
    """Each delete form on the page as (opening_tag, full_form_html)."""
    forms = []
    for match in re.finditer(r"<form\b[^>]*>.*?</form>", html, re.S):
        block = match.group(0)
        opening = re.match(r"<form\b[^>]*>", block).group(0)
        if re.search(r'action="[^"]*/expenses/\d+/delete[^"]*"', opening):
            forms.append((opening, block))
    return forms


def attr(tag, name):
    match = re.search(rf'\b{name}\s*=\s*"([^"]*)"', tag)
    return match.group(1) if match else None


def delete_ids_on_page(html):
    return [
        int(re.search(r"/expenses/(\d+)/delete", attr(opening, "action")).group(1))
        for opening, _ in delete_forms(html)
    ]


def stat_value(html, label):
    """Text of the summary stat card with the given label."""
    match = re.search(
        rf'{re.escape(label)}</p>\s*<p class="stat-value">([^<]*)</p>', html
    )
    assert match, f"stat card {label!r} not found"
    return match.group(1).strip()


def get_profile(client, query=""):
    response = client.get("/profile" + query)
    assert response.status_code == 200
    return response.get_data(as_text=True)


@pytest.fixture
def seed_ids(demo_user_id):
    """Ids of the eight seeded demo expenses."""
    return expense_ids(demo_user_id)


@pytest.fixture
def owner_with_expenses(make_user, add_expense):
    """A fresh user owning three expenses with unique descriptions."""
    user_id = make_user("Dora Owner", "dora@example.com")
    ids = [
        add_expense(user_id, 10.00, "Food", "2020-01-05", "Alpha item"),
        add_expense(user_id, 20.00, "Bills", "2020-01-20", "Beta item"),
        add_expense(user_id, 30.00, "Other", "2020-03-10", "Gamma item"),
    ]
    return user_id, ids


# ------------------------------------------------------------------ #
# Query helper: delete_expense(expense_id, user_id)                   #
# ------------------------------------------------------------------ #

def test_query_delete_expense_owner_returns_one_and_removes_row(demo_user_id, seed_ids):
    """Unit table row 1: valid id and correct user returns 1 and removes the row."""
    target = seed_ids[0]
    assert delete_expense_query(target, demo_user_id) == 1
    assert fetch_expense(target) is None


def test_query_delete_expense_removes_only_the_matching_row(demo_user_id, seed_ids):
    """Files to change: the DELETE removes only the single matching row."""
    delete_expense_query(seed_ids[0], demo_user_id)
    assert expense_ids(demo_user_id) == seed_ids[1:]


def test_query_delete_expense_wrong_user_returns_zero_and_keeps_row(
    demo_user_id, make_user, seed_ids
):
    """Unit table row 2: wrong user returns 0, the row remains, no error is raised."""
    other_id = make_user()
    target = seed_ids[0]
    before = fetch_expense(target)
    assert delete_expense_query(target, other_id) == 0
    assert fetch_expense(target) == before
    assert len(expense_ids()) == SEED_COUNT


def test_query_delete_expense_nonexistent_id_returns_zero_without_error(
    demo_user_id,
):
    """Unit table row 3: non-existent id returns 0 and leaves the database unchanged."""
    before = all_expense_rows()
    assert delete_expense_query(999999, demo_user_id) == 0
    assert all_expense_rows() == before


def test_query_delete_expense_twice_second_call_returns_zero(demo_user_id, seed_ids):
    """Returns the number of rows deleted: a repeat call deletes nothing."""
    assert delete_expense_query(seed_ids[0], demo_user_id) == 1
    assert delete_expense_query(seed_ids[0], demo_user_id) == 0


def test_query_delete_expense_does_not_touch_users_table(demo_user_id, seed_ids):
    """Database changes: no other table is touched by a delete."""
    conn = get_db()
    try:
        users_before = [dict(r) for r in conn.execute("SELECT * FROM users ORDER BY id")]
    finally:
        conn.close()
    delete_expense_query(seed_ids[0], demo_user_id)
    conn = get_db()
    try:
        users_after = [dict(r) for r in conn.execute("SELECT * FROM users ORDER BY id")]
    finally:
        conn.close()
    assert users_after == users_before


# ------------------------------------------------------------------ #
# Route: auth guard                                                   #
# ------------------------------------------------------------------ #

def test_post_logged_out_redirects_to_login_and_deletes_nothing(client, seed_ids):
    """Routes + DoD 1: logged-out POST redirects to /login (302), row remains."""
    before = all_expense_rows()
    response = client.post(delete_url(seed_ids[0]))
    assert response.status_code == 302
    assert redirect_target(response)[0] == "/login"
    assert all_expense_rows() == before


def test_post_logged_out_nonexistent_id_redirects_the_same_way(client):
    """Rules: login check runs first, so a missing id gives the same 302 to /login."""
    response = client.post(delete_url(999999))
    assert response.status_code == 302
    assert redirect_target(response)[0] == "/login"


def test_post_logged_out_response_is_identical_for_existing_and_missing_ids(
    client, seed_ids
):
    """Rules: a logged-out request never reveals whether an expense exists."""
    existing = client.post(delete_url(seed_ids[0]))
    missing = client.post(delete_url(999999))
    assert existing.status_code == missing.status_code == 302
    assert existing.headers["Location"] == missing.headers["Location"]


# ------------------------------------------------------------------ #
# Route: successful delete                                            #
# ------------------------------------------------------------------ #

def test_post_own_expense_redirects_to_profile_and_removes_row(
    client, login, demo_user_id, seed_ids
):
    """Routes + DoD 5: own expense, 302 to /profile and the row is gone."""
    login(demo_user_id)
    target = seed_ids[2]
    response = client.post(delete_url(target))
    assert response.status_code == 302
    assert redirect_target(response)[0] == "/profile"
    assert fetch_expense(target) is None


def test_post_own_expense_removes_only_that_row(
    client, login, demo_user_id, make_user, add_expense, seed_ids
):
    """Database changes: only the one row is removed; other rows and users' rows stay."""
    other_id = make_user()
    other_expense = add_expense(other_id, 99.00, "Food", "2026-01-01", "Other user's")
    login(demo_user_id)
    before = {row["id"]: row for row in all_expense_rows()}
    target = seed_ids[3]

    client.post(delete_url(target))

    after = {row["id"]: row for row in all_expense_rows()}
    expected = {k: v for k, v in before.items() if k != target}
    assert after == expected
    assert other_expense in after


def test_redirect_after_delete_is_the_unfiltered_profile(
    client, login, demo_user_id, seed_ids
):
    """Rules: redirect lands on the unfiltered /profile, even from a filtered view."""
    login(demo_user_id)
    response = client.post(
        delete_url(seed_ids[0]) + "?date_from=2026-01-01&date_to=2026-01-31"
    )
    assert response.status_code == 302
    path, query = redirect_target(response)
    assert path == "/profile"
    assert query == ""


def test_deleted_expense_no_longer_listed_after_redirect(
    client, login, owner_with_expenses
):
    """DoD 6: after deleting, /profile no longer lists the deleted expense."""
    user_id, ids = owner_with_expenses
    login(user_id)
    assert "Beta item" in get_profile(client)

    response = client.post(delete_url(ids[1]), follow_redirects=True)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Beta item" not in html
    assert "Alpha item" in html
    assert "Gamma item" in html
    assert ids[1] not in delete_ids_on_page(html)


def test_profile_totals_change_after_delete(client, login, demo_user_id):
    """DoD 6: summary totals on /profile reflect the deletion."""
    login(demo_user_id)
    before = get_profile(client)
    assert stat_value(before, "Total spent") == SEED_TOTAL
    assert stat_value(before, "Transactions") == str(SEED_COUNT)

    client.post(delete_url(expense_id_by_description("Electricity bill")))

    after = get_profile(client)
    assert stat_value(after, "Total spent") == SEED_TOTAL_WITHOUT_ELECTRICITY
    assert stat_value(after, "Transactions") == str(SEED_COUNT - 1)
    assert "Electricity bill" not in after


# ------------------------------------------------------------------ #
# Route: 404 cases                                                    #
# ------------------------------------------------------------------ #

def test_post_other_users_expense_returns_404_and_row_unchanged(
    client, login, make_user, seed_ids
):
    """Routes + DoD 3: another user's expense gives 404 and the row is unchanged."""
    intruder = make_user()
    login(intruder)
    target = seed_ids[0]
    before = fetch_expense(target)
    response = client.post(delete_url(target))
    assert response.status_code == 404
    assert fetch_expense(target) == before
    assert len(expense_ids()) == SEED_COUNT


def test_post_other_users_expense_looks_the_same_as_missing_expense(
    client, login, make_user, seed_ids
):
    """Routes: the response does not reveal whether the expense exists."""
    login(make_user())
    other = client.post(delete_url(seed_ids[0]))
    missing = client.post(delete_url(999999))
    assert other.status_code == missing.status_code == 404
    assert other.get_data() == missing.get_data()


def test_post_nonexistent_id_returns_404(client, login, demo_user_id):
    """Routes + DoD 2: a non-existent expense id returns 404."""
    login(demo_user_id)
    assert client.post(delete_url(999999)).status_code == 404
    assert len(expense_ids()) == SEED_COUNT


def test_post_with_session_for_nonexistent_user_returns_404(client, login, seed_ids):
    """Rules: a session whose user does not exist gives 404, not a server error."""
    login(987654)
    response = client.post(delete_url(seed_ids[0]))
    assert response.status_code == 404
    assert len(expense_ids()) == SEED_COUNT


def test_post_with_session_for_removed_user_returns_404(
    client, login, make_user, seed_ids
):
    """Rules: a user deleted after logging in gets 404 (not 500) and nothing is deleted."""
    user_id = make_user("Gone Soon", "gone@example.com")
    login(user_id)
    conn = get_db()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
    response = client.post(delete_url(seed_ids[0]))
    assert response.status_code == 404
    assert len(expense_ids()) == SEED_COUNT


def test_deleting_same_expense_twice_second_attempt_is_404(
    client, login, demo_user_id, seed_ids
):
    """Rules: once removed, a repeat POST for the same id is a 404."""
    login(demo_user_id)
    first = client.post(delete_url(seed_ids[0]))
    second = client.post(delete_url(seed_ids[0]))
    assert first.status_code == 302
    assert second.status_code == 404
    assert len(expense_ids()) == SEED_COUNT - 1


@pytest.mark.parametrize("bad_id", ["abc", "-1", "0", "1.5", "99999999999999999999"])
def test_post_odd_ids_return_404_and_delete_nothing(client, login, demo_user_id, bad_id):
    """Routes: odd ids (non-numeric, negative, zero, huge) are a 404, never a 500."""
    login(demo_user_id)
    response = client.post(f"/expenses/{bad_id}/delete")
    assert response.status_code == 404
    assert len(expense_ids()) == SEED_COUNT


# ------------------------------------------------------------------ #
# Route: method restrictions                                          #
# ------------------------------------------------------------------ #

def test_get_logged_in_returns_405_and_deletes_nothing(
    client, login, demo_user_id, seed_ids
):
    """Routes + DoD 4: GET returns 405 for a logged-in user and never deletes."""
    login(demo_user_id)
    response = client.get(delete_url(seed_ids[0]))
    assert response.status_code == 405
    assert expense_ids() == sorted(seed_ids)


def test_get_logged_out_returns_405_and_deletes_nothing(client, seed_ids):
    """Routes + DoD 4: GET returns 405 for a logged-out user and never deletes."""
    response = client.get(delete_url(seed_ids[0]))
    assert response.status_code == 405
    assert expense_ids() == sorted(seed_ids)


def test_get_nonexistent_id_still_returns_405(client, login, demo_user_id):
    """Rules: the route accepts only POST, whether or not the expense exists."""
    login(demo_user_id)
    assert client.get(delete_url(999999)).status_code == 405


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("logged_in", [True, False])
def test_other_methods_are_not_allowed(
    client, login, demo_user_id, seed_ids, method, logged_in
):
    """Rules: methods other than POST (PUT, PATCH, DELETE) return 405 and delete nothing."""
    if logged_in:
        login(demo_user_id)
    response = client.open(delete_url(seed_ids[0]), method=method)
    assert response.status_code == 405
    assert expense_ids() == sorted(seed_ids)


# ------------------------------------------------------------------ #
# Profile page: Edit and Delete controls                              #
# ------------------------------------------------------------------ #

def test_profile_every_row_has_edit_link_and_delete_button(
    client, login, demo_user_id, seed_ids
):
    """Templates + DoD 8: each transaction row shows both Edit and Delete."""
    login(demo_user_id)
    rows = table_rows(get_profile(client))
    assert len(rows) == SEED_COUNT
    for row in rows:
        assert re.search(r'<a\b[^>]*href="/expenses/\d+/edit"[^>]*>\s*Edit\s*</a>', row)
        assert re.search(
            r'<button\b[^>]*>\s*Delete\s*</button>', row
        ), "row has no Delete button"


def test_profile_delete_forms_cover_every_expense_exactly_once(
    client, login, demo_user_id, seed_ids
):
    """Templates: one delete form per transaction, pointing at /expenses/<id>/delete."""
    login(demo_user_id)
    ids_on_page = delete_ids_on_page(get_profile(client))
    assert sorted(ids_on_page) == sorted(seed_ids)


def test_profile_delete_form_uses_post_method(client, login, demo_user_id):
    """Templates: the delete form has method="POST"."""
    login(demo_user_id)
    forms = delete_forms(get_profile(client))
    assert len(forms) == SEED_COUNT
    for opening, _ in forms:
        assert attr(opening, "method").lower() == "post"


def test_profile_delete_form_action_is_the_delete_url(client, login, demo_user_id):
    """Templates: the form action resolves to exactly /expenses/<id>/delete."""
    login(demo_user_id)
    for opening, _ in delete_forms(get_profile(client)):
        assert re.fullmatch(r"/expenses/\d+/delete", attr(opening, "action"))


def test_profile_delete_form_has_confirm_in_onsubmit(client, login, demo_user_id):
    """Templates: onsubmit returns the browser confirm() result, so Cancel blocks submit."""
    login(demo_user_id)
    for opening, _ in delete_forms(get_profile(client)):
        onsubmit = attr(opening, "onsubmit")
        assert onsubmit is not None
        assert onsubmit.strip().startswith("return confirm(")
        assert onsubmit.strip().endswith(")")


def test_profile_delete_form_has_display_inline_style(client, login, demo_user_id):
    """Templates: the form carries style="display:inline"."""
    login(demo_user_id)
    for opening, _ in delete_forms(get_profile(client)):
        assert attr(opening, "style").replace(" ", "") == "display:inline"


def test_profile_delete_button_is_submit_with_btn_delete_class(
    client, login, demo_user_id
):
    """Templates: the control is <button type="submit" class="btn-delete">Delete</button>."""
    login(demo_user_id)
    for _, block in delete_forms(get_profile(client)):
        match = re.search(r"<button\b[^>]*>\s*Delete\s*</button>", block)
        assert match, "no Delete button inside the form"
        button = match.group(0)
        assert attr(button, "type") == "submit"
        assert "btn-delete" in attr(button, "class").split()


def test_profile_only_inline_style_is_display_inline_on_delete_forms(
    client, login, demo_user_id
):
    """Rules + DoD 9: the only inline style on the page is display:inline on delete forms."""
    login(demo_user_id)
    html = get_profile(client)
    styles = re.findall(r'\bstyle\s*=\s*"([^"]*)"', html)
    assert len(styles) == SEED_COUNT
    assert all(s.replace(" ", "") == "display:inline" for s in styles)
    # No single-quoted or unquoted inline styles either.
    assert len(re.findall(r"\bstyle\s*=", html)) == SEED_COUNT


def test_profile_has_no_other_inline_scripts_than_onsubmit(client, login, demo_user_id):
    """Rules: the onsubmit confirm() is the only inline script permitted."""
    login(demo_user_id)
    html = get_profile(client)
    handlers = re.findall(r"\son[a-z]+\s*=", html)
    assert len(handlers) == SEED_COUNT
    assert all(h.strip() == "onsubmit=" for h in handlers)


def test_edit_and_delete_in_each_row_refer_to_same_expense(
    client, login, owner_with_expenses
):
    """Templates: Edit and Delete controls in one row point at the same expense id."""
    user_id, ids = owner_with_expenses
    login(user_id)
    rows = table_rows(get_profile(client))
    assert len(rows) == len(ids)
    seen = []
    for row in rows:
        edit_id = int(re.search(r'href="/expenses/(\d+)/edit"', row).group(1))
        delete_id = int(re.search(r'action="/expenses/(\d+)/delete"', row).group(1))
        assert edit_id == delete_id
        seen.append(edit_id)
    assert sorted(seen) == sorted(ids)


def test_profile_row_delete_form_belongs_to_that_rows_expense(
    client, login, owner_with_expenses
):
    """Templates: each row's delete form targets the expense shown in that row."""
    user_id, ids = owner_with_expenses
    login(user_id)
    by_description = {"Alpha item": ids[0], "Beta item": ids[1], "Gamma item": ids[2]}
    for row in table_rows(get_profile(client)):
        description = next(d for d in by_description if d in row)
        assert f'/expenses/{by_description[description]}/delete' in row


def test_profile_still_uses_rupee_symbol(client, login, demo_user_id):
    """Rules: currency is always shown as the rupee sign, never a pound sign."""
    login(demo_user_id)
    html = get_profile(client)
    assert "₹" in html
    assert "£" not in html


# ------------------------------------------------------------------ #
# Date filter and empty states                                        #
# ------------------------------------------------------------------ #

def test_date_filter_still_works_with_delete_buttons(
    client, login, fixed_today, owner_with_expenses
):
    """DoD 11: date_from/date_to still filter rows, and filtered rows keep delete forms."""
    user_id, ids = owner_with_expenses
    login(user_id)
    html = get_profile(client, "?date_from=2020-01-01&date_to=2020-01-31")
    assert "Alpha item" in html
    assert "Beta item" in html
    assert "Gamma item" not in html
    assert sorted(delete_ids_on_page(html)) == sorted(ids[:2])
    assert len(table_rows(html)) == 2


def test_delete_from_filtered_view_works_and_lands_on_unfiltered_profile(
    client, login, fixed_today, owner_with_expenses
):
    """Rules: deleting from a filtered view works and the user loses the filter."""
    user_id, ids = owner_with_expenses
    login(user_id)
    filtered = get_profile(client, "?date_from=2020-01-01&date_to=2020-01-31")
    action = attr(delete_forms(filtered)[0][0], "action")

    response = client.post(action)

    assert response.status_code == 302
    assert redirect_target(response) == ("/profile", "")
    assert len(expense_ids(user_id)) == 2
    unfiltered = get_profile(client)
    assert "Gamma item" in unfiltered  # outside the old filter, shown again


def test_user_with_no_expenses_sees_no_delete_forms(client, login, make_user):
    """Templates: a user with no expenses has no delete forms on the profile page."""
    login(make_user("Empty User", "empty@example.com"))
    html = get_profile(client)
    assert delete_forms(html) == []
    assert "/delete" not in html
    assert table_rows(html) == []


def test_deleting_last_expense_leaves_a_normal_empty_profile(
    client, login, make_user, add_expense
):
    """Edge case: deleting the only remaining expense gives a normal empty profile page."""
    user_id = make_user("Solo User", "solo@example.com")
    only = add_expense(user_id, 12.00, "Food", "2026-02-02", "Only one")
    login(user_id)

    response = client.post(delete_url(only), follow_redirects=True)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert expense_ids(user_id) == []
    assert "Only one" not in html
    assert delete_forms(html) == []
    assert table_rows(html) == []
    assert stat_value(html, "Transactions") == "0"


def test_deleting_one_users_expense_does_not_change_other_users_profile(
    client, login, demo_user_id, owner_with_expenses
):
    """Database changes: another user's data is unaffected by a delete."""
    user_id, ids = owner_with_expenses
    login(demo_user_id)
    client.post(delete_url(expense_id_by_description("Pharmacy")))
    assert expense_ids(user_id) == sorted(ids)


# ------------------------------------------------------------------ #
# CSS: .btn-delete                                                    #
# ------------------------------------------------------------------ #

def btn_delete_rules(css):
    """Every CSS rule block whose selector mentions .btn-delete."""
    return re.findall(r"[^{}]*\.btn-delete[^{}]*\{[^}]*\}", css)


def test_btn_delete_rule_exists_in_global_stylesheet():
    """Files to change: .btn-delete lives in static/css/style.css."""
    assert btn_delete_rules(STYLE_CSS.read_text(encoding="utf-8"))


def test_btn_delete_is_not_defined_in_profile_css():
    """Files to change: .btn-delete is global, so it is not in profile.css."""
    assert ".btn-delete" not in PROFILE_CSS.read_text(encoding="utf-8")


def test_btn_delete_uses_danger_variable():
    """Files to change: text/border colour comes from var(--danger)."""
    rules = " ".join(btn_delete_rules(STYLE_CSS.read_text(encoding="utf-8")))
    assert "var(--danger)" in rules


def test_btn_delete_hover_uses_danger_light_variable():
    """Files to change: hover background comes from var(--danger-light)."""
    rules = " ".join(btn_delete_rules(STYLE_CSS.read_text(encoding="utf-8")))
    assert "var(--danger-light)" in rules


def test_btn_delete_contains_no_hex_colours():
    """Rules + DoD 10: the .btn-delete rule contains no hex colour values."""
    rules = btn_delete_rules(STYLE_CSS.read_text(encoding="utf-8"))
    assert rules
    for rule in rules:
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", rule), rule


def test_danger_variables_are_declared_in_root_not_redefined_for_delete():
    """Files to change: --danger and --danger-light already exist in :root."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{[^}]*\}", css)
    assert root
    assert re.search(r"--danger\s*:", root.group(0))
    assert re.search(r"--danger-light\s*:", root.group(0))


# ------------------------------------------------------------------ #
# Test isolation                                                      #
# ------------------------------------------------------------------ #

def test_tests_use_a_temporary_database_not_spendly_db(database):
    """DoD 12: the suite runs against a temp database, never the real spendly.db."""
    import os

    assert os.environ["SPENDLY_DB_PATH"] == str(database)
    assert Path(database).resolve() != (PROJECT_ROOT / "spendly.db").resolve()
