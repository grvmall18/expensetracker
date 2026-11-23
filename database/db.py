"""SQLite database helpers for Spendly.

get_db()   -- returns a SQLite connection with row access by name and
              foreign keys enabled
init_db()  -- creates all tables using CREATE TABLE IF NOT EXISTS
seed_db()  -- inserts demo data for development (idempotent)
"""

import os
import sqlite3
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash

# spendly.db lives in the project root (the parent of this package folder).
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "spendly.db"

# The only valid values for expenses.category.
CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

# (day offset from the 1st of the current month, category, amount, description)
SEED_EXPENSES = [
    (0, "Bills", 120.00, "Electricity bill"),
    (2, "Food", 62.50, "Weekly groceries"),
    (4, "Transport", 28.00, "Metro card recharge"),
    (6, "Health", 35.74, "Pharmacy"),
    (9, "Shopping", 45.00, "Headphones"),
    (12, "Entertainment", 18.00, "Movie ticket"),
    (15, "Food", 27.00, "Lunch with friends"),
    (19, "Other", 10.00, "Miscellaneous"),
]


def get_db():
    """Open and return a new SQLite connection. The caller closes it.

    The database path comes from the SPENDLY_DB_PATH environment variable
    when it is set (so tests can use a temporary file); otherwise it is
    spendly.db in the project root.
    """
    db_path = os.environ.get("SPENDLY_DB_PATH") or str(DEFAULT_DB_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the users and expenses tables if they do not exist."""
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert the demo user and sample expenses. Does nothing if users exist."""
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cursor.lastrowid

        today = date.today()
        first_of_month = today.replace(day=1)
        rows = []
        for offset, category, amount, description in SEED_EXPENSES:
            expense_date = min(first_of_month.replace(day=1 + offset), today)
            rows.append(
                (user_id, amount, category, expense_date.isoformat(), description)
            )

        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def create_user(name, email, password):
    """Insert a new user with a hashed password and return the new user's id.

    Raises sqlite3.IntegrityError if the email is already registered.
    """
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


def get_user_by_email(email):
    """Return the user row with this email, or None if there is no such user."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()
