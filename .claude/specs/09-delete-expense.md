# Delete Expense

## Overview

- This step lets a logged-in user permanently delete one of their own expenses from the profile transaction table.
- A "Delete" button in each row submits a POST request to `/expenses/<id>/delete`.
- The handler verifies ownership, removes the row from the database, and redirects back to `/profile`.
- There is no separate confirmation page. A browser-side `confirm()` dialog in the form's `onsubmit` handler prevents accidental deletions.
- The existing `get_expense_by_id` helper from Step 08 is reused for the ownership check, so no new lookup function is needed.
- Only one new mutation helper is added: `delete_expense` in `database/queries.py`.

## Depends on

- Step 01 — Database setup, implemented in code. The `expenses` table exists and `get_db()` is available.
- Step 03 — Login and Logout, implemented in code. `session["user_id"]` is set on login and enforced by this route.
- Step 05 — Profile page renders live transactions, implemented in code. The delete button lives in this table.
- Step 06 — Date filter for the profile page, implemented in code. The transaction list the delete buttons appear in is filtered by this step.
- Step 08 — Edit Expense, implemented in code. `get_expense_by_id` is available, and the Actions column already exists in the profile transactions table.

## Routes

- `POST /expenses/<int:id>/delete` — verify ownership, delete the expense row, and redirect to `/profile` — logged-in only.
- There is no GET handler. A bare GET to this URL returns 405 Method Not Allowed.
- Unauthenticated POST requests redirect to `/login` with status 302, and nothing is deleted.
- An expense that does not exist, or that belongs to another user, returns 404. The response does not reveal whether the expense exists.

## Database changes

- No new tables or columns.
- The `expenses` table already has all required columns.
- `delete_expense` removes only the single matching row. It does not touch any other table, because no other table references `expenses`.

## Templates

- Modify `templates/profile.html`:
  - Inside the existing "Actions" cell of each transaction row, add a delete form:
    - A `<form>` with `method="POST"` and an action built with `url_for('delete_expense', id=tx.id)`, which resolves to `/expenses/<id>/delete`.
    - `style="display:inline"` on the `<form>` tag. This is the only permitted inline style in the project. It is a layout value, not a design value.
    - `onsubmit="return confirm('Delete this expense?')"` on the `<form>` tag. Returning `false` when the user cancels stops the submission.
    - A `<button type="submit">` with `class="btn-delete"` and the label "Delete".
  - The "Edit" link from Step 08 stays in the same cell, next to the Delete button.

## Files to change

- `database/queries.py`:
  - Add `delete_expense(expense_id, user_id)`:
    - Runs a parameterised `DELETE FROM expenses WHERE id = ? AND user_id = ?`.
    - The `user_id` condition is the ownership guard.
    - Commits and closes its connection before returning.
    - Returns the number of rows deleted, so the caller can tell whether anything was removed.
- `app.py`:
  - Import `delete_expense` from `database.queries`.
  - Replace the GET-only placeholder at `/expenses/<int:id>/delete` with a POST-only handler, declared with `methods=["POST"]`.
  - Redirect to `/login` if the user is not authenticated.
  - Call `get_expense_by_id(id, session["user_id"])`. If it returns `None`, return 404.
  - Call `delete_expense(id, session["user_id"])`. If it reports zero rows deleted, return 404.
  - Redirect to `url_for("profile")`.
- `templates/profile.html` — add the delete form inside the existing Actions cell of each row.
- `static/css/style.css`:
  - Add a `.btn-delete` style to `style.css`. It is a general-purpose destructive button style, so it lives in the global stylesheet and not in `profile.css`.
  - Use the existing `--danger` variable for the text and border colour, and the existing `--danger-light` variable for the hover background. Both are already declared in the `:root` block of `style.css`. Do not add new colour variables and do not write any hex value in the rule.
  - The style gives the button the same size, padding, font and border radius as the "Edit" link next to it, so the two actions line up in the Actions cell.

## Files to create

- `tests/test_delete_expense.py` — unit and route tests for this step. It reuses the fixtures in `tests/conftest.py` from Step 05.

## New dependencies

- None.

## Rules for implementation

- No SQLAlchemy or ORMs. Use raw `sqlite3` through `get_db()` only.
- Use parameterised queries only. Never string-format values into SQL.
- `PRAGMA foreign_keys = ON` must be enabled on every connection. This is already handled in `get_db()`.
- `delete_expense` must scope its DELETE to `id = ? AND user_id = ?`. This is the ownership guard that stops one user deleting another user's expense.
- The route must accept only POST. A bare GET must return 405. Flask returns this automatically when the route is declared with `methods=["POST"]`, so no GET handler is written.
- The login check runs before any lookup, so a logged-out request never reveals whether an expense exists.
- If the session's user no longer exists, the ownership check finds nothing and the route returns 404. It does not raise a server error.
- The route calls `get_expense_by_id` before `delete_expense`. Ownership is checked in the route as well as in the DELETE query.
- If `delete_expense` reports zero rows deleted, return 404. This can only happen if the expense was removed or its owner changed between the check and the delete.
- After successful deletion, redirect to `url_for("profile")`. Do not render a template.
- The redirect lands on the unfiltered profile view, the Step 06 default, so a user deleting from a filtered view loses the filter. This matches Step 08.
- The only permitted inline style is `style="display:inline"` on the `<form>` tag. No hex colours or other design values may be inlined anywhere.
- The `onsubmit` attribute holding the `confirm()` call is the only inline script permitted. It contains no logic beyond returning the confirmation result.
- Use CSS variables. Never hardcode hex values.
- All templates extend `base.html`.
- Currency must always display as ₹. Never £ or $.
- Use `url_for()` for every internal link. Never hardcode paths.
- CSRF protection is deferred to a later step, as in the other specs. This route is the highest-risk endpoint in the app, because a forged POST from another site could delete an expense. CSRF protection should be the first item added when the project reaches it.

## Tests to write

- File: `tests/test_delete_expense.py`. It reuses the fixtures in `tests/conftest.py` from Step 05: the temporary database, the test client, and the helper for creating users and expenses.
- Log in for route tests by setting `session["user_id"]` through the test client's session transaction.
- Create a second user in the fixtures, so the "other user's expense" cases have a real owner to test against.
- Unit tests:

| Function | Input | Expected output |
|---|---|---|
| delete_expense | Valid expense_id, correct user_id | Returns 1. The row is removed from the database |
| delete_expense | Valid expense_id, wrong user_id | Returns 0. The row remains in the database, and no error is raised |
| delete_expense | Non-existent expense_id | Returns 0. No error is raised, and the database is unchanged |

- Route tests:
  - `POST /expenses/<id>/delete` unauthenticated redirects to `/login` with status 302, and the row remains in the database.
  - `POST /expenses/<id>/delete` authenticated, own expense, redirects to `/profile` with status 302. The row no longer exists in the database.
  - `POST /expenses/<id>/delete` authenticated, other user's expense, returns status 404. The row still exists in the database.
  - `POST /expenses/<id>/delete` authenticated, non-existent id, returns status 404.
  - `POST /expenses/<id>/delete` authenticated as a user who no longer exists, returns status 404, not a server error.
  - `GET /expenses/<id>/delete` for any user, logged in or not, returns status 405 (Method Not Allowed).
  - `GET /profile` renders a delete form for each transaction row, with `method="POST"` and the correct action URL, and with the `confirm()` call in its `onsubmit` attribute.

## Definition of done

- [ ] POST to `/expenses/<id>/delete` while logged out redirects to `/login`
- [ ] POST to `/expenses/<id>/delete` for a non-existent expense returns 404
- [ ] POST to `/expenses/<id>/delete` for another user's expense returns 404, and the row is unchanged
- [ ] GET to `/expenses/<id>/delete` returns 405
- [ ] Clicking "Delete" on a transaction row and confirming in the browser dialog removes that expense from the database
- [ ] After deletion, the user is redirected to `/profile`, and the deleted expense no longer appears in the transaction list
- [ ] Cancelling the browser `confirm()` dialog does not submit the form, and the expense is left intact
- [ ] Each transaction row in the profile table shows both "Edit" and "Delete" actions
- [ ] The only inline style on the page is `style="display:inline"` on the delete forms
- [ ] The `.btn-delete` colour comes from a CSS variable, not a hex value
- [ ] The profile date filter still works with the delete buttons present
- [ ] The test suite passes and never writes to `spendly.db`
