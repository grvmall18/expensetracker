# Report: `.claude/plans/05-backend-routes-for-profile-page.md` vs `.claude/specs/05-backend-routes-for-profile-page.md`

**Overall status: 🟡 Amber.** The plan covers every functional requirement in the spec, and the implementation followed it. Two items keep it from Green: the spec's "three parallel subagents" line is neither followed nor mentioned in the plan, and the plan replaces `pytest-flask` with plain pytest fixtures. One verification step was also only partly run when the plan was executed, and I have now run it.

## Status by spec section

| Spec section | Status | Notes |
|---|---|---|
| Overview | 🟡 Amber | Live data, per-user data and the navbar lookup are covered. The subagent line is not (see issue 1). |
| Depends on | 🟢 Green | Steps 01 to 04 are stated as implemented, and the real database was checked read-only |
| Routes | 🟢 Green | `/profile` is modified in place, and a deleted user's session is cleared and redirected |
| Database changes | 🟢 Green | None |
| Templates | 🟢 Green | `inr` filter on every amount, no structural change, and the empty state without placeholder text |
| Files to change | 🟢 Green | `app.py` and `profile.html`, with two small extra edits in `profile.html` (below) |
| Files to create | 🟢 Green | `queries.py`, `conftest.py` and `test_backend_connection.py` |
| New dependencies | 🟡 Amber | The spec says `pytest` and `pytest-flask` are already available. `pytest-flask` is not installed here, so the plan does not use it (see issue 2). |
| Rules for implementation | 🟢 Green | All 15 rules covered (below) |
| Tests to write | 🟢 Green | All 10 unit rows and all route cases from the spec are covered, plus extras |
| Definition of done | 🟢 Green | All 11 items map to a verification step |

### Rules, one by one

| Spec rule | In the plan? |
|---|---|
| Raw sqlite3, parameterised queries only | 🟢 Yes, and a source check confirms no f-string SQL |
| Foreign keys on every connection | 🟢 Yes, through `get_db()` |
| ₹ only, formatting in the template, helpers return raw numbers | 🟢 Yes |
| Round `total_spent` and every amount to two decimals | 🟢 Yes, in Python and with `ROUND` in SQL |
| `member_since` as "Month YYYY" from `created_at` | 🟢 Yes |
| Order transactions by date then id, newest first | 🟢 Yes |
| Top category tie goes to the first alphabetically | 🟢 Yes, through the SQL ordering |
| Percentages sum to 100, largest absorbs the remainder | 🟢 Yes, and an empty list avoids dividing by zero |
| No expenses gives zeros, "—" and empty lists, never an exception | 🟢 Yes |
| Helpers call `get_db()` and close the connection | 🟢 Yes, with `finally` blocks |
| Tests never touch the real `spendly.db` | 🟢 Yes, with a modification-time check |
| CSS variables, no inline styles, templates extend `base.html` | 🟢 Yes. No CSS changes were needed. |

## Decisions the plan added (not in the spec)

All 🟢 Green, because none contradict the spec:
- The percentage logic lives in `queries.py`, and the old hardcoded helpers and the unused `month_year` filter were removed.
- A blank description renders as empty text, not the word "None".
- The navbar lookup reads the user but does not clear the session.
- `conftest.py` sets the database path before `app` is imported, because importing the app seeds a database.
- Extra tests: member-since format, a tie for top category, float rounding, the limit, a NULL description, users seeing only their own expenses, the navbar name, and that the tests never use the real database.

## 🟡 Issues

1. **The "three parallel subagents" line is not followed or mentioned.** The spec's Overview says three subagents handle the three data concerns and the results are integrated into the route. The plan is silent on this, and the work was done directly, one helper at a time. The line describes how to build the step, not what the code does, so the result is the same, but the plan should have said it chose not to.
2. **`pytest-flask` is replaced by plain pytest fixtures.** The spec says it is available. It is listed in `requirements.txt` but not installed here. The plan flags this, and the tests need only a test client. But the fixtures were never tried with `pytest-flask` installed, so whether its own `app` and `client` fixtures would conflict with the ones in `conftest.py` is unknown.
3. **One verification step was only partly run.** Plan step 2 says to confirm that no `spendly.db` appears when the tests run from a different directory. When the step was first carried out, the suite ran only from the project root. I have now run it from another directory: all 26 tests pass, no `spendly.db` appears there, and the real database keeps the same modification time and size.

## 🟢 Checks that passed

- Every functional requirement in the spec appears in the plan, and nothing in the plan contradicts it.
- All 26 tests pass from the project root and from another directory. The real `spendly.db` is not written to.
- Checks against a copy of the real data pass: the demo user sees ₹346.24, 8 transactions, Bills, and 7 categories summing to 100%. A new user sees ₹0.00 and 0 transactions and none of the demo user's expenses.

## Not covered by either document

- **Step 08 will need expense ids.** `get_recent_transactions` returns no `id`. Step 08's spec already says to add it.
- **Registration quirks:** a newly registered user's profile shows a table header with no rows and no explanatory text. That follows the spec but may look unfinished.
- **Version mismatch:** `requirements.txt` pins `pytest` 8.3.5, but 8.4.2 is installed.

## Recommended fixes

- Add a sentence to the plan saying why the work didn't use subagents.
- Decide whether to install `pytest-flask`, and if so run the suite once with it present.
- Optionally add a one-line empty-state message for new users, which would need a small CSS rule.
