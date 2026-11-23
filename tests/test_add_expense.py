"""Step 07: insert_expense() and the /expenses/add route."""

import re
import sqlite3

import pytest

from database.db import CATEGORIES, get_db
from database.queries import insert_expense

VALID = {
    "amount": "50.0",
    "category": "Food",
    "date": "2026-03-20",
    "description": "Lunch",
}


def rows_for(user_id):
    conn = get_db()
    try:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT id, user_id, amount, category, date, description "
                "FROM expenses WHERE user_id = ? ORDER BY id",
                (user_id,),
            )
        ]
    finally:
        conn.close()


def post_expense(client, **overrides):
    """POST the valid form, replacing fields. A value of None omits the field."""
    data = {**VALID, **overrides}
    data = {key: value for key, value in data.items() if value is not None}
    return client.post("/expenses/add", data=data)


def error_message(html):
    match = re.search(r'<div class="auth-error">([^<]*)</div>', html)
    return match.group(1) if match else None


# ------------------------------------------------------------------ #
# insert_expense                                                      #
# ------------------------------------------------------------------ #

def test_insert_expense_stores_the_row_and_returns_its_id(make_user):
    user_id = make_user()
    expense_id = insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")

    assert isinstance(expense_id, int)
    assert rows_for(user_id) == [
        {
            "id": expense_id,
            "user_id": user_id,
            "amount": 50.0,
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        }
    ]


def test_insert_expense_stores_none_as_null(make_user):
    user_id = make_user()
    insert_expense(user_id, 50.0, "Food", "2026-03-20", None)
    assert rows_for(user_id)[0]["description"] is None


def test_insert_expense_with_unknown_user_violates_the_foreign_key():
    with pytest.raises(sqlite3.IntegrityError):
        insert_expense(99999, 50.0, "Food", "2026-03-20", "x")


# ------------------------------------------------------------------ #
# Access control                                                      #
# ------------------------------------------------------------------ #

def test_get_form_logged_out_redirects_to_login(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_post_logged_out_redirects_and_inserts_nothing(client, make_user):
    user_id = make_user()
    response = post_expense(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert rows_for(user_id) == []


@pytest.mark.parametrize("method", ["get", "post"])
def test_session_for_a_deleted_user_is_redirected_not_a_server_error(client, login, method):
    login(99999)
    response = getattr(client, method)("/expenses/add", data=VALID if method == "post" else None)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as session:
        assert "user_id" not in session


# ------------------------------------------------------------------ #
# The form page                                                       #
# ------------------------------------------------------------------ #

def test_get_form_shows_every_field_and_seven_categories(client, login, make_user):
    login(make_user())
    response = client.get("/expenses/add")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert re.search(r'<form method="post"', html, re.I)
    select = html.split('<select id="category"')[1].split("</select>")[0]
    assert re.findall(r'<option value="([^"]*)"', select) == CATEGORIES
    assert len(re.findall(r"<option", select)) == 7
    for name in ("amount", "category", "date", "description"):
        assert f'name="{name}"' in html
    assert 'step="0.01"' in html and 'min="0.01"' in html
    assert 'maxlength="200"' in html
    assert ">Save Expense</button>" in html


def test_form_defaults_the_date_to_today(client, login, make_user, fixed_today):
    login(make_user())
    html = client.get("/expenses/add").get_data(as_text=True)
    assert f'value="{fixed_today.isoformat()}"' in html


def test_cancel_link_goes_to_the_profile_page(client, login, make_user):
    login(make_user())
    html = client.get("/expenses/add").get_data(as_text=True)
    assert 'href="/profile">Cancel</a>' in html


# ------------------------------------------------------------------ #
# Saving                                                              #
# ------------------------------------------------------------------ #

def test_valid_post_redirects_to_profile_and_saves_the_expense(client, login, make_user):
    user_id = make_user()
    login(user_id)
    response = post_expense(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    saved = rows_for(user_id)
    assert len(saved) == 1
    assert (saved[0]["amount"], saved[0]["category"], saved[0]["date"], saved[0]["description"]) == (
        50.0, "Food", "2026-03-20", "Lunch",
    )


def test_saved_expense_appears_on_the_profile_page_in_rupees(client, login, make_user):
    login(make_user())
    response = client.post("/expenses/add", data=VALID, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Lunch" in html
    assert "₹50.00" in html


def test_expense_is_saved_for_the_logged_in_user_only(client, login, make_user):
    me = make_user(email="me@example.com")
    someone_else = make_user(email="else@example.com")
    login(me)
    post_expense(client)
    assert len(rows_for(me)) == 1
    assert rows_for(someone_else) == []


def test_future_date_is_accepted(client, login, make_user, fixed_today):
    user_id = make_user()
    login(user_id)
    response = post_expense(client, date="2026-04-15")
    assert response.status_code == 302
    assert rows_for(user_id)[0]["date"] == "2026-04-15"


def test_unpadded_date_is_stored_in_iso_form(client, login, make_user):
    user_id = make_user()
    login(user_id)
    post_expense(client, date="2026-3-5")
    assert rows_for(user_id)[0]["date"] == "2026-03-05"


def test_two_decimal_amount_is_stored_exactly(client, login, make_user):
    user_id = make_user()
    login(user_id)
    post_expense(client, amount="19.99")
    assert rows_for(user_id)[0]["amount"] == 19.99


@pytest.mark.parametrize("description", [None, "", "   "])
def test_missing_or_blank_description_is_stored_as_null(client, login, make_user, description):
    user_id = make_user()
    login(user_id)
    response = post_expense(client, description=description)
    assert response.status_code == 302
    assert rows_for(user_id)[0]["description"] is None


def test_description_is_stripped(client, login, make_user):
    user_id = make_user()
    login(user_id)
    post_expense(client, description="  Lunch  ")
    assert rows_for(user_id)[0]["description"] == "Lunch"


def test_description_of_exactly_200_characters_is_accepted(client, login, make_user):
    user_id = make_user()
    login(user_id)
    response = post_expense(client, description="x" * 200)
    assert response.status_code == 302
    assert len(rows_for(user_id)[0]["description"]) == 200


# ------------------------------------------------------------------ #
# Validation                                                          #
# ------------------------------------------------------------------ #

INVALID_CASES = [
    ("missing amount", {"amount": None}, "Amount is required."),
    ("blank amount", {"amount": "  "}, "Amount is required."),
    ("zero amount", {"amount": "0"}, "greater than zero"),
    ("negative amount", {"amount": "-5"}, "greater than zero"),
    ("non-numeric amount", {"amount": "abc"}, "must be a number"),
    ("nan amount", {"amount": "nan"}, "must be a number"),
    ("infinite amount", {"amount": "inf"}, "must be a number"),
    ("three decimal places", {"amount": "10.555"}, "two decimal places"),
    ("category outside the list", {"category": "Gifts"}, "valid category"),
    ("lower-case category", {"category": "food"}, "valid category"),
    ("missing category", {"category": None}, "valid category"),
    ("missing date", {"date": None}, "Date is required."),
    ("malformed date", {"date": "not-a-date"}, "valid date"),
    ("calendar-impossible date", {"date": "2026-02-30"}, "valid date"),
    ("description over 200 characters", {"description": "x" * 201}, "200 characters"),
]


@pytest.mark.parametrize("label, overrides, message", INVALID_CASES, ids=[c[0] for c in INVALID_CASES])
def test_invalid_submission_shows_an_error_and_saves_nothing(client, login, make_user, label, overrides, message):
    user_id = make_user()
    login(user_id)
    response = post_expense(client, **overrides)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert message in (error_message(html) or "")
    assert rows_for(user_id) == []


def test_failed_submission_keeps_what_the_user_typed(client, login, make_user):
    login(make_user())
    response = post_expense(
        client, amount="10.555", category="Bills", date="2026-03-01", description="keep me"
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'value="10.555"' in html
    assert 'value="2026-03-01"' in html
    assert 'value="keep me"' in html
    assert '<option value="Bills" selected>' in html
    assert html.count(" selected>") == 1


def test_only_the_first_error_is_reported(client, login, make_user):
    login(make_user())
    response = post_expense(client, amount="0", category="Gifts", date="not-a-date")
    html = response.get_data(as_text=True)
    assert html.count('class="auth-error"') == 1
    assert "greater than zero" in html


# ------------------------------------------------------------------ #
# Links to the form                                                   #
# ------------------------------------------------------------------ #

def test_navbar_shows_add_expense_only_when_logged_in(client, login, make_user):
    guest_nav = client.get("/").get_data(as_text=True).split('<div class="nav-links">')[1].split("</div>")[0]
    assert "Add Expense" not in guest_nav

    login(make_user())
    nav = client.get("/").get_data(as_text=True).split('<div class="nav-links">')[1].split("</div>")[0]
    assert 'href="/expenses/add">Add Expense</a>' in nav


def test_profile_page_links_to_the_form(client, login, make_user):
    login(make_user())
    html = client.get("/profile").get_data(as_text=True)
    assert re.search(r'<a href="/expenses/add" class="btn-add">Add Expense</a>', html)
    heading = html.split('id="transactions"')[1].split("<table")[0]
    assert "Transaction history" in heading and "btn-add" in heading
