# 02 — Registration

## Overview

- This step upgrades the existing stub `GET /register` route into a fully functional registration flow that handles both GET and POST.
- The form accepts four fields: `name`, `email`, `password`, and `confirm_password`.
- On success, the app flashes a success message and redirects to `/login`.
- On any validation failure, the app re-renders the form with a flashed error message.
- Current state: `register.html` already posts to a hard-coded `/register` and has `name`, `email`, and `password` inputs, but has no `confirm_password` input and shows errors through a single `error` variable. `app.py` has no `secret_key` and no POST handling.
- This is the entry point for all authenticated features. Nothing that depends on a signed-in user can be used until accounts can be created.

## Depends on

- Step 01 — Database setup, implemented in code (the `users` table and `get_db()`).

## Routes

- `GET /register` — render the registration form — public. This route already exists as a stub and is upgraded in this step.
- `POST /register` — process the form, validate input, insert the user, and redirect to `/login` — public.

## Database changes

- No new tables or columns.
- The existing `users` table covers all requirements.
- Add one new DB helper to `database/db.py`: `create_user(name, email, password)`.
  - Hashes the password with werkzeug.
  - Inserts a row into `users`.
  - Returns the new user's id.
  - Raises `sqlite3.IntegrityError` if the email is already taken (UNIQUE constraint).

## Templates

- Modify `templates/register.html`:
  - Change the form action to `url_for('register')` and set `method="post"`.
  - Add `name` attributes to all inputs: `name`, `email`, `password`, and `confirm_password`.
  - Add the missing "Confirm password" input, styled like the existing inputs.
  - Replace the single `error` variable block with a block that displays all flashed messages, using the message category to choose between an error style and a success style.
  - Keep the "Min. 8 characters" hint on the password input.
  - Keep all existing visual design unchanged.
- Modify `templates/login.html`, display only:
  - Add a block that displays flashed messages of any category, so the registration success message is visible after the redirect.
  - Step 03 builds the rest of the login form.

## Files to change

- `app.py` — upgrade `register()` to handle GET and POST, add the flash and redirect logic, and set `app.secret_key`.
- `database/db.py` — add the `create_user()` helper.
- `templates/register.html` — wire up the form action and method, add the confirm-password input, and display flashed messages.
- `templates/login.html` — add the flashed-message display only.

## Files to create

- None.

## New dependencies

- None.
- Uses `werkzeug.security` (already installed) and Flask's built-in `flash`, `redirect`, and `url_for`.

## Rules for implementation

- No SQLAlchemy or ORMs.
- Use parameterised queries only. Never use f-strings in SQL.
- Hash passwords with `werkzeug.security.generate_password_hash`. Never store plaintext passwords.
- `app.secret_key` must be set in `app.py` for `flash()` to work. Use a hardcoded dev string for now.
- Trim whitespace from `name` and `email`. Convert `email` to lowercase before validating, inserting, or comparing. Do not trim the password.
- Server-side validation must check in this order:
  - 1. All fields are non-empty after trimming.
  - 2. The email has basic valid shape: text, then `@`, then text.
  - 3. The password is at least 8 characters long.
  - 4. `password` equals `confirm_password`.
  - 5. The email is not already registered (catch `sqlite3.IntegrityError`).
- The 8-character minimum applies to registration only. The seeded demo user (`demo123`) is exempt, because it is not created through this form.
- On any validation failure, re-render the form with a flashed error of category `error` and HTTP status 200. Do not redirect. Keep the entered name and email in the form.
- On success, flash a message of category `success` and redirect to `url_for('login')`.
- Use `abort(405)` if an unsupported HTTP method reaches the route.
- All templates must extend `base.html`.
- Use CSS variables. Never hardcode hex values.
- Use `url_for()` for every internal link. Never hardcode URLs.

## Definition of done

- [ ] `GET /register` renders the registration form, including the confirm-password field, without errors
- [ ] Submitting with all valid fields creates a new user in `users` and redirects to `/login`
- [ ] The success message is visible on the login page after registering
- [ ] Submitting with mismatched passwords re-renders the form with an error and makes no DB insert
- [ ] Submitting a password shorter than 8 characters re-renders with an error and makes no DB insert
- [ ] Submitting with an already-registered email re-renders with "Email already registered"
- [ ] Registering the same email with different letter case (for example `Demo@Spendly.com`) is rejected as already registered
- [ ] Submitting with any empty field re-renders with a validation error
- [ ] The password is stored as a hash, never plaintext, which can be checked by inspecting `spendly.db`
- [ ] No duplicate user is created on repeated valid submissions with the same email
- [ ] `app.secret_key` is set and `flash()` works
