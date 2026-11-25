# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Spendly is a small Flask + SQLite expense tracker: registration, login, a profile page with stats, category breakdown and date filter, and add/edit/delete for expenses. Server-rendered Jinja templates, no JS framework, no ORM. Amounts are shown in rupees via the `inr` template filter.

## Commands

```bash
pip install -r requirements.txt                          # flask, werkzeug, pytest, pytest-flask
python app.py                                            # dev server at http://localhost:5001 (debug=True)
python -m pytest                                         # full suite (220 tests, about 1 minute)
python -m pytest tests/test_edit_expense.py -v           # one file
python -m pytest tests/test_edit_expense.py -k "name"    # tests whose names match
```

No linter or build step is configured.

Importing `app` runs `init_db()` and `seed_db()` against `spendly.db` (gitignored). If the users table is empty, this creates the demo user `demo@spendly.com` / `demo123` with 8 expenses dated in the current month.

## Architecture

- `app.py` is the whole web layer: routes, form validation (`validate_expense_form`), display helpers, template filters, and the date-preset logic for the profile filter. Auth is a bare `session["user_id"]`. Each protected route (profile, add, edit, delete) checks it and redirects to `/login` itself; there is no decorator.
- `database/db.py` holds the connection, schema and seed. `get_db()` opens a **new** connection on every call (row_factory=Row, foreign keys on), and callers close it. It also owns `CATEGORIES`, the only valid expense categories, and user creation and lookup by email.
- `database/queries.py` is pure data access for the profile and expense pages, with no Flask imports. Each helper opens and closes its own connection and returns raw numbers; formatting happens in the templates. Expense lookups and mutations are always scoped by `user_id`, so another user's expense looks the same as a missing one, and both return 404. Ids outside SQLite's 8-byte range are treated as not found (`_is_possible_row_id`) rather than raising `OverflowError`.
- Date filtering: the stats, transaction and breakdown helpers take optional `date_from`/`date_to`, and the range applies only when **both** are given. `/profile` silently falls back to "All Time" for a half-set or malformed range, and flashes an error for a reversed one.

### Schema

- `users(id, name, email UNIQUE, password_hash, created_at)`
- `expenses(id, user_id -> users, amount REAL, category, date TEXT as YYYY-MM-DD, description, created_at)`

### Gotchas

- **Name clash:** the view function `delete_expense` in `app.py` shares its name with the query helper, so the helper is imported as `remove_expense`. The profile template links to the route by the name `delete_expense`, so don't rename the view.
- **Test DB isolation:** the database path comes from the `SPENDLY_DB_PATH` env var and falls back to `spendly.db`. `tests/conftest.py` sets the variable to a temp file *before* importing `app`, because importing seeds the database. It also gives every test a fresh seeded DB. Keep that import order. Fixtures: `client`, `login(user_id)` (sets the session directly), `make_user`, `add_expense`, `demo_user_id`, and `fixed_today` (pins `app.get_today` to 2026-03-15).
- Seed expense dates are relative to the current month, so tests that depend on dates should use `fixed_today` or explicit dates.
- `app.secret_key` is a hardcoded dev value. Delete is POST-only, so GET returns 405.

## Spec-driven workflow

Features are built in numbered steps. Each step has a prompt file in the repo root (`Spec_NN_*.md`) and a spec in `.claude/specs/NN-*.md`, with a review in `.claude/specs/NN-*-review.md` when one exists (steps 08 and 09 have none). File names are not consistent between steps, for example `03-login_logout.md` vs `03-login-logout-review.md`, so glob rather than guess. `.claude/plans/` is gitignored.

Custom slash commands live in `.claude/commands/`: `/create-spec`, `/test-feature <spec-name>`, `/code-review-feature <spec-name>`, `/seed-user`, `/seed-expense`, and `/ship-feature`. Only `/create-spec` reads this file, and it uses the roadmap below to check that a requested step isn't already done. Read the relevant spec before changing a feature, since specs are the source of truth for route and validation behavior.

### Roadmap

Steps 01–09 are implemented, and the next new step is 10.

| Step | Feature | Dedicated test file |
|---|---|---|
| 01 | Database setup | none |
| 02 | Registration | none |
| 03 | Login and logout | none |
| 04 | Profile page | none |
| 05 | Backend routes for the profile page | `test_backend_connection.py` |
| 06 | Date filter on the profile | none |
| 07 | Add expense | `test_add_expense.py` |
| 08 | Edit expense | `test_edit_expense.py` |
| 09 | Delete expense | `test_delete_expense.py` and `test_09-delete-expense.py` |

### Test file naming

Test files are not named after specs consistently. `/test-feature <arg>` runs `tests/test_<arg>.py`, so only the step-09 file, `test_09-delete-expense.py`, matches a spec name. For the other steps use the file names in the table above. Step 09 has two overlapping files, `test_delete_expense.py` (35 tests) and `test_09-delete-expense.py` (58 tests, written from the spec and the more thorough of the two). Both cover the route, the query helper, the rendered Delete buttons and the `.btn-delete` CSS rule. Add new delete tests to `test_09-delete-expense.py` rather than creating a third file.
