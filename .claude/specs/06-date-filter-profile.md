# 06 — Date Filter for Profile Page

## Overview

- This step adds a date-range filter to the existing `/profile` route, so users can narrow the transaction list, summary stats, and category breakdown to a specific period.
- The filter is driven entirely by query-string parameters `date_from` and `date_to` on `GET /profile`. No new routes are required.
- A compact filter bar contains four quick-select preset buttons: "This Month", "Last 3 Months", "Last 6 Months", and "All Time". It also contains two `<input type="date">` fields that let users pick any custom range.
- All three data sections (summary stats, recent transactions, and category breakdown) must respect the active date filter.

## Depends on

- Step 01 — Database setup, implemented in code. The `expenses` table, with its `date` column, must exist.
- Step 04 — Profile page UI, implemented in code. The template with all four sections and `static/css/profile.css` must exist.
- Step 05 — Backend connection, implemented in code. `get_summary_stats`, `get_recent_transactions`, and `get_category_breakdown` in `database/queries.py` must exist and be wired to the `/profile` route.

## Routes

- No new routes.
- The existing `GET /profile` route is modified to read two optional query parameters:
  - `date_from` — an ISO date string in `YYYY-MM-DD` format. This is the inclusive lower bound.
  - `date_to` — an ISO date string in `YYYY-MM-DD` format. This is the inclusive upper bound.
- A filter applies only when both parameters are present and valid. If either parameter is absent, blank, or malformed, the route falls back to the unfiltered "All Time" view. A single date on its own is treated as absent, so a half-set range is never applied. The route never returns an error.

## Database changes

- No database changes.
- The `expenses.date` column (TEXT, `YYYY-MM-DD`) already supports `BETWEEN` comparison in SQLite.

## Templates

- Modify `templates/profile.html`:
  - Display flashed messages at the top of the page, above the filter bar, so the "Start date must be before end date." message is visible.
  - Add a filter bar section above the summary stats row. It contains:
    - Four quick-select preset buttons: "This Month", "Last 3 Months", "Last 6 Months", and "All Time".
      - Each preset is a link to `/profile` with the `date_from` and `date_to` query parameters computed in `app.py`.
      - "All Time" passes no query parameters, so the URL is a clean `/profile`.
    - A custom range sub-form with two `<input type="date">` fields, `date_from` and `date_to`, both marked `required`, and an "Apply" submit button. The fields show the currently applied dates when a filter is active.
    - An active state on the button or custom-range fields that is currently applied, so the user can see which filter is active. The rules for choosing it are in the implementation rules below.
  - No structural changes to any existing section. Only the Jinja variables fed into them change when a filter is active.

## Files to change

- `app.py`:
  - In the `profile()` view, read `date_from` and `date_to` from `request.args`.
  - Validate both values as well-formed ISO dates using `datetime.strptime(value, "%Y-%m-%d")`. On `ValueError`, or when the value is blank, treat the value as absent.
  - If only one of the two values is valid, treat both as absent, with no flash message.
  - If `date_from` is later than `date_to` after validation, treat both as absent and flash "Start date must be before end date." with category `error`. Render the page directly, with no redirect.
  - Compute the preset date ranges in `app.py`. Never compute them in the template. Use one small helper that returns today's date, so tests can substitute a fixed date.
  - Compute which control is active and pass it to the template, along with the validated `date_from`, `date_to`, and the preset URL parameters.
  - Pass `date_from` and `date_to` to each of the three query helpers.
- `database/queries.py`:
  - `get_summary_stats(user_id, date_from=None, date_to=None)`:
    - When both parameters are provided, add `AND date BETWEEN ? AND ?` to the expenses queries.
    - When they are absent, behave exactly as in Step 05 (unfiltered).
  - `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)`:
    - Use the same pattern. Newest-first ordering and the limit stay unchanged.
  - `get_category_breakdown(user_id, date_from=None, date_to=None)`:
    - Use the same pattern. The percentage recalculation logic stays unchanged.
- `templates/profile.html`: add the filter bar and the flash display, as described in the Templates section.
- `static/css/profile.css`: add styles for the filter bar and the active-preset button state. Use CSS variables only.

## Files to create

- None. `static/css/profile.css` is created in Step 04.

## New dependencies

- None.

## Rules for implementation

- No SQLAlchemy or ORMs. Use raw `sqlite3` through `get_db()` only.
- Use parameterised queries only. Never string-format dates into SQL. Use `?` placeholders for date-range bounds too.
- Validate dates in `app.py` with `datetime.strptime(value, "%Y-%m-%d")`. On `ValueError`, treat the parameter as absent and fall back to no filter.
- "Today" is the server's local date, taken from a single helper in `app.py`.
- Preset ranges all end today (inclusive) and are defined as follows:
  - "This Month": from the first day of the current month through today.
  - "Last 3 Months": from the same day of the month three months ago through today. If that day does not exist in that month, use the last day of that month.
  - "Last 6 Months": from the same day of the month six months ago through today, with the same rule for missing days.
  - "All Time": no date parameters.
- Generate preset links with `url_for("profile", date_from=..., date_to=...)`. Never hardcode URL strings in the template.
- When `date_from` and `date_to` are both absent, all three query helpers must behave identically to their Step 05 behaviour (unfiltered).
- If `date_from` is later than `date_to` after validation, treat both as absent and flash "Start date must be before end date."
- A filter that has only one valid date is treated as no filter, without a flash message.
- The "All Time" preset must pass no query parameters, so the URL is a clean `/profile`.
- Compute preset date ranges in `app.py`, not in the template.
- Active state: when the applied range exactly equals a preset's computed range, highlight that preset. When no parameters are applied, highlight "All Time". When a valid range is applied that matches no preset, highlight the custom range form and show its dates in the fields. Never highlight more than one preset at a time, and the preset match wins over the custom range.
- Use CSS variables. Never hardcode hex values.
- No inline styles.
- All templates extend `base.html`.
- Use `url_for()` for every internal link. Never hardcode paths.

## Definition of done

- [ ] Visiting `/profile` with no query parameters returns the same data as Step 05 (unfiltered, all expenses)
- [ ] Clicking "This Month" filters all three sections to the first day of the current month through today
- [ ] Clicking "Last 3 Months" filters to expenses from the same day three months ago through today, with missing days clamped to the end of that month
- [ ] Clicking "Last 6 Months" filters to expenses from the same day six months ago through today, with missing days clamped to the end of that month
- [ ] Clicking "All Time" removes any active filter and shows all expenses
- [ ] Submitting a custom date range with valid `date_from` and `date_to` shows only expenses within that range in all three sections
- [ ] Submitting a range where `date_from` is later than `date_to` shows the flash error and falls back to the unfiltered view
- [ ] Submitting a malformed date string (for example `date_from=not-a-date`) does not crash the app and silently falls back to the unfiltered view
- [ ] Visiting `/profile` with only `date_from` or only `date_to` shows the unfiltered view with no error
- [ ] Both custom-range inputs are marked `required`, so the form cannot be submitted with a blank date
- [ ] Exactly one control is highlighted: the matching preset, or the custom range when it matches no preset, or "All Time" when no filter is applied
- [ ] All amounts continue to display the ₹ symbol regardless of the active filter
- [ ] A user with no expenses in the selected range sees ₹0.00 total spent, 0 transactions, and an empty category breakdown, with no errors
