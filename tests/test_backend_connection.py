"""Step 05: live query helpers and the /profile route."""

import re
from datetime import datetime
from pathlib import Path

from database.db import get_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_CATEGORIES = ["Bills", "Food", "Shopping", "Health", "Transport", "Entertainment", "Other"]


# ------------------------------------------------------------------ #
# Test isolation                                                      #
# ------------------------------------------------------------------ #

def test_tests_never_use_the_real_database():
    conn = get_db()
    try:
        in_use = conn.execute("PRAGMA database_list").fetchone()["file"]
    finally:
        conn.close()
    assert in_use
    assert Path(in_use).resolve() != (PROJECT_ROOT / "spendly.db").resolve()


# ------------------------------------------------------------------ #
# get_user_by_id                                                      #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(demo_user_id):
    user = get_user_by_id(demo_user_id)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert re.fullmatch(r"[A-Z][a-z]+ \d{4}", user["member_since"])


def test_get_user_by_id_member_since_format():
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) "
            "VALUES ('Old User', 'old@example.com', 'x', '2026-01-15 10:30:00')"
        )
        conn.commit()
        user_id = cursor.lastrowid
    finally:
        conn.close()
    assert get_user_by_id(user_id)["member_since"] == "January 2026"


def test_get_user_by_id_missing():
    assert get_user_by_id(99999) is None


# ------------------------------------------------------------------ #
# get_summary_stats                                                   #
# ------------------------------------------------------------------ #

def test_summary_stats_with_expenses(demo_user_id):
    assert get_summary_stats(demo_user_id) == {
        "total_spent": 346.24,
        "transaction_count": 8,
        "top_category": "Bills",
    }


def test_summary_stats_without_expenses(make_user):
    assert get_summary_stats(make_user()) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


def test_summary_stats_tie_goes_to_first_alphabetically(make_user, add_expense):
    user_id = make_user()
    add_expense(user_id, 50.0, "Food", "2026-03-01")
    add_expense(user_id, 50.0, "Bills", "2026-03-02")
    assert get_summary_stats(user_id)["top_category"] == "Bills"


def test_summary_stats_total_is_rounded(make_user, add_expense):
    user_id = make_user()
    add_expense(user_id, 0.1, "Food", "2026-03-01")
    add_expense(user_id, 0.2, "Food", "2026-03-02")
    assert get_summary_stats(user_id)["total_spent"] == 0.3


def test_summary_stats_only_counts_own_expenses(demo_user_id, make_user, add_expense):
    other = make_user()
    add_expense(other, 1000.0, "Other", "2026-03-01")
    assert get_summary_stats(demo_user_id)["total_spent"] == 346.24


# ------------------------------------------------------------------ #
# get_recent_transactions                                             #
# ------------------------------------------------------------------ #

def test_recent_transactions_with_expenses(demo_user_id):
    items = get_recent_transactions(demo_user_id)
    assert len(items) == 8
    assert all(set(item) == {"id", "date", "description", "category", "amount"} for item in items)
    dates = [item["date"] for item in items]
    assert dates == sorted(dates, reverse=True)
    assert items[0]["description"] == "Miscellaneous"


def test_recent_transactions_respects_limit(demo_user_id):
    everything = get_recent_transactions(demo_user_id)
    assert get_recent_transactions(demo_user_id, limit=3) == everything[:3]


def test_recent_transactions_same_date_higher_id_first(make_user, add_expense):
    user_id = make_user()
    add_expense(user_id, 5.0, "Food", "2030-01-01", "first")
    add_expense(user_id, 6.0, "Food", "2030-01-01", "second")
    items = get_recent_transactions(user_id)
    assert [item["description"] for item in items] == ["second", "first"]


def test_recent_transactions_without_expenses(make_user):
    assert get_recent_transactions(make_user()) == []


def test_recent_transactions_keeps_null_description(make_user, add_expense):
    user_id = make_user()
    add_expense(user_id, 5.0, "Food", "2030-01-01", None)
    assert get_recent_transactions(user_id)[0]["description"] is None


# ------------------------------------------------------------------ #
# get_category_breakdown                                              #
# ------------------------------------------------------------------ #

def test_category_breakdown_with_expenses(demo_user_id):
    rows = get_category_breakdown(demo_user_id)
    assert [row["name"] for row in rows] == SEED_CATEGORIES
    amounts = [row["amount"] for row in rows]
    assert amounts == sorted(amounts, reverse=True)
    assert amounts == [120.0, 89.5, 45.0, 35.74, 28.0, 18.0, 10.0]
    assert all(isinstance(row["pct"], int) for row in rows)
    assert sum(row["pct"] for row in rows) == 100
    assert [row["pct"] for row in rows] == [35, 26, 13, 10, 8, 5, 3]


def test_category_breakdown_without_expenses(make_user):
    assert get_category_breakdown(make_user()) == []


def test_category_breakdown_rounding_remainder_goes_to_largest(make_user, add_expense):
    user_id = make_user()
    for category in ("Bills", "Food", "Health"):
        add_expense(user_id, 10.0, category, "2026-03-01")
    rows = get_category_breakdown(user_id)
    assert sum(row["pct"] for row in rows) == 100
    assert [row["pct"] for row in rows] == [34, 33, 33]


# ------------------------------------------------------------------ #
# GET /profile                                                        #
# ------------------------------------------------------------------ #

def _stat(html, label):
    match = re.search(
        rf'{label}</p>\s*<p class="stat-value">([^<]+)</p>', html
    )
    return match.group(1) if match else None


def test_profile_unauthenticated_redirects_to_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_with_deleted_user_clears_session_and_redirects(client, login):
    login(99999)
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_profile_for_seed_user(client, login, demo_user_id):
    login(demo_user_id)
    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert "₹" in html
    assert _stat(html, "Total spent") == "₹346.24"
    assert _stat(html, "Transactions") == "8"
    assert _stat(html, "Top category") == "Bills"

    tbody = html.split("<tbody>")[1].split("</tbody>")[0]
    descriptions = re.findall(r"<td>([^<]*)</td>\s*<td><span", tbody)
    assert len(descriptions) == 8
    assert descriptions[0] == "Miscellaneous"

    breakdown = html.split('id="category-breakdown"')[1]
    bars = re.findall(r'<progress class="bar bar-(\w+)" value="(\d+)"', breakdown)
    assert [name for name, _ in bars] == [c.lower() for c in SEED_CATEGORIES]
    assert sum(int(value) for _, value in bars) == 100


def test_profile_transactions_are_newest_first(client, login, demo_user_id):
    login(demo_user_id)
    html = client.get("/profile").get_data(as_text=True)
    tbody = html.split("<tbody>")[1].split("</tbody>")[0]
    dates = re.findall(r"<td>(\d+ \w{3} \d{4})</td>", tbody)
    parsed = [datetime.strptime(d, "%d %b %Y") for d in dates]
    assert parsed == sorted(parsed, reverse=True)


def test_profile_for_new_user_with_no_expenses(client, login, make_user):
    user_id = make_user(name="Asha Rao", email="asha@example.com")
    login(user_id)
    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Asha Rao" in html
    assert "Demo User" not in html
    assert _stat(html, "Total spent") == "₹0.00"
    assert _stat(html, "Transactions") == "0"
    assert _stat(html, "Top category") == "—"
    assert "<progress" not in html
    assert "<tr>" not in html.split("<tbody>")[1].split("</tbody>")[0]


def test_navbar_shows_real_user_name(client, login, make_user):
    login(make_user(name="Asha Rao", email="asha@example.com"))
    html = client.get("/profile").get_data(as_text=True)
    nav = html.split('<div class="nav-links">')[1].split("</div>")[0]
    assert "Asha Rao" in nav
    assert "Demo User" not in nav


def test_users_only_see_their_own_expenses(client, login, demo_user_id, make_user, add_expense):
    add_expense(demo_user_id, 77.0, "Food", "2026-11-02", "Secret demo purchase")
    login(make_user(name="Asha Rao", email="asha@example.com"))
    html = client.get("/profile").get_data(as_text=True)
    assert "Secret demo purchase" not in html
    assert "₹0.00" in html


def test_null_description_renders_blank(client, login, make_user, add_expense):
    user_id = make_user()
    add_expense(user_id, 12.0, "Food", "2026-03-01", None)
    login(user_id)
    html = client.get("/profile").get_data(as_text=True)
    assert "None" not in html
    assert "₹12.00" in html


def test_every_amount_uses_the_rupee_symbol(client, login, demo_user_id):
    login(demo_user_id)
    html = client.get("/profile").get_data(as_text=True)
    assert "£" not in html and "$" not in html
    transaction_amounts = re.findall(r'<td class="tx-amount">([^<]*)</td>', html)
    breakdown_amounts = re.findall(r'<span class="breakdown-amount">([^<]*)</span>', html)
    all_amounts = transaction_amounts + breakdown_amounts + [_stat(html, "Total spent")]
    assert len(transaction_amounts) == 8 and len(breakdown_amounts) == 7
    assert all(re.fullmatch(r"₹[\d,]+\.\d{2}", amount) for amount in all_amounts)
