---
name: spendly-database
description: Create, reset, seed or change the Spendly SQLite database (spendly.db) through database/db.py - users and expenses tables, get_db, init_db, seed_db, CATEGORIES. Use for any schema or seed-data work.
---

# Spendly database (SQLite)

Use this skill when a task needs to create, rebuild, reset, seed or change the schema of the Spendly database, or edits `database/db.py`.

Sources of truth:

- What exists today: `database/db.py`.
- Required behaviour: the specs in `.claude/specs/` - `01-database-setup.md` (schema, `get_db`, `init_db`, `seed_db`, categories), `02-registration.md` (`create_user`), `03-login_logout.md` (`get_user_by_email`).
- The `*-review.md` files are background, not requirements. This skill ranks below the code and the specs.

Read the relevant spec before changing anything. If the code and a spec disagree, tell the user instead of picking one silently.

## Where things live

```
Expense_Tracker_Basic/
├── app.py               # imports init_db/seed_db and runs them inside app.app_context() at import time
├── database/
│   ├── __init__.py
│   ├── db.py            # connection, schema, seed, CATEGORIES, create_user, get_user_by_email
│   └── queries.py       # profile/expense data access, including insert_expense
├── spendly.db           # created at the project root; gitignored
└── tests/conftest.py    # points SPENDLY_DB_PATH at a temp file before importing app
```

## Rules (do not break)

- Built-in `sqlite3` only. No ORM, no SQLAlchemy, no new pip packages.
- All schema and demo-seed code stays in `database/db.py`.
- Parameterised queries (`?`) only. Never f-strings, `%` or `.format()` in SQL.
- `get_db()` opens a **new** connection on every call; the caller closes it (`try/finally: conn.close()`).
- Every connection sets `row_factory = sqlite3.Row` and runs `PRAGMA foreign_keys = ON`.
- DB path: `os.environ.get("SPENDLY_DB_PATH")`, falling back to `DEFAULT_DB_PATH` (`spendly.db` in the project root, built from `Path(__file__).resolve().parent.parent`). Never hardcode a path relative to the working directory, and never remove the env var - the tests depend on it.
- `amount` is `REAL`. `date` is `TEXT` in `YYYY-MM-DD` (the profile date filter compares strings).
- Passwords only as `werkzeug.security.generate_password_hash` hashes.
- `init_db()` and `seed_db()` must be idempotent; they run on every import of `app`.

## Schema (as implemented)

| Table | Column | Type | Constraints |
|---|---|---|---|
| users | id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| users | name | TEXT | NOT NULL |
| users | email | TEXT | NOT NULL UNIQUE |
| users | password_hash | TEXT | NOT NULL |
| users | created_at | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP |
| expenses | id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| expenses | user_id | INTEGER | NOT NULL REFERENCES users(id) |
| expenses | amount | REAL | NOT NULL |
| expenses | category | TEXT | NOT NULL |
| expenses | date | TEXT | NOT NULL, YYYY-MM-DD |
| expenses | description | TEXT | nullable |
| expenses | created_at | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP |

There is no `ON DELETE CASCADE`, no CHECK constraint and no explicit index (`UNIQUE` on `users.email` creates an automatic one). Deleting a user who still has expenses fails with a foreign key error. Don't add any of these unless the user asks.

`CATEGORIES` in `db.py` is the list of valid categories: Food, Transport, Bills, Health, Entertainment, Shopping, Other. Python code imports it, and `app.py` passes it to the templates. Don't type the list again in routes or templates.

## Functions in database/db.py

- `get_db()` - see rules above.
- `init_db()` - `CREATE TABLE IF NOT EXISTS` for `users` then `expenses`, commit, close.
- `seed_db()` - return early if `users` has any row. Otherwise insert `Demo User` / `demo@spendly.com` / hashed `demo123`, then the 8 rows in `SEED_EXPENSES` with `executemany`. Each row is `(day offset from the 1st of the current month, category, amount, description)`; the date is `min(first_of_month + offset, today)`, so seed dates are always in the current month and never in the future. The 8 rows cover all 7 categories.
- `create_user(name, email, password)` - insert with hashed password, return the new id; raises `sqlite3.IntegrityError` for a duplicate email.
- `get_user_by_email(email)` - return the row or `None`.

Run every command below from the project root. Each works in both PowerShell and Git Bash.

## Which database file is in use

```
python -c "import os; print(os.environ.get('SPENDLY_DB_PATH'))"
```

`None` means `spendly.db` in the project root. Anything else is the file the app and these commands will use; confirm with the user that it is the intended one before writing to it.

## Adding users and expenses for development

`seed_db()` only creates the demo data, and only in an empty database. For anything extra, leave `db.py` alone.

- Commands: `/seed-user` adds one random user; `/seed-expense <user_id> <count> <months>` adds expenses for a user.
- One user by hand. Pass a lowercase email: login lowercases what is typed, and `create_user` does not.
  ```
  python -c "from database.db import create_user; print(create_user('Asha Rao', 'asha@example.com', 'password123'))"
  ```
- One expense: `insert_expense(user_id, amount, category, date, description)` from `database/queries.py`. It does not validate, so pass a category from `CATEGORIES`, a positive amount and a `YYYY-MM-DD` date.
- Many expenses: a throwaway script that uses one `get_db()` connection, `executemany`, a single `commit()`, and `rollback()` on failure. Don't commit the script.

## Changing the schema or demo data

1. Read the spec and `database/db.py`.
2. Make the change in `db.py`. Keep `app.py`'s startup block (`with app.app_context(): init_db(); seed_db()`) intact.
3. An existing database will not pick the change up: `CREATE TABLE IF NOT EXISTS` does not alter tables, and `seed_db()` returns early. Tell the user, and either reset (below) or, if the data must be kept, agree a migration with them first.
4. Verify and run the tests.
5. Report what changed and the verification output.

## Resetting the database

A reset deletes every user and expense. **Ask the user before step 3.**

1. Check which file is in use (above). The commands below assume `spendly.db`; if `SPENDLY_DB_PATH` is set, use that path instead.
2. Ask the user to stop the dev server (`python app.py`), or stop it yourself if you started it.
3. Back up outside the repo, then delete only after the backup path is printed:
   ```
   python -c "import shutil, time; print(shutil.copy2('spendly.db', time.strftime('../spendly-backup-%Y%m%d-%H%M%S.db')))"
   python -c "import os; os.remove('spendly.db')"
   ```
4. Recreate it:
   ```
   python -c "from database.db import init_db, seed_db; init_db(); seed_db()"
   ```
5. Verify.

To create a database that doesn't exist yet, run only steps 4 and 5.

## Verify

```
python -c "from database.db import get_db; c=get_db(); print([r[0] for r in c.execute('SELECT name FROM sqlite_master WHERE type=?', ('table',))]); print(c.execute('SELECT COUNT(*) FROM users').fetchone()[0], c.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]); print(c.execute('PRAGMA foreign_keys').fetchone()[0]); c.close()"
```

Expect `users` and `expenses` in the table list (plus `sqlite_sequence`, which SQLite creates for `AUTOINCREMENT`), counts `1 8` on a fresh seed, and `1` for foreign keys. Running `seed_db()` again must not change the counts. The `sqlite3` command-line tool may not be installed on Windows, so use Python.

Then run `python -m pytest` (about 220 tests, ~1 minute). Every test gets a fresh seeded temp DB, so schema or seed changes show up across the whole suite.

## Changing categories

Specs 01, 07 and 08 fix the seven categories, so confirm the change with the user first. Use single-word names: CSS class names are the lowercased category.

- [ ] `database/db.py`: `CATEGORIES`, and `SEED_EXPENSES` if it uses a removed name.
- [ ] `static/css/profile.css`: `--cat-<name>` and `--cat-<name>-bg` in `:root`, plus `.badge-<name>` and `.bar-<name>`.
- [ ] `tests/test_backend_connection.py`: `SEED_CATEGORIES` if the demo data changes.
- [ ] `.claude/commands/seed-expense.md`: its category list.
- [ ] This skill and the specs that list the categories.
- [ ] Existing rows with a renamed or removed category: the edit form cannot show the old value and preselects the first option, so saving would silently change it. Ask before updating those rows.

## Testing notes

- Never point tests at the real `spendly.db`. `tests/conftest.py` sets `SPENDLY_DB_PATH` **before** `import app` because importing seeds the DB - keep that order.
- Use the existing fixtures (`database`, `client`, `login`, `make_user`, `add_expense`, `demo_user_id`, `fixed_today`) instead of opening connections by hand.
- Tests that depend on seed dates should use `fixed_today` (pins `app.get_today` to 2026-03-15) or explicit dates.
- Useful DB checks: duplicate email raises `sqlite3.IntegrityError`; an expense with an unknown `user_id` raises `sqlite3.IntegrityError` (foreign key); `seed_db()` twice leaves 1 user and 8 expenses.
