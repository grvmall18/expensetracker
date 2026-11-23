# 01 — Database Setup

## 1. Overview

This step replaces the stub in `database/db.py` with a working SQLite implementation. The file currently contains only comments and defines no functions, so all three functions are written from scratch. The step creates the database connection helper, the two core tables (`users` and `expenses`), and a small, fully specified demo dataset for development.

This is the foundational step of Spendly. Authentication, the profile page, and expense tracking all depend on the tables and connection helper created here. Nothing in the app can store or read real data until this step is implemented in code.

## 2. Depends on

This is the first step. It has no prerequisites.

## 3. Routes

- No new routes are added in this step.
- The existing placeholder routes in `app.py` remain unchanged.

## 4. Database Schema

The database file is `spendly.db`, located in the project root unless overridden (see section 5).

### Table A: users

| Column | SQLite Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| name | TEXT | NOT NULL |
| email | TEXT | NOT NULL, UNIQUE |
| password_hash | TEXT | NOT NULL |
| created_at | TEXT | NOT NULL, DEFAULT CURRENT_TIMESTAMP |

### Table B: expenses

| Column | SQLite Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| user_id | INTEGER | NOT NULL, FOREIGN KEY references users(id) |
| amount | REAL | NOT NULL |
| category | TEXT | NOT NULL |
| date | TEXT | NOT NULL. Must be in YYYY-MM-DD format |
| description | TEXT | None (optional) |
| created_at | TEXT | NOT NULL, DEFAULT CURRENT_TIMESTAMP |

The `expenses.date` column must always hold a date in `YYYY-MM-DD` format.

## 5. Functions to Implement (database/db.py)

- **get_db()**: Opens the SQLite database and returns the connection.
  - The database path is read from the environment variable `SPENDLY_DB_PATH` if it is set. Otherwise it is `spendly.db` in the project root. This lets tests use a temporary database without touching the real one.
  - Sets `row_factory = sqlite3.Row`.
  - Enables `PRAGMA foreign_keys = ON`.
  - Returns a new connection on every call. The caller is responsible for closing it.
- **init_db()**: Creates both tables using `CREATE TABLE IF NOT EXISTS`. Safe to call multiple times.
- **seed_db()**: Checks whether the `users` table already has rows. If it does, returns early. Otherwise inserts:
  - One demo user with name `Demo User`, email `demo@spendly.com`, and password `demo123`, hashed via werkzeug.
  - The eight sample expenses in the table below, all linked to the demo user.

### Seed expenses

| # | Day offset from the 1st | Category | Amount | Description |
|---|---|---|---|---|
| 1 | 0 | Bills | 120.00 | Electricity bill |
| 2 | 2 | Food | 62.50 | Weekly groceries |
| 3 | 4 | Transport | 28.00 | Metro card recharge |
| 4 | 6 | Health | 35.74 | Pharmacy |
| 5 | 9 | Shopping | 45.00 | Headphones |
| 6 | 12 | Entertainment | 18.00 | Movie ticket |
| 7 | 15 | Food | 27.00 | Lunch with friends |
| 8 | 19 | Other | 10.00 | Miscellaneous |

- Each date is the first day of the current month plus the day offset, in `YYYY-MM-DD` format. If that date would be later than today, use today instead, so no seed expense is ever dated in the future.
- The seed amounts total 346.24.
- The category totals are Bills 120.00, Food 89.50, Shopping 45.00, Health 35.74, Transport 28.00, Entertainment 18.00, and Other 10.00. Bills is the top category.

## 6. Changes to app.py

- Import `get_db`, `init_db`, and `seed_db` from `database.db`.
- Call `init_db()` and `seed_db()` inside `app.app_context()` on startup.
- The database must be ready before any route is served.

## 7. Files to Change

- `database/db.py`
- `app.py`
- `.gitignore` — add `spendly.db`, so the seeded database file is never committed. The existing entry `expense_tracker.db` does not match it.

No other files are changed.

## 8. Files to Create

- None.

## 9. Dependencies

- No new pip packages.
- Use `sqlite3` (standard library).
- Use `werkzeug.security` (already installed).

## 10. Categories (Fixed List)

- Food
- Transport
- Bills
- Health
- Entertainment
- Shopping
- Other

These are the only valid values for `expenses.category`.

## 11. Rules for Implementation

- No ORM. Do not use SQLAlchemy.
- Use parameterized queries only. Never use string formatting in SQL.
- Run `PRAGMA foreign_keys = ON` on every connection.
- Store `amount` as REAL, not INTEGER.
- Hash passwords with `generate_password_hash` from `werkzeug.security`.
- `seed_db()` must be idempotent (safe to call multiple times).
- Dates must always be `YYYY-MM-DD`.
- The database path must come from `SPENDLY_DB_PATH` when set, so tests never write to the real database.

## 12. Expected Behavior

When called correctly:

- **get_db()** returns an open connection to the configured database. Rows can be read by column name, and foreign key enforcement is on.
- **init_db()** creates both tables if they do not exist. Calling it again changes nothing and raises no error.
- **seed_db()** on an empty database inserts the demo user and the eight seed expenses. On a database that already has users, it does nothing.

The database must enforce these constraints:

- `users.email` must be unique.
- Every `expenses.user_id` must refer to an existing user.
- Columns marked NOT NULL must reject NULL values.

## 13. Error Handling Expectations

- Inserting a duplicate email must fail with a UNIQUE constraint failure.
- Inserting an expense with an invalid `user_id` must fail with a foreign key constraint failure.
- Invalid queries must raise clear errors that help with debugging. Errors must not be silently hidden.
- If the database file cannot be created or opened, the error must surface at startup. The app must not start in a half-working state.

## 14. Definition of Done

- [ ] Database file is created on app startup
- [ ] Both tables exist with the correct schema and constraints
- [ ] Demo user exists with a hashed password
- [ ] Eight sample expenses exist across all seven categories, matching the seed table
- [ ] Seed amounts total 346.24 and Bills is the top category
- [ ] No seed expense is dated in the future
- [ ] No duplicate seed data on repeated runs
- [ ] Setting `SPENDLY_DB_PATH` makes the app and tests use that file instead of `spendly.db`
- [ ] `spendly.db` is listed in `.gitignore`
- [ ] App starts without errors
- [ ] Foreign key enforcement works
- [ ] All queries use parameterized SQL
