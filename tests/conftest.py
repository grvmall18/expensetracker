"""Shared test fixtures.

Tests must never touch the real spendly.db. The app seeds its database when
`app` is imported, so SPENDLY_DB_PATH is pointed at a throwaway file *before*
that import happens. Every test then gets its own fresh temporary database.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_IMPORT_DB_DIR = tempfile.TemporaryDirectory()
os.environ["SPENDLY_DB_PATH"] = os.path.join(_IMPORT_DB_DIR.name, "import-time.db")

import app as app_module  # noqa: E402  (must come after SPENDLY_DB_PATH is set)
from database.db import create_user, get_db, init_db, seed_db  # noqa: E402


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    """A fresh, seeded temporary database for every test."""
    path = tmp_path / "test.db"
    monkeypatch.setenv("SPENDLY_DB_PATH", str(path))
    init_db()
    seed_db()
    return path


@pytest.fixture
def app(database):
    app_module.app.config.update(TESTING=True)
    return app_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def demo_user_id(database):
    """Id of the seeded demo user, who owns the eight seed expenses."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()
    finally:
        conn.close()
    return row["id"]


@pytest.fixture
def make_user(database):
    """Create an extra user with no expenses and return the new id."""

    def _make_user(name="New User", email="new.user@example.com", password="password123"):
        return create_user(name, email, password)

    return _make_user


@pytest.fixture
def add_expense(database):
    """Insert an expense with raw SQL (insert_expense arrives in Step 07)."""

    def _add_expense(user_id, amount, category, expense_date, description=None):
        conn = get_db()
        try:
            cursor = conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, expense_date, description),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    return _add_expense


@pytest.fixture
def fixed_today(monkeypatch):
    """Pin the app's idea of "today" to 2026-03-15 and return that date."""
    from datetime import date

    today = date(2026, 3, 15)
    monkeypatch.setattr(app_module, "get_today", lambda: today)
    return today


@pytest.fixture
def login(client):
    """Log a user in by setting session["user_id"] directly."""

    def _login(user_id):
        with client.session_transaction() as session:
            session["user_id"] = user_id

    return _login
