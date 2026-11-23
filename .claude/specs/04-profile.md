# 04 — Profile Page

## Overview

- This step replaces the `/profile` stub with a fully designed profile page that shows static, hardcoded data.
- The goal is to establish the complete UI layout before any real database queries are wired up in Step 05.
- The page has four sections:
  - A user info card.
  - A summary stats row.
  - A transaction history table.
  - A category breakdown.
- This step also makes the navbar reflect the logged-in state, because the page is only reachable when signed in.
- Building the UI first lets the design be validated in isolation and makes the templates ready for the backend-connection step.

## Depends on

- Step 01 — Database Setup, implemented in code. The schema must exist.
- Step 02 — Registration, implemented in code. User accounts must be creatable.
- Step 03 — Login and Logout, implemented in code. The session must be set, `/logout` must work, and `/profile` must be a protected route.

## Routes

- `GET /profile` — render the profile page — logged-in only. Redirect to `/login` if the user is not authenticated.

## Database changes

- No database changes.
- The existing `users` and `expenses` tables are sufficient.
- No database queries in this step. All data is hardcoded.

## Templates

- Create `templates/profile.html` as a full profile page that extends `base.html`. It links `static/css/profile.css` through the `head` block.
- The page must contain four sections, in this order:
  1. User info card: avatar initials, name, email, and member-since date, all hardcoded. The initials are derived from the hardcoded name in `app.py` (the first letter of the first and last words).
  2. Summary stats row: total spent, number of transactions, and top category.
  3. Transaction history table: recent expenses showing date, description, category badge, and amount. At least three hardcoded rows.
  4. Category breakdown: per-category totals shown as rows with a name, an amount, and a native `<progress>` element whose `value` and `max` attributes carry the percentage. At least three hardcoded categories.
- Display formats:
  - Currency: the ₹ symbol, two decimal places, and commas as thousands separators, for example ₹1,234.50.
  - Transaction dates: day, abbreviated month, and year, for example 14 Mar 2026.
  - Member-since: month name and year, for example March 2026.
- Modify `templates/base.html` so the navbar reflects the logged-in state:
  - Logged in: show the user's name, a Profile link, and a Logout link, all generated with `url_for`. Hide "Sign in" and "Get started".
  - Guest: keep "Sign in" and "Get started" as they are.
  - The footer, including the Terms and Privacy links, is unchanged.

## Files to change

- `app.py`:
  - Replace the `/profile` stub with a real view function that redirects unauthenticated users to `/login` and passes hardcoded context variables to `profile.html`: a user dict, a stats dict, an expenses list, and a category breakdown list.
  - Register a context processor that supplies the navbar user. In this step it returns the hardcoded user's name when `session["user_id"]` is present, and nothing otherwise. Step 05 replaces the hardcoded name with a database lookup.
- `templates/base.html` — logged-in navbar state, as described in the Templates section.

## Files to create

- `templates/profile.html`
- `static/css/profile.css` — all profile page styles, including the filter bar added in Step 06.

## New dependencies

- None.

## Rules for implementation

- No SQLAlchemy or ORMs. Use raw `sqlite3` via `get_db()` if a database call is ever needed.
- Use parameterised queries only. Never string-format SQL.
- Authentication guard: check `session.get("user_id")`. If it is absent, call `redirect(url_for("login"))`.
- All data passed to the template must be hardcoded Python dicts and lists in `app.py`. No database queries in this step.
- The hardcoded data must be internally consistent. Define one hardcoded expense list, and derive the stats and the category breakdown from it in Python, so that total spent, transaction count, top category, and the breakdown amounts all agree with the table rows.
- Use CSS variables. Never hardcode hex values in `profile.html` or in rules in `profile.css`. The per-category colour variables are declared once in a `:root` block at the top of `profile.css`, and every rule uses those variables.
- No inline styles anywhere in `profile.html`. Progress bars use the native `<progress>` element, not a width style.
- All templates must extend `base.html`.
- Category badges must use a CSS class per category (for example a shared badge class plus a category modifier class), not inline colour styles.
- Use `url_for()` for every internal link. Never hardcode paths.

## Definition of done

- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The page displays a user info card with initials, a name, an email, and a member-since date
- [ ] The page displays at least three summary stat values (for example total spent, transaction count, and top category)
- [ ] The page displays a transaction history table with at least three hardcoded rows
- [ ] The page displays a category breakdown section with at least three categories, each with a progress bar
- [ ] The stats and breakdown agree with the table rows (same total, same count, same top category)
- [ ] When logged in, the navbar shows the user's name, a Profile link, and a Logout link
- [ ] When logged out, the navbar still shows "Sign in" and "Get started"
- [ ] No hex colour values appear in `profile.html`, and none appear in `profile.css` outside the `:root` variable block
- [ ] No inline styles appear in `profile.html`
