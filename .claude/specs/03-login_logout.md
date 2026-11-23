# 03 — Login and Logout

## Overview

- This step converts the `/login` stub into a functional GET and POST handler.
  - The POST handler verifies the submitted credentials against the `users` table.
  - On success, it stores the authenticated user's id in `session["user_id"]`.
  - On success, it redirects to the landing page until a dashboard route exists.
- This step also implements `/logout`, which clears the session and redirects to `/`.
- After this step, the app can tell logged-in users apart from guests.
- Current state: `login.html` already has a form posting to a hard-coded `/login` and shows errors through a single `error` variable. This step rewires that form, so it is not built from scratch.
- This is a prerequisite for all expense features.

## Depends on

- Step 01 — Database Setup, implemented in code. The `users` table must exist.
- Step 02 — Registration, implemented in code. `create_user()`, password hashing, and `app.secret_key` must be in place, and a user must exist to log in against. Sessions and `flash()` do not work without the secret key.

## Routes

- `GET /login` — render the login form — public. A user who is already logged in is redirected to `url_for("landing")`.
- `POST /login` — validate credentials, set the session, and redirect — public.
- `GET /logout` — clear the session and redirect to `/` — public, no login required.

## Database changes

- No database schema changes.
- The `users` table from Step 01 already stores `email` and `password_hash`.
- Add one new DB helper to `database/db.py`: `get_user_by_email(email)`.
  - Queries the `users` table by email.
  - Returns the matching user row, or `None` if no user matches.
  - Lives in `database/db.py`, not inline in the route.

## Templates

- Modify `templates/login.html`:
  - Rewire the existing form: set the form action to `url_for('login')` and `method="post"`, with `email` and `password` fields.
  - Replace the single `error` variable block with a block that displays all flashed messages of any category. This includes the success message from registration and the error message from a failed login.
  - Keep the link to `/register` for new users, generated with `url_for`.

## Files to change

- `app.py` — implement `login()` as a GET and POST handler, and implement `logout()`.
- `database/db.py` — add the `get_user_by_email()` helper.
- `templates/login.html` — rewire the form and flash display.

## Files to create

- None.

## New dependencies

- None.
- Uses `werkzeug.security.check_password_hash`, which is already available.

## Rules for implementation

- No SQLAlchemy or ORMs. Use raw `sqlite3` through `get_db()`.
- Use parameterised queries only. Never use f-strings in SQL.
- Verify passwords with `werkzeug.security.check_password_hash`.
- Trim whitespace from the submitted email and convert it to lowercase before the lookup. Do not trim the password.
- The session key for the logged-in user must be `session["user_id"]`, stored as an integer.
- Use `flask.session`. Do not build a custom session mechanism.
- On successful login, call `session.clear()` first, then set `session["user_id"]`, so no data from an earlier session carries over.
- On a failed login, flash the generic error `"Invalid email or password."` with category `error`, re-render the login page with HTTP status 200, and do not redirect. Do not reveal which field was wrong.
- An empty email or password counts as a failed login and gets the same generic error.
- When the email is not found, still run a password check against a dummy hash, so the response time does not reveal whether an account exists.
- After a successful login, redirect to `url_for("landing")` until a dashboard exists.
- `logout()` must call `session.clear()` and then redirect to `url_for("landing")`.
- Logout stays a GET route for now, as specified. When CSRF protection is added in a later step, logout should move to POST.
- All templates must extend `base.html`.
- Use CSS variables. Never hardcode hex values.
- Use `url_for()` for every internal link. Never hardcode paths.

## Definition of done

- [ ] `GET /login` renders the login form with email and password fields
- [ ] Submitting valid credentials (`demo@spendly.com` / `demo123`) sets `session["user_id"]` and redirects to `/`
- [ ] The email is matched regardless of letter case or surrounding spaces
- [ ] Submitting a wrong password shows the flash "Invalid email or password." and stays on the login page with status 200
- [ ] Submitting an unregistered email shows the same generic error flash
- [ ] Submitting an empty email or password shows the same generic error flash
- [ ] The success message from registration is visible on the login page
- [ ] A logged-in user who visits `/login` is redirected to `/`
- [ ] `GET /logout` clears the session and redirects to `/`
- [ ] After logout, `session["user_id"]` is no longer present
- [ ] The `/logout` route no longer returns the raw stub string
