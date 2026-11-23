# Report: `.claude/plans/01-databasesetup.md` vs `.claude/specs/01-database-setup.md`

**Overall status: 🟡 Amber.** The plan covers every requirement in the spec, and the implementation follows it. Three items need fixing: one verification step caused the missing-database problem, one risk note is inaccurate, and one import will fail lint checks.

## Status by spec section

| Spec section | Status | Notes |
|---|---|---|
| 1. Overview | 🟢 Green | Plan implements the overview's scope |
| 2. Depends on | 🟢 Green | No prerequisites, and the plan adds none |
| 3. Routes | 🟢 Green | Placeholder routes kept unchanged |
| 4. Database schema | 🟢 Green | All columns, types and constraints listed. `REFERENCES users(id)` is equivalent to the spec's FOREIGN KEY. |
| 5. Functions | 🟢 Green | `get_db`, `init_db` and `seed_db` specified, including the `SPENDLY_DB_PATH` override and the eight-row seed table |
| 6. Changes to app.py | 🟢 Green | Import, plus `init_db`/`seed_db` inside `app.app_context()` |
| 7. Files to change | 🟢 Green | `db.py`, `app.py` and `.gitignore` match exactly |
| 8. Files to create | 🟢 Green | None, as the spec says |
| 9. Dependencies | 🟢 Green | Only `sqlite3` and `werkzeug.security` |
| 10. Categories | 🟢 Green | Seed rows use only the seven fixed categories |
| 11. Rules | 🟢 Green | Parameterised SQL, FK pragma, REAL amounts, hashing, idempotent seed, `YYYY-MM-DD` dates |
| 12. Expected behaviour | 🟢 Green | Each function's behaviour and constraints covered |
| 13. Error handling | 🟢 Green | Plan says sqlite errors propagate, matching the spec |
| 14. Definition of done | 🟢 Green | Each item maps to a verification step |

## 🟡 Issues in the plan

1. **Verification step 8 deletes the database.** It says to delete the generated `spendly.db` after the startup check. That is why the file was missing. The spec's Definition of done requires the file to be created on app startup, not removed afterwards. The step should keep the file, or delete only a temporary one. **This is the root cause of the missing-database problem.**
2. **The Risks note is inaccurate.** It says `app.py` isn't committed "with the earlier Terms and Privacy routes beyond the last push". Those routes were pushed in commit `93d1236`. The real risk is any other uncommitted `app.py` changes, so the plan should say to check `git diff app.py` before committing.
3. **Unused import.** `app.py` imports `get_db` but never uses it. Linters will flag it. The spec lists `get_db` under functions to implement, not under the app.py import list, so this is a plan choice rather than a spec requirement.

## 🟢 Checks that passed

- Every spec requirement appears in the plan. Nothing is missing, and nothing is added beyond the spec.
- The seed-date rule matches the spec: first of the month plus offset, capped at today.
- The verification steps cover the Definition of done, including the `SPENDLY_DB_PATH` override, the foreign key check, and `.gitignore`.
- The implemented code matches the plan. The checks in the plan all passed when run earlier.

## Recommended fixes

- Rewrite verification step 8 to keep `spendly.db` in place.
- Correct the Risks note.
- Remove the unused `get_db` import from `app.py`.
