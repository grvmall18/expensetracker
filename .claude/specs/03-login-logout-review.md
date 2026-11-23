# Report: `.claude/plans/03-login-logout.md` vs `.claude/specs/03-login_logout.md`

**Overall status: 🟢 Green.** The plan covers every requirement in the spec, and the implementation follows the plan. The only issues are small: two near-identical plan files, one interpretation of the dummy-hash rule, and a few spec rules the plan covers only by implication.

## Status by spec section

| Spec section | Status | Notes |
|---|---|---|
| Overview | 🟢 Green | The plan's Context covers the login and logout goals and the current state of `login.html` |
| Depends on | 🟢 Green | Steps 01 and 02 are stated as implemented, and the secret key and flash support are named |
| Routes | 🟢 Green | GET and POST `/login`, GET `/logout`. The logged-in GET redirect is included. |
| Database changes | 🟢 Green | `get_user_by_email` is a parameterised lookup in `db.py` that returns the row or `None` |
| Templates | 🟢 Green | Form action via `url_for`, `method="post"`, the old `error` block removed, the flash loop kept, and the register link kept |
| Files to change | 🟢 Green | `app.py`, `database/db.py` and `templates/login.html`, as in the spec |
| Files to create | 🟢 Green | None |
| New dependencies | 🟢 Green | None. Uses `check_password_hash`. |
| Rules for implementation | 🟢 Green | All 14 rules covered (see below) |
| Definition of done | 🟢 Green | All 11 items map to a verification step |

### Rules, one by one

| Spec rule | In the plan? |
|---|---|
| Raw sqlite3 via `get_db()`, no ORM, parameterised queries | 🟢 Yes |
| Verify with `check_password_hash` | 🟢 Yes |
| Trim and lowercase email, do not trim password | 🟢 Yes |
| `session["user_id"]` stored as an integer | 🟢 Yes, and checked by type in verification step 2 |
| Use `flask.session` | 🟢 Yes |
| `session.clear()` before setting the user on login | 🟢 Yes, with a check that old data is gone (step 11) |
| Failed login: generic message, category `error`, status 200, no redirect | 🟢 Yes |
| Empty email or password gets the same generic error | 🟢 Yes |
| Dummy hash check when the email is not found | 🟡 Yes, but skipped for an empty email (see issue 2) |
| Redirect to the landing page after login | 🟢 Yes |
| `logout()` clears the session, then redirects to the landing page | 🟢 Yes |
| Logout stays GET for now | 🟢 Yes, and noted as a risk |
| Templates extend `base.html`, no hex colours, `url_for` for links | 🟡 Covered by implication only. The plan says no CSS changes are needed, and uses `url_for` for the form and register link. It never states "extends `base.html`", which is already true. |

## 🟢 Decisions the plan added (not in the spec)

None contradict the spec:
- A POST from an already-logged-in user is processed normally, and only GET is redirected, as the spec words it.
- The email is not re-filled after a failed login.
- The exact message text `Invalid email or password.`.

## 🟡 Issues

1. **Two copies of the plan exist.** `02-login-logout.md` and `03-login-logout.md` have almost the same content. Only one sentence in Context differs. The older file's sentence says it matches the file name `02-...`, so the two now describe themselves differently. Keep the `03` file and delete the other, or leave both.
2. **Empty email skips the dummy hash check.** The spec says to run a dummy check "when the email is not found". An empty email is not looked up at all, so skipping the check is a fair reading, and it reveals nothing about any account. But the spec is silent on this case, and the plan makes the call without flagging it as an interpretation.
3. **The plan's Context describes the project as it was then.** It says "Steps 01 and 02 are implemented". Steps 04 and 05 have since changed `app.py` and `profile.html`. This only matters if someone reads the plan as a description of today's code.

## 🟢 Checks that passed

- Every spec requirement appears in the plan, and nothing in the plan contradicts the spec.
- Verification covers every Definition of done item, plus the timing guard, session clearing, switching users, and that the real database is untouched.
- The login and logout code is unchanged since Step 3. The Step 3 checks were rerun after Step 5 and all 27 passed.

## Not covered by either document

- **Login CSRF and logout CSRF:** neither form has a token. The spec defers this and notes that logout should move to POST later.
- **Cookie settings:** nothing sets `SameSite`, `Secure` or session lifetime, so the defaults apply.
- **Rate limiting or lockout:** repeated guesses are not slowed down. The plan lists this as a risk.

## Recommended fixes

- Delete the older `02-login-logout.md` copy, or add a line to each noting that the other exists.
- Add a line to the plan saying an empty email skips the dummy check on purpose, and why.
- Optionally add "no change to `base.html` inheritance" to the plan's rules checklist.
