# 05 — Backend Routes for Profile Page

## Overview

- This step replaces all hardcoded data in the `/profile` route with live queries against the SQLite database.
- The profile page currently renders a static demo user, fixed summary stats, a hand-typed transaction list, and a hardcoded category breakdown.
- This step connects those four sections to real data, so every logged-in user sees their own expenses. It also replaces the hardcoded navbar name with a database lookup.
- Three parallel subagents handle the three independent data concerns, which are transaction history, summary stats, and category breakdown. Their results are then integrated into the single `/profile` route.

## Depends on

- Step 01 — Database setup, implemented in code. The tables, `get_db()`, `SPENDLY_DB_PATH` support, and the seed data exist.
- Step 02 — Registration, implemented in code. Users are stored in the database.
- Step 03 — Login and Logout, implemented in code. `session["user_id"]` is set on login.
- Step 04 — Profile page static UI, implemented in code. The template already renders all four sections, and `static/css/profile.css` exists.

## Routes

- No new routes.
- The existing `GET /profile` route is modified in place.
- If `session["user_id"]` refers to a user that no longer exists in the database, the route clears the session and redirects to `/login`.

## Database changes

- No database changes.
- The `users` and `expenses` tables already have all the required columns: `user_id`, `amount`, `category`, `date`, `description`, and `created_at`.

## Templates

- Modify `templates/profile.html`:
  - Render all amounts with the ₹ symbol (Indian Rupee), using one shared Jinja filter registered in `app.py`. The filter outputs the ₹ symbol, commas as thousands separators, and exactly two decimal places. Never use £ or $.
  - The four dynamic sections are already present in the template, so no structural changes are needed. Only the Jinja variables they consume become real data.
  - When a user has no expenses, the stats show ₹0.00 and 0 transactions, the top category shows "—", and the breakdown section is empty.

## Files to change

- `app.py`:
  - Replace the hardcoded data in the `profile()` view with calls to the new query helpers in `database/queries.py`.
  - Replace the hardcoded navbar name from Step 04 with a lookup through `get_user_by_id`.
  - Register the currency filter.
- `templates/profile.html` — confirm the shared currency filter is used for every amount.

## Files to create

- `database/queries.py` — pure query helpers with no Flask imports. One function per data concern:
  - `get_user_by_id(user_id)` returns a dict with `name`, `email`, and `member_since`, or `None` if no user matches.
  - `get_summary_stats(user_id)` returns a dict with `total_spent`, `transaction_count`, and `top_category`.
  - `get_recent_transactions(user_id, limit=10)` returns a list of dicts, each with `date`, `description`, `category`, and `amount`, ordered newest first.
  - `get_category_breakdown(user_id)` returns a list of dicts, each with `name`, `amount`, and `pct`. `pct` is the percentage of the total, rounded to the nearest integer. The list is ordered by amount, descending.
- `tests/conftest.py` — shared fixtures: a temporary database selected through `SPENDLY_DB_PATH`, `init_db()` and `seed_db()` run against it, the Flask test client, and a helper to create an extra user with no expenses.
- `tests/test_backend_connection.py` — unit and route tests for this step.

## New dependencies

- None. `pytest` and `pytest-flask` are already in `requirements.txt`.

## Rules for implementation

- No SQLAlchemy or ORMs. Use raw `sqlite3` through `get_db()` only.
- Use parameterised queries only. Never string-format values into SQL.
- `PRAGMA foreign_keys = ON` must be enabled on every connection. This is already handled in `get_db()`.
- Currency must always display as ₹. Never £ or $. Helpers return raw numbers, and all formatting happens in the template through the shared filter.
- `total_spent` and every `amount` returned by a helper must be rounded to two decimal places, so floating-point sums such as 346.24000000000007 never reach the page.
- `member_since` must be derived from `users.created_at` (stored as `YYYY-MM-DD HH:MM:SS`) and formatted as "Month YYYY", for example "January 2026".
- Transactions are ordered by `date` descending, then by `id` descending, so expenses on the same date have a stable order.
- `top_category` is the category with the highest total. If two categories tie, the one that comes first alphabetically wins.
- `pct` values in the category breakdown must sum to 100. Use integer rounding, and adjust the largest category to absorb any rounding remainder. When there are no expenses, return an empty list, so no division by zero happens.
- If a user has no expenses, all helpers must return zeros and empty lists. `top_category` is "—". Helpers must never raise exceptions for this case.
- All helpers in `database/queries.py` must call `get_db()` internally and close the connection before returning.
- Tests must never touch the real `spendly.db`. They use the temporary database from `tests/conftest.py`.
- Use CSS variables. Never hardcode hex values.
- No inline styles.
- All templates extend `base.html`.

## Tests to write

- Files: `tests/conftest.py` and `tests/test_backend_connection.py`.
- Seed data: the eight seed expenses defined in Step 01, totalling 346.24.
- Unit tests:

| Function | Input | Expected output |
|---|---|---|
| get_user_by_id | Valid user_id | Dict with the correct name, email, and member_since |
| get_user_by_id | Non-existent id | None |
| get_summary_stats | user_id with expenses | Correct total_spent, transaction_count, and top_category |
| get_summary_stats | user_id with no expenses | {"total_spent": 0, "transaction_count": 0, "top_category": "—"} |
| get_recent_transactions | user_id with expenses | List ordered newest first. Each item has date, description, category, and amount |
| get_recent_transactions | user_id with expenses and limit smaller than the count | Only `limit` items, still newest first |
| get_recent_transactions | Two expenses on the same date | The one with the higher id comes first |
| get_recent_transactions | user_id with no expenses | Empty list |
| get_category_breakdown | user_id with expenses | List ordered by amount, descending. pct values are integers that sum to 100 |
| get_category_breakdown | user_id with no expenses | Empty list |

- Route tests, logging in by setting `session["user_id"]` through the test client's session transaction:
  - `GET /profile` while unauthenticated redirects to `/login` with status 302.
  - `GET /profile` with a session for a user id that does not exist redirects to `/login` with status 302.
  - `GET /profile` while authenticated as the seed user:
    - Returns status 200.
    - The response contains "Demo User".
    - The response contains "demo@spendly.com".
    - The response contains the ₹ symbol.
    - `total_spent` matches the sum of all seed expenses, which is 346.24.
    - `transaction_count` is 8.
    - `top_category` is "Bills", the category with the highest single total.
    - The transaction list appears in newest-first order.
    - The category breakdown contains all 7 categories.
  - `GET /profile` while authenticated as a new user with no expenses returns status 200 and shows ₹0.00 and 0 transactions.

## Definition of done

- [ ] Logging in as demo@spendly.com / demo123 shows "Demo User" and "demo@spendly.com" on the profile page, not the hardcoded strings
- [ ] Total spent on the profile page equals ₹346.24
- [ ] Transaction count on the profile page is 8
- [ ] Top category on the profile page is "Bills"
- [ ] The transaction list shows 8 rows, ordered newest date first
- [ ] The category breakdown shows 7 categories, and their percentages add up to 100%
- [ ] All amounts on the page display the ₹ symbol with two decimal places
- [ ] The navbar shows the real user name from the database
- [ ] A session pointing at a deleted user is cleared and redirected to `/login`
- [ ] Registering a brand-new user and visiting `/profile` shows ₹0.00 total spent, 0 transactions, and an empty category breakdown, with no errors
- [ ] The test suite passes and never writes to `spendly.db`
