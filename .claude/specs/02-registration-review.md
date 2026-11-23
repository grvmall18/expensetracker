# Report: `.claude/plans/02-registration.md` vs `.claude/specs/02-registration.md`

**Overall status: 🟡 Amber.** The plan covers every requirement in the spec, and the implementation follows the plan. The one real deviation is that the plan left the success-message styling undecided, and the implementation ended up editing `style.css`, a file the spec doesn't list. The other items are small.

## Status by spec section

| Spec section | Status | Notes |
|---|---|---|
| Overview | 🟢 Green | The plan's Context states the current state and the goal |
| Depends on | 🟢 Green | Plan states Step 01 is implemented, and checks `spendly.db` against it |
| Routes | 🟢 Green | GET and POST on `/register`, public |
| Database changes | 🟢 Green | `create_user` hashes, inserts, returns the id, and lets `IntegrityError` propagate |
| Templates | 🟡 Amber | Register and login changes match. The success-message styling was left to be "decided in implementation" (see issue 1). |
| Files to change | 🟡 Amber | `app.py`, `db.py`, `register.html` and `login.html` match. `style.css` ended up changed too, but isn't in the spec's list. |
| Files to create | 🟢 Green | None |
| New dependencies | 🟢 Green | None. Uses `werkzeug.security` and Flask's built-ins. |
| Rules for implementation | 🟢 Green | Every rule is covered (details below) |
| Definition of done | 🟢 Green | All 11 items map to a verification step |

### Rules, one by one

| Spec rule | In the plan? |
|---|---|
| No ORM, parameterised queries only | 🟢 Yes |
| Hash with `generate_password_hash`, no plaintext | 🟢 Yes |
| `app.secret_key` hardcoded for dev | 🟢 Yes, with a value and a warning |
| Trim name and email, lowercase email, do not trim password | 🟢 Yes |
| Validation order: non-empty, email shape, length, match, duplicate | 🟢 Yes, in the same order |
| 8-character minimum applies to registration only, demo user exempt | 🟡 Implicit only. The plan doesn't say the demo user is exempt. |
| On failure: flash `error`, status 200, no redirect, keep name and email | 🟢 Yes |
| On success: flash `success`, redirect to login | 🟢 Yes |
| `abort(405)` for unsupported methods | 🟢 Yes, with a note that Flask's `methods` already blocks them |
| Templates extend `base.html`, CSS variables only, `url_for` for links | 🟢 Yes |

## Decisions the plan added (not in the spec)

All 🟢 Green, because none contradict the spec:
- Email shape is checked with `^[^@\s]+@[^@\s]+$`, with no dot required.
- Exact message texts for each validation failure.
- The password is not re-filled after an error.

One small wording difference: the spec's checklist quotes "Email already registered" without a full stop, and the plan's message ends with one. A text match still works.

## 🟡 Issues

1. **Success-message styling was left open, and the fallback was poor.** The plan said that if no success style existed, the success message would share the red `auth-error` style, and the choice would be made in implementation. `style.css` has no success style, so the implementation added an `.auth-success` class instead. That is a better result, but it changes a file outside the spec's list, and the plan didn't anticipate it. The new rule uses only existing CSS variables and changes no existing rule.
2. **Demo-user exemption isn't stated in the plan.** The spec says the 8-character minimum does not apply to the seeded user. The plan doesn't mention it, so a reader might wonder whether `demo123` is a conflict. It isn't, because the demo user doesn't go through this form.
3. **The plan's user counts ignore the demo user.** Verification step 2 says a valid POST "creates one new user". A temporary database is seeded with the demo user at import, so the count after one registration is 2. My first check run failed because of this. The app was correct and the test expectation was wrong.
4. **Hash check used a temporary database.** The spec says to check the hash by "inspecting `spendly.db`". The plan checks a temporary database, and also confirms that the real `spendly.db` is unchanged. This is equivalent and safer, but it isn't literally what the spec says.

## 🟢 Checks that passed

- Every spec requirement appears in the plan, and nothing in it contradicts the spec.
- The implementation matches the plan, apart from the `style.css` change.
- Verification covers every Definition of done item, plus malformed emails, 405 for other methods, and that the real database is untouched. All 33 checks passed.

## Observations that neither document covers

- **CSRF protection:** the form has no CSRF token. Other specs defer this too.
- **Account enumeration:** the required "Email already registered" message tells anyone whether an address has an account. The spec asks for it, so this is a known trade-off.
- **Field length:** no maximum length is set for name or password.

## Recommended fixes

- Add the `.auth-success` change to the plan's "Files to change", or to the spec's.
- Add a line saying the demo user is exempt from the length rule.
- Adjust the plan's verification wording to account for the seeded demo user.
