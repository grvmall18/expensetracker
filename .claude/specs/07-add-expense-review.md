# Report: `.claude/plans/07-add-expense.md` vs `.claude/specs/07-add-expense.md`

**Overall status: 🟡 Amber.** The plan covers every requirement in the spec, and the implementation followed it. It is Amber for two reasons: the plan changes three files that the spec's "Files to change" list doesn't name (all declared in the plan), and the plan's regression step ended with two stale failures in my own scratch scripts.

## Status by spec section

| Spec section | Status | Notes |
|---|---|---|
| Overview | 🟢 Green | The form page, the GET and POST handler, the insert helper and both "Add Expense" links |
| Depends on | 🟢 Green | The plan states Steps 01 to 06 are implemented, covering the spec's four dependencies |
| Routes | 🟢 Green | GET and POST, logged-in only, logged-out requests redirected, and a logged-out POST saves nothing |
| Database changes | 🟢 Green | None. The plan confirmed `description` is the only nullable field. |
| Templates | 🟢 Green | All fields, the seven-option select, the date default, the Save and Cancel controls, the flash block, re-filled values, the profile button and the navbar link |
| Files to change | 🟡 Amber | The spec's four files match. Three more are changed (see issue 1). |
| Files to create | 🟢 Green | `add_expense.html` and `tests/test_add_expense.py` |
| New dependencies | 🟢 Green | None. `math` is standard library. |
| Rules for implementation | 🟢 Green | All rules covered, with the navbar condition as a declared difference |
| Tests to write | 🟢 Green | Both unit rows and all 14 route cases are covered, plus extras |
| Definition of done | 🟢 Green | All 16 items map to a verification step or a test |

### Rules, one by one

| Spec rule | In the plan? |
|---|---|
| Raw sqlite3, parameterised, foreign keys on | 🟢 Yes, and a source check confirms five bound values |
| `insert_expense` commits, closes, returns the id, does not validate | 🟢 Yes |
| `None` description stored as NULL | 🟢 Yes |
| Validation order: amount, category, date, description, first failure stops | 🟢 Yes, with a test that only the first error shows |
| Amount: `float()`, finite, above zero, two decimals at most, rounded | 🟢 Yes |
| Category exactly one of the seven, case-sensitive | 🟢 Yes |
| Date parsed with `strptime`, past, present and future accepted, impossible dates rejected | 🟢 Yes, through the Step 06 helper |
| Description trimmed, blank becomes NULL, over 200 rejected | 🟢 Yes |
| Errors flashed as `error`, status 200, no redirect, values kept | 🟢 Yes |
| Redirect to the profile page after saving | 🟢 Yes |
| ₹ only, CSS variables, no inline styles, templates extend `base.html`, `url_for` links | 🟢 Yes, with source checks |

## 🟢 Decisions the plan added (not in the spec)

None contradict the spec:
- A session for a deleted user is redirected to `/login` instead of causing a server error. This closes a gap I raised when reviewing the spec.
- The categories are defined once in `database/db.py` and imported by `app.py`.
- The navbar link uses `nav_user`, like the other signed-in links, so a stale session shows no link. The spec says `session.user_id`.
- Dates are stored in ISO form, so `2026-3-5` is saved as `2026-03-05`.
- No success message after saving, as the spec doesn't ask for one.
- The form's `method` is written in lower case. HTML treats it the same as `POST`.

## 🟡 Issues

1. **Three files are changed that the spec doesn't list.** `database/db.py` (the shared `CATEGORIES` list), `static/css/profile.css` (styles for the new button and heading row) and `tests/conftest.py` (a `fixed_today` fixture so the default date and "future" tests are deterministic). The plan declares all three. None is hard to justify, but the spec's file list should be updated to match.
2. **Plan verification step 5 did not end clean.** It says to rerun the earlier steps' scratch checks. Two of them failed afterwards: one counted exactly four helpers closing their connection (there are now five), and one expected `get_today()` to be called once (the form now calls it too). Both are stale assertions in scratch scripts, not regressions in the app, but the step was not green.
3. **The date helper trims spaces.** The Step 06 helper, reused here, also accepts a date with surrounding spaces. The spec says to parse with `strptime`, which would reject that. A browser date input never sends spaces, so the effect is tiny.

## 🟢 Checks that passed

- Every spec requirement appears in the plan, and nothing in the plan contradicts the spec.
- All 66 tests pass (26 existing, 40 new), from the project root and from another directory. The real `spendly.db` is not written to.
- End to end on a copy of your database: a ₹12.50 expense appeared on the profile page, the total moved from ₹346.24 to ₹358.74, and invalid submissions added nothing.

## Not covered by either document

- **Double submission:** nothing stops a double-click on "Save Expense" from saving the same expense twice.
- **Amount limit:** there is no maximum, so a very large number is accepted.
- **CSRF:** the form has no token, as in the other steps.
- **Narrow screens:** the navbar link is hidden by the existing mobile rule. The profile page's button is the only route to the form on a phone.
- **Profile table limit:** only the 10 newest expenses show, so an old-dated expense is saved but may not appear in the table.

## Recommended fixes

- Add the three extra files to the spec's "Files to change", or note them in the plan as deliberate additions.
- Update the two stale assertions in the scratch scripts, or ignore them.
- Optionally guard against double submission, for example by disabling the button after the first click.
