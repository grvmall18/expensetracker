import calendar
import math
import re
import sqlite3
from datetime import date, datetime

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import (
    CATEGORIES,
    create_user,
    get_db,
    get_user_by_email,
    init_db,
    seed_db,
)
from database.queries import (
    get_category_breakdown,
    get_expense_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
    insert_expense,
    update_expense,
)

# The delete route below is a view function named delete_expense (the profile
# template links to it by that name), so the query helper of the same name is
# imported under an alias to keep the two apart.
from database.queries import delete_expense as remove_expense

app = Flask(__name__)
# Development only. Replace with a secret from the environment before deployment.
app.secret_key = "spendly-dev-only-change-me"

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+$")

MAX_DESCRIPTION_LENGTH = 200

# Checked when a login email is unknown, so the response time does not reveal
# whether an account exists.
DUMMY_HASH = generate_password_hash("spendly-dummy-password")

# Make sure the database exists and has demo data before any route is served.
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Display helpers                                                     #
# ------------------------------------------------------------------ #

def get_initials(name):
    """First letter of the first and last words of the name, upper case."""
    words = name.split()
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][0].upper()
    return (words[0][0] + words[-1][0]).upper()


def get_today():
    """The server's local date. The single source of "today" for the filter."""
    return date.today()


def shift_months_back(day, months):
    """The same day of the month, `months` months earlier.

    If that day does not exist in the earlier month (for example 31 May minus
    three months), the last day of that month is used.
    """
    month_index = day.year * 12 + (day.month - 1) - months
    year, month = divmod(month_index, 12)
    month += 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def get_presets(today):
    """The four quick-select ranges. Every range ends today, inclusive."""
    return [
        {
            "key": "this_month",
            "label": "This Month",
            "date_from": today.replace(day=1).isoformat(),
            "date_to": today.isoformat(),
        },
        {
            "key": "last_3_months",
            "label": "Last 3 Months",
            "date_from": shift_months_back(today, 3).isoformat(),
            "date_to": today.isoformat(),
        },
        {
            "key": "last_6_months",
            "label": "Last 6 Months",
            "date_from": shift_months_back(today, 6).isoformat(),
            "date_to": today.isoformat(),
        },
        # No parameters at all: the URL is a clean /profile.
        {"key": "all_time", "label": "All Time", "date_from": None, "date_to": None},
    ]


def parse_iso_date(value):
    """Parse a YYYY-MM-DD string into a date, or return None if it is not valid."""
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def validate_expense_form(form):
    """Check the add-expense form. Returns (clean_values, None) or (None, message).

    Checks run in this order and the first failure stops them: amount,
    category, date, description.
    """
    raw_amount = form.get("amount", "").strip()
    category = form.get("category", "")
    raw_date = form.get("date", "").strip()
    description = form.get("description", "").strip()

    if not raw_amount:
        return None, "Amount is required."
    try:
        amount = float(raw_amount)
    except ValueError:
        return None, "Amount must be a number."
    if not math.isfinite(amount):
        return None, "Amount must be a number."
    if amount <= 0:
        return None, "Amount must be greater than zero."
    if round(amount, 2) != amount:
        return None, "Amount can have at most two decimal places."

    if category not in CATEGORIES:
        return None, "Please choose a valid category."

    if not raw_date:
        return None, "Date is required."
    parsed_date = parse_iso_date(raw_date)
    if parsed_date is None:
        return None, "Please enter a valid date."

    if len(description) > MAX_DESCRIPTION_LENGTH:
        return None, f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer."

    return {
        "amount": round(amount, 2),
        "category": category,
        "date": parsed_date.isoformat(),
        "description": description or None,
    }, None


def get_active_filter(date_from, date_to, presets):
    """Which control to highlight: a preset key, "custom", or "all_time".

    A preset whose range exactly equals the applied range wins over "custom".
    """
    if date_from is None:
        return "all_time"
    for preset in presets:
        if (
            preset["date_from"] == date_from.isoformat()
            and preset["date_to"] == date_to.isoformat()
        ):
            return preset["key"]
    return "custom"


@app.template_filter("inr")
def inr(value):
    """Format a number as rupees: ₹1,234.50."""
    return f"₹{value:,.2f}"


@app.template_filter("short_date")
def short_date(value):
    """Format an ISO date as '14 Mar 2026'."""
    d = date.fromisoformat(value)
    return f"{d.day} {d:%b %Y}"


@app.context_processor
def inject_nav_user():
    """Give every template the signed-in user's name for the navbar."""
    user_id = session.get("user_id")
    if user_id:
        user = get_user_by_id(user_id)
        if user is not None:
            return {"nav_user": {"name": user["name"]}}
    return {"nav_user": None}


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    if request.method != "POST":
        abort(405)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    def fail(message):
        flash(message, "error")
        return render_template("register.html", name=name, email=email), 200

    if not name or not email or not password or not confirm_password:
        return fail("All fields are required.")
    if not EMAIL_PATTERN.match(email):
        return fail("Please enter a valid email address.")
    if len(password) < 8:
        return fail("Password must be at least 8 characters.")
    if password != confirm_password:
        return fail("Passwords do not match.")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        return fail("Email already registered.")

    flash("Account created. Please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("landing"))
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    def fail():
        flash("Invalid email or password.", "error")
        return render_template("login.html"), 200

    if not email or not password:
        return fail()

    user = get_user_by_email(email)
    if user is None:
        check_password_hash(DUMMY_HASH, password)
        return fail()
    if not check_password_hash(user["password_hash"], password):
        return fail()

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Session and expense routes                                          #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        # The session points at a user that no longer exists.
        session.clear()
        return redirect(url_for("login"))

    # A filter applies only when both dates are present and valid. A half-set
    # or malformed range silently falls back to "All Time". A reversed range
    # does the same, with a message.
    date_from = parse_iso_date(request.args.get("date_from"))
    date_to = parse_iso_date(request.args.get("date_to"))
    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.", "error")
        date_from = date_to = None
    elif not (date_from and date_to):
        date_from = date_to = None

    presets = get_presets(get_today())
    user["initials"] = get_initials(user["name"])
    return render_template(
        "profile.html",
        user=user,
        stats=get_summary_stats(user_id, date_from, date_to),
        expenses=get_recent_transactions(user_id, date_from=date_from, date_to=date_to),
        breakdown=get_category_breakdown(user_id, date_from, date_to),
        presets=presets,
        filter_from=date_from.isoformat() if date_from else "",
        filter_to=date_to.isoformat() if date_to else "",
        active_filter=get_active_filter(date_from, date_to, presets),
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    if get_user_by_id(user_id) is None:
        # The session points at a user that no longer exists.
        session.clear()
        return redirect(url_for("login"))

    if request.method == "GET":
        form = {
            "amount": "",
            "category": "",
            "date": get_today().isoformat(),
            "description": "",
        }
        return render_template("add_expense.html", categories=CATEGORIES, form=form)
    if request.method != "POST":
        abort(405)

    values, error = validate_expense_form(request.form)
    if error:
        flash(error, "error")
        # Show exactly what was submitted, so nothing the user typed is lost.
        form = {
            "amount": request.form.get("amount", ""),
            "category": request.form.get("category", ""),
            "date": request.form.get("date", ""),
            "description": request.form.get("description", ""),
        }
        return render_template("add_expense.html", categories=CATEGORIES, form=form), 200

    insert_expense(
        user_id,
        values["amount"],
        values["category"],
        values["date"],
        values["description"],
    )
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        # Checked before the expense is loaded, so a logged-out visitor learns
        # nothing about which expenses exist.
        return redirect(url_for("login"))

    # Scoped to the owner: a missing expense, someone else's expense and a
    # session for a deleted user all look the same, and all are a 404.
    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "GET":
        form = {
            "amount": f"{expense['amount']:.2f}",
            "category": expense["category"],
            "date": expense["date"],
            "description": expense["description"] or "",
        }
        return render_template(
            "edit_expense.html", categories=CATEGORIES, form=form, expense=expense
        )
    if request.method != "POST":
        abort(405)

    values, error = validate_expense_form(request.form)
    if error:
        flash(error, "error")
        # Show what was submitted, not the stored values, so nothing the user
        # typed is lost.
        form = {
            "amount": request.form.get("amount", ""),
            "category": request.form.get("category", ""),
            "date": request.form.get("date", ""),
            "description": request.form.get("description", ""),
        }
        return (
            render_template(
                "edit_expense.html", categories=CATEGORIES, form=form, expense=expense
            ),
            200,
        )

    changed = update_expense(
        id,
        user_id,
        values["amount"],
        values["category"],
        values["date"],
        values["description"],
    )
    if changed == 0:
        # The expense disappeared or changed owner between the lookup and the update.
        abort(404)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    # POST only: Flask answers any other method with 405, so a link or a page
    # load can never delete anything.
    user_id = session.get("user_id")
    if not user_id:
        # Checked before the expense is loaded, so a logged-out visitor learns
        # nothing about which expenses exist.
        return redirect(url_for("login"))

    # Scoped to the owner: a missing expense, someone else's expense and a
    # session for a deleted user all look the same, and all are a 404.
    if get_expense_by_id(id, user_id) is None:
        abort(404)

    if remove_expense(id, user_id) == 0:
        # The expense disappeared or changed owner between the lookup and the delete.
        abort(404)
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
