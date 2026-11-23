"""Query helpers for the profile and expense pages.

Pure data access: no Flask imports. Each helper opens its own connection with
get_db() and closes it before returning. Helpers return raw numbers; all
formatting (currency, dates) happens in the templates. Everything here only
reads, except insert_expense().

The stats, transaction and breakdown helpers accept an optional date range.
A range applies only when both date_from and date_to are given (date objects
or YYYY-MM-DD strings, both ends inclusive). With no range they return every
expense, exactly as before.
"""

from datetime import date

from database.db import get_db

NO_CATEGORY = "—"

# SQLite integers are 8 bytes. A Python int outside this range cannot be bound
# as a query parameter (sqlite3 raises OverflowError), and no row can have such
# an id, so the helpers below treat it as "not found" without touching the
# database. The URL converter accepts numbers of any length, so a visitor can
# reach this with a long enough id.
_SQLITE_MIN_INT = -(2**63)
_SQLITE_MAX_INT = 2**63 - 1


def _is_possible_row_id(value):
    """True if value can be bound as a SQLite INTEGER, so a row could have it."""
    return _SQLITE_MIN_INT <= value <= _SQLITE_MAX_INT


def _date_filter(date_from, date_to):
    """Return (sql_fragment, params) narrowing expenses to a date range.

    The fragment is a fixed string; only the bound values vary. If either end
    is missing, no filter is applied.
    """
    if date_from and date_to:
        return " AND date BETWEEN ? AND ?", (str(date_from), str(date_to))
    return "", ()


def get_user_by_id(user_id):
    """Return {"name", "email", "member_since"} for the user, or None.

    member_since is "Month YYYY", for example "January 2026".
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    joined = date.fromisoformat(row["created_at"][:10])
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": joined.strftime("%B %Y"),
    }


def get_summary_stats(user_id, date_from=None, date_to=None):
    """Return {"total_spent", "transaction_count", "top_category"}.

    A user with no expenses in the range gets zeros and "—". When two
    categories tie for the highest total, the one that comes first
    alphabetically wins.
    """
    clause, params = _date_filter(date_from, date_to)
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total "
            "FROM expenses WHERE user_id = ?" + clause,
            (user_id, *params),
        ).fetchone()
        top = conn.execute(
            "SELECT category, ROUND(SUM(amount), 2) AS total FROM expenses "
            "WHERE user_id = ?" + clause + " GROUP BY category "
            "ORDER BY total DESC, category ASC LIMIT 1",
            (user_id, *params),
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_spent": round(totals["total"], 2),
        "transaction_count": totals["n"],
        "top_category": top["category"] if top else NO_CATEGORY,
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    """Return up to `limit` expenses, newest first.

    Expenses on the same date are ordered by id, highest first, so the order is
    stable. Each item has id, date, description, category and amount.
    """
    clause, params = _date_filter(date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + clause + " ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, *params, limit),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row["id"],
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": round(row["amount"], 2),
        }
        for row in rows
    ]


def get_category_breakdown(user_id, date_from=None, date_to=None):
    """Return [{"name", "amount", "pct"}], largest category first.

    pct is an integer percentage of the user's total in the range, and the
    percentages sum to 100: the largest category absorbs any rounding
    remainder. A user with no expenses in the range gets an empty list.
    """
    clause, params = _date_filter(date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category AS name, ROUND(SUM(amount), 2) AS amount "
            "FROM expenses WHERE user_id = ?" + clause + " GROUP BY category "
            "ORDER BY amount DESC, name ASC",
            (user_id, *params),
        ).fetchall()
    finally:
        conn.close()

    breakdown = [{"name": row["name"], "amount": row["amount"]} for row in rows]
    if not breakdown:
        return []

    grand_total = sum(item["amount"] for item in breakdown)
    if grand_total <= 0:
        for item in breakdown:
            item["pct"] = 0
        return breakdown

    for item in breakdown:
        item["pct"] = int(item["amount"] / grand_total * 100 + 0.5)
    breakdown[0]["pct"] += 100 - sum(item["pct"] for item in breakdown)
    return breakdown


def insert_expense(user_id, amount, category, date, description):
    """Insert an expense and return its new id.

    The caller validates the values first; this function does not. A
    description of None is stored as NULL. Raises sqlite3.IntegrityError if
    user_id does not refer to an existing user.
    """
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, str(date), description),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_expense_by_id(expense_id, user_id):
    """Return one expense as a dict, or None.

    The query is scoped to the owner, so an expense that does not exist and an
    expense that belongs to someone else look exactly the same: None. So does an
    id too large for SQLite to store.
    """
    if not _is_possible_row_id(expense_id):
        return None
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, user_id, amount, category, date, description "
            "FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "amount": round(row["amount"], 2),
        "category": row["category"],
        "date": row["date"],
        "description": row["description"],
    }


def update_expense(expense_id, user_id, amount, category, date, description):
    """Update an expense in place and return the number of rows changed.

    The WHERE clause names the owner as well as the expense, as a second
    ownership guard: for someone else's expense nothing changes and 0 is
    returned. Only the four editable columns are written, so user_id and
    created_at never change. The caller validates the values first. An id too
    large for SQLite to store matches nothing, so 0 is returned.
    """
    if not _is_possible_row_id(expense_id):
        return 0
    conn = get_db()
    try:
        cursor = conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
            "WHERE id = ? AND user_id = ?",
            (amount, category, str(date), description, expense_id, user_id),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def delete_expense(expense_id, user_id):
    """Permanently delete an expense and return the number of rows deleted.

    The WHERE clause names the owner as well as the expense, as a second
    ownership guard: for someone else's expense, or one that does not exist,
    nothing is deleted and 0 is returned, as it is for an id too large for
    SQLite to store. Deletion cannot be undone.
    """
    if not _is_possible_row_id(expense_id):
        return 0
    conn = get_db()
    try:
        cursor = conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
