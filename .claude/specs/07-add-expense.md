# Add Expense

## Overview

- This step lets a logged-in user submit a new expense through a dedicated form page at `/expenses/add`.
- The route already exists as a GET placeholder. This step upgrades it to a full GET and POST handler.
- Validated data is inserted into the `expenses` table, and the user is redirected to the profile page on success.
- A reusable `insert_expense()` query helper is added to `database/queries.py`.
- An "Add Expense" button is added to `profile.html`, and an "Add Expense" link is added to the navbar in `base.html`, so users can reach the form.

## Depends on

- Step 01 — Database setup, implemented in code. The `expenses` table exists with all required columns, and `get_db()` is available.
- Step 03 — Login and Logout, implemented in code. `session["user_id"]` is set on login and checked by this route.
- Step 04 and Step 05 — Profile page, implemented in code. The profile page is the redirect target after saving.
- Step 06 — Date filter for the profile page, implemented in code. The `today` helper in `app.py` supplies the default date for the form.

## Routes

- `GET /expenses/add` — render the add-expense form — logged-in only.
- `POST /expenses/add` — validate the submitted data and insert the new expense — logged-in only.
- Unauthenticated requests to either method redirect to `/login` with status 302. A POST from a logged-out user is discarded and never inserts anything.

## Database changes

- No database changes.
- The `expenses` table already has all required columns: `id`, `user_id`, `amount`, `category`, `date`, `description`, and `created_at`.
- `created_at` is set by the database default. The helper does not write it.

## Templates

- Create `templates/add_expense.html`:
  - Extends `base.html`.
  - Contains a form with `method="POST"` and `action="/expenses/add"`, using `url_for('add_expense')` for the action.
  - Fields:
    - `amount` — number input, `step="0.01"`, `min="0.01"`, `required`.
    - `category` — a `<select>` with exactly seven options, in this order: Food, Transport, Bills, Health, Entertainment, Shopping, Other.
    - `date` — `<input type="date">`, `required`, defaulting to today's date.
    - `description` — text input, optional, `maxlength="200"`.
  - A submit button labelled "Save Expense" and a cancel link back to `/profile`, generated with `url_for('profile')`.
  - A block that displays flashed error messages.
  - On a failed submission, every field is re-populated with the submitted values, and the selected category stays selected.
- Modify `templates/profile.html`:
  - Add an "Add Expense" button or link pointing to `url_for('add_expense')`, placed next to the transaction history heading.
- Modify `templates/base.html`:
  - Add an "Add Expense" link to the navbar, shown only when `session.user_id` is set. Place it alongside the existing Profile and Logout links from Step 04.

## Files to change

- `app.py`:
  - Replace the GET-only placeholder at `/expenses/add` with a GET and POST handler.
  - GET: redirect to `/login` if unauthenticated. Otherwise render `add_expense.html` with the default date filled in.
  - POST: redirect to `/login` if unauthenticated. Otherwise read the form fields, validate them, and call `insert_expense()`. On success, redirect to `url_for("profile")`. On failure, re-render the form with the error and the submitted values.
- `database/queries.py` — add `insert_expense(user_id, amount, category, date, description)`.
- `templates/profile.html` — add the "Add Expense" button.
- `templates/base.html` — add the "Add Expense" navbar link for logged-in users.

## Files to create

- `templates/add_expense.html`
- `tests/test_add_expense.py` — unit and route tests for this step. It reuses the fixtures in `tests/conftest.py` from Step 05.

## New dependencies

- None.

## Rules for implementation

- No SQLAlchemy or ORMs. Use raw `sqlite3` through `get_db()` only.
- Use parameterised queries only. Never string-format values into SQL.
- `PRAGMA foreign_keys = ON` must be enabled on every connection. This is already handled in `get_db()`.
- `insert_expense()` commits its own transaction, closes its connection, and returns the new row's `id`. It does not validate its inputs. The route validates them before calling it.
- `insert_expense()` stores `description` as NULL when it is `None`.
- Validation runs in this order on POST. The first failure stops validation, and the form is re-rendered with that one error:
  1. `amount`: required. Parse with `float()`, catching `ValueError`. It must be finite (reject `nan` and `inf`), greater than 0, and have no more than two decimal places. Store the value rounded to two decimal places.
  2. `category`: required. It must be exactly one of the seven fixed categories. Reject anything else, including values that differ only by letter case.
  3. `date`: required. It must be a valid `YYYY-MM-DD` date, parsed with `datetime.strptime(value, "%Y-%m-%d")`. Dates in the past, today, and the future are all accepted, so users can log scheduled bills and other upcoming expenses. Dates that do not exist on the calendar, such as 2026-02-30, are rejected.
  4. `description`: optional. Strip surrounding whitespace. Store `None` if the result is blank. If it is longer than 200 characters after stripping, reject it with an error.
- Server-side validation applies the same limits as the HTML attributes. The HTML `min`, `required` and `maxlength` attributes are a convenience only.
- Each validation error is shown with a flashed message of category `error`. The form is re-rendered directly with status 200, with no redirect, and the submitted values are kept.
- After a successful insert, redirect to `url_for("profile")`. Do not render the form again.
- Currency must always display as ₹. Never £ or $.
- Use CSS variables. Never hardcode hex values.
- No inline styles.
- All templates extend `base.html`.
- Use `url_for()` for every internal link. Never hardcode paths.

## Tests to write

- Files: `tests/test_add_expense.py`. It reuses the fixtures in `tests/conftest.py` from Step 05: the temporary database, the test client, and the helper for creating a user.
- Log in for route tests by setting `session["user_id"]` through the test client's session transaction.
- Unit tests:

| Function | Input | Expected output |
|---|---|---|
| insert_expense | Valid user_id, amount=50.0, category="Food", date="2026-03-20", description="Lunch" | Row inserted. Querying the database returns the new row with these values, and the function returns its id |
| insert_expense | Valid user_id, amount=50.0, category="Food", date="2026-03-20", description=None | Row inserted with description stored as NULL |

- Route tests:
  - `GET /expenses/add` unauthenticated redirects to `/login` with status 302.
  - `GET /expenses/add` authenticated returns status 200. The response contains a category `<select>` with all seven options, and a form with `method="POST"`.
  - `POST /expenses/add` unauthenticated redirects to `/login` with status 302, and no row is inserted.
  - `POST /expenses/add` authenticated with valid data (amount=50.0, category=Food, date=2026-03-20, description=Lunch) redirects to `/profile` with status 302. A new expense row exists for the test user.
  - `POST /expenses/add` authenticated with a missing amount returns status 200 and an error message.
  - `POST /expenses/add` authenticated with amount=0 returns status 200 and an error message.
  - `POST /expenses/add` authenticated with a non-numeric amount returns status 200 and an error message.
  - `POST /expenses/add` authenticated with amount=10.555 (more than two decimal places) returns status 200 and an error message.
  - `POST /expenses/add` authenticated with a category outside the fixed list returns status 200 and an error message.
  - `POST /expenses/add` authenticated with an invalid date string returns status 200 and an error message.
  - `POST /expenses/add` authenticated with a calendar-impossible date such as 2026-02-30 returns status 200 and an error message.
  - `POST /expenses/add` authenticated with a date later than today (for example one month ahead) redirects to `/profile` with status 302. A row is inserted with that date.
  - `POST /expenses/add` authenticated with a description longer than 200 characters returns status 200 and an error message.
  - `POST /expenses/add` authenticated with no description redirects to `/profile` with status 302. A row is inserted with description NULL.
  - On a failed POST, the response re-populates the submitted amount, date and description, and keeps the submitted category selected.

## Definition of done

- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows a form with amount, category, date, and description fields
- [ ] The date field defaults to today's date
- [ ] The category dropdown contains exactly: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- [ ] Submitting a valid expense redirects to `/profile`, and the new expense appears in the transaction list
- [ ] Submitting with a missing, zero, or non-numeric amount re-renders the form with an error, and the previously entered values are kept
- [ ] Submitting an amount with more than two decimal places re-renders the form with an error
- [ ] Submitting with an invalid category re-renders the form with an error
- [ ] Submitting with an invalid date (malformed, or not a real calendar date) re-renders the form with an error
- [ ] Submitting a future date is accepted and the expense is saved with that date
- [ ] Submitting a description longer than 200 characters re-renders the form with an error
- [ ] Submitting without a description saves the expense with no error and a NULL description
- [ ] The "Add Expense" button on the profile page navigates to `/expenses/add`
- [ ] The navbar shows an "Add Expense" link when logged in, and does not show it when logged out
- [ ] Amounts shown on the profile page after saving display the ₹ symbol
- [ ] The test suite passes and never writes to `spendly.db`
