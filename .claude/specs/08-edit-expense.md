# Edit Expense

## Overview

- This step lets a logged-in user edit any of their own expenses through a pre-populated form at `/expenses/<id>/edit`.
- The GET handler loads the existing expense from the database and renders the form with its current values.
- The POST handler validates the submission and updates the row in place.
- Ownership is enforced: a user can only view or edit expenses that belong to them. Any other expense returns 404.
- Two new query helpers are added to `database/queries.py`: `get_expense_by_id` and `update_expense`.
- The transactions table in `profile.html` gains an "Edit" action link per row. This requires `get_recent_transactions` to also return each expense's id.

## Depends on

- Step 01 — Database setup, implemented in code. The `expenses` table exists with all required columns, and `get_db()` is available.
- Step 03 — Login and Logout, implemented in code. `session["user_id"]` is set on login and enforced by this route.
- Step 05 — Profile page renders live transactions, implemented in code. The edit link lives in this table.
- Step 06 — Date filter for the profile page, implemented in code. The transaction list the edit links appear in is filtered by this step, and the filter must keep working with the new `id` field.
- Step 07 — Add Expense, implemented in code. This step reuses its form pattern and its validation rules.

## Routes

- `GET /expenses/<int:id>/edit` — render the edit form pre-populated with the expense's current values — logged-in only.
- `POST /expenses/<int:id>/edit` — validate the submitted data and save the changes — logged-in only.
- Unauthenticated requests to either method redirect to `/login` with status 302. A POST from a logged-out user is discarded and changes nothing.
- An expense that does not exist, or that belongs to another user, returns 404 for both methods. The response does not reveal whether the expense exists.

## Database changes

- No new tables or columns.
- All required columns already exist in `expenses`: `id`, `user_id`, `amount`, `category`, `date`, and `description`.
- `update_expense` does not change `user_id` or `created_at`.

## Templates

- Create `templates/edit_expense.html`:
  - Extends `base.html`.
  - Contains a form with `method="POST"` and an action built with `url_for('edit_expense', id=expense.id)`, which resolves to `/expenses/<id>/edit`.
  - Uses the same four fields as `add_expense.html`, all pre-filled with the expense's current values:
    - `amount` — number input, `step="0.01"`, `min="0.01"`, `required`.
    - `category` — a `<select>` with exactly seven options, in this order: Food, Transport, Bills, Health, Entertainment, Shopping, Other. The option matching the current category is pre-selected.
    - `date` — `<input type="date">`, `required`.
    - `description` — text input, optional, `maxlength="200"`. An empty description shows as an empty field.
  - A submit button labelled "Save Changes" and a cancel link back to `/profile`, generated with `url_for('profile')`.
  - A block that displays flashed error messages.
  - On a failed submission, every field is re-populated with the submitted values, not the original values. The selected category is the submitted one.
- Modify `templates/profile.html`:
  - Add an "Actions" column header (`<th>`) to the transactions table header.
  - Add an "Edit" link cell to each transaction row, pointing to `url_for('edit_expense', id=tx.id)`.
  - Keep the Step 06 filter bar and the Step 05 summary stats unchanged.

## Files to change

- `database/queries.py`:
  - Add `get_expense_by_id(expense_id, user_id)`:
    - Selects one expense with `WHERE id = ? AND user_id = ?`.
    - Returns the row as a dict-like object, or `None` if the expense is missing or belongs to another user.
  - Add `update_expense(expense_id, user_id, amount, category, date, description)`:
    - Runs a parameterised `UPDATE expenses ... WHERE id = ? AND user_id = ?`.
    - Commits its own transaction and closes its connection.
    - Returns the number of rows changed, so the caller can tell whether anything was updated.
  - Modify `get_recent_transactions`:
    - Add `id` to the SELECT column list, so each transaction dict carries its expense id.
    - Keep its existing ordering, limit, and Step 06 date-filter parameters unchanged.
- `app.py`:
  - Import `get_expense_by_id` and `update_expense` from `database.queries`.
  - Replace the GET-only placeholder at `/expenses/<int:id>/edit` with a full handler. Declare it with `methods=["GET", "POST"]`.
  - GET: redirect to `/login` if unauthenticated. Call `get_expense_by_id`. If it returns `None`, return 404. Otherwise render `edit_expense.html` with the expense and the list of categories.
  - POST: redirect to `/login` if unauthenticated. Call `get_expense_by_id` first, and return 404 if it returns `None`. Otherwise read and validate the form fields, then call `update_expense`. On success, redirect to `url_for("profile")`. On failure, re-render the form with the error and the submitted values.
- `templates/profile.html`:
  - Add `<th>Actions</th>` to the table header.
  - Add an "Edit" link cell to each transaction row.

## Files to create

- `templates/edit_expense.html`
- `tests/test_edit_expense.py` — unit and route tests for this step. It reuses the fixtures in `tests/conftest.py` from Step 05.

## New dependencies

- None.

## Rules for implementation

- No SQLAlchemy or ORMs. Use raw `sqlite3` through `get_db()` only.
- Use parameterised queries only. Never string-format values into SQL.
- `PRAGMA foreign_keys = ON` must be enabled on every connection. This is already handled in `get_db()`.
- `get_expense_by_id` must scope its query to `id = ? AND user_id = ?`. It returns `None` if the expense is not found or the ownership check fails.
- `update_expense` must include `user_id = ?` in its WHERE clause as a second ownership guard, in addition to the check in the route.
- The route calls `get_expense_by_id` before any update. Ownership is checked in the route as well as in the query.
- If the session's user no longer exists, the ownership check finds nothing, so the route returns 404. It does not raise a server error.
- Unauthenticated access to both GET and POST must redirect to `/login`. The check runs before the expense is loaded, so the response for a logged-out request never reveals whether an expense exists.
- If the expense does not exist or belongs to another user, return 404 for both GET and POST.
- Validation rules for POST are identical to Step 07. The first failure stops validation, and the form is re-rendered with that one error:
  1. `amount`: required. Parse with `float()`, catching `ValueError`. It must be finite (reject `nan` and `inf`), greater than 0, and have no more than two decimal places. Store the value rounded to two decimal places.
  2. `category`: required. It must be exactly one of the seven fixed categories. Reject anything else, including values that differ only by letter case.
  3. `date`: required. It must be a valid `YYYY-MM-DD` date, parsed with `datetime.strptime(value, "%Y-%m-%d")`. Past, present and future dates are accepted. Dates that do not exist on the calendar, such as 2026-02-30, are rejected.
  4. `description`: optional. Strip surrounding whitespace. Store `None` if the result is blank. If it is longer than 200 characters after stripping, reject it with an error.
- Server-side validation applies the same limits as the HTML attributes. The HTML `min`, `required` and `maxlength` attributes are a convenience only.
- Each validation error is shown with a flashed message of category `error`. The form is re-rendered directly with status 200, with no redirect. The form shows the submitted values, not the original values.
- After a successful update, redirect to `url_for("profile")`. Do not render the form again.
- The redirect after a successful save lands on the profile page with the current filter reset to the unfiltered view, which is the Step 06 default.
- If `update_expense` reports zero rows changed, return 404. This can only happen if the expense was removed or its owner changed between the check and the update.
- Currency must always display as ₹. Never £ or $.
- Use CSS variables. Never hardcode hex values.
- No inline styles.
- All templates extend `base.html`.
- Use `url_for()` for every internal link. Never hardcode paths.

## Tests to write

- Files: `tests/test_edit_expense.py`. It reuses the fixtures in `tests/conftest.py` from Step 05: the temporary database, the test client, and the helper for creating users and expenses.
- Log in for route tests by setting `session["user_id"]` through the test client's session transaction.
- Create a second user in the fixtures, so the "other user's expense" cases have a real owner to test against.
- Unit tests:

| Function | Input | Expected output |
|---|---|---|
| get_expense_by_id | Valid expense_id, correct user_id | The matching row, as a dict-like object with its fields |
| get_expense_by_id | Valid expense_id, wrong user_id | None |
| get_expense_by_id | Non-existent expense_id | None |
| update_expense | Valid expense_id, correct user_id, amount=99.0 | Returns 1. The row in the database shows amount 99.0 |
| update_expense | Valid expense_id, wrong user_id | Returns 0. The row in the database is unchanged, and no error is raised |
| get_recent_transactions | User with expenses | Each returned item includes an `id` key matching the expense |

- Route tests:
  - `GET /expenses/<id>/edit` unauthenticated redirects to `/login` with status 302.
  - `GET /expenses/<id>/edit` authenticated, own expense, returns status 200. The response contains the form pre-filled with the current amount, date and description, and the `<select>` has the correct category pre-selected.
  - `GET /expenses/<id>/edit` authenticated, other user's expense, returns status 404.
  - `GET /expenses/<id>/edit` authenticated, non-existent id, returns status 404.
  - `POST /expenses/<id>/edit` unauthenticated redirects to `/login` with status 302, and the row is unchanged.
  - `POST /expenses/<id>/edit` authenticated, valid data (for example amount=99.0), redirects to `/profile` with status 302. The database shows the updated values.
  - `POST /expenses/<id>/edit` authenticated, other user's expense, returns status 404, and the row is unchanged.
  - `POST /expenses/<id>/edit` authenticated, missing amount, returns status 200 and an error message. The database row is unchanged.
  - `POST /expenses/<id>/edit` authenticated, amount=0, returns status 200 and an error message.
  - `POST /expenses/<id>/edit` authenticated, non-numeric amount, returns status 200 and an error message.
  - `POST /expenses/<id>/edit` authenticated, amount=10.555 (more than two decimal places), returns status 200 and an error message.
  - `POST /expenses/<id>/edit` authenticated, category outside the fixed list, returns status 200 and an error message.
  - `POST /expenses/<id>/edit` authenticated, invalid date string, returns status 200 and an error message.
  - `POST /expenses/<id>/edit` authenticated, calendar-impossible date such as 2026-02-30, returns status 200 and an error message.
  - `POST /expenses/<id>/edit` authenticated, no description, redirects to `/profile` with status 302. The row is updated with description NULL.
  - On a failed POST, the response shows the submitted values, not the original ones, and keeps the submitted category selected.
  - `GET /profile` shows an "Edit" link for each transaction row, pointing to that expense's edit URL.

## Definition of done

- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for a non-existent expense returns 404
- [ ] Visiting `/expenses/<id>/edit` for another user's expense returns 404
- [ ] Visiting `/expenses/<id>/edit` while logged in shows a form pre-filled with the expense's current values
- [ ] The category dropdown has the correct category pre-selected
- [ ] Submitting valid changes redirects to `/profile`, and the updated values appear in the transaction list
- [ ] Submitting with a missing, zero, or non-numeric amount re-renders the form with an error, and the submitted values are kept
- [ ] Submitting an amount with more than two decimal places re-renders the form with an error
- [ ] Submitting with an invalid category re-renders the form with an error
- [ ] Submitting with an invalid or calendar-impossible date re-renders the form with an error
- [ ] Submitting a future date is accepted and saved
- [ ] Submitting without a description saves the expense with no error and a NULL description
- [ ] A POST to another user's expense changes nothing in the database
- [ ] A session whose user no longer exists gets 404, not a server error
- [ ] Each row in the profile transaction table has an "Edit" link pointing to the correct URL
- [ ] The profile date filter still works with the new `id` field present
- [ ] The test suite passes and never writes to `spendly.db`
