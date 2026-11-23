# Report: `.claude/plans/06-date-filter-profile.md` vs `.claude/specs/06-date-filter-profile.md`

**Overall status: 🟡 Amber.** The plan covers every requirement in the spec, and the implementation followed it. Every verification step in the plan was run and passed. It is Amber because the plan trims spaces around dates while describing itself as following the spec exactly, which it doesn't, and because the filter has no automated tests inside the project.

## Status by spec section

| Spec section | Status | Notes |
|---|---|---|
| Overview | 🟢 Green | The filter, the query-string driver, the presets and custom range, and all three sections respecting it |
| Depends on | 🟢 Green | The plan states Steps 01 to 05 are implemented, which covers the spec's Steps 01, 04 and 05 |
| Routes | 🟢 Green | Both parameters, the "both valid" rule, and the silent fallback for blank, malformed and single dates |
| Database changes | 🟢 Green | None. The plan confirmed the `date` column is text, so `BETWEEN` works inclusively. |
| Templates | 🟢 Green | Flash display, filter bar above the stats row, four presets, `required` date inputs, pre-filled dates and the active state |
| Files to change | 🟢 Green | `app.py`, `queries.py`, `profile.html` and `profile.css`, as in the spec |
| Files to create | 🟢 Green | None |
| New dependencies | 🟢 Green | None. `calendar` and `datetime` are standard library. |
| Rules for implementation | 🟡 Amber | All rules covered, with one deviation (issue 1) |
| Definition of done | 🟢 Green | All 13 items map to a verification step, with one gap in the plan's wording (issue 2) |

### Rules, one by one

| Spec rule | In the plan? |
|---|---|
| Raw sqlite3 via `get_db()`, `?` placeholders for the bounds | 🟢 Yes, as a fixed SQL fragment with bound values |
| Validate with `datetime.strptime(value, "%Y-%m-%d")` | 🟡 Yes, but with extra trimming of spaces (issue 1) |
| "Today" from a single helper | 🟢 Yes, `get_today()`, replaceable in checks |
| Preset ranges, including clamping for short months | 🟢 Yes, with a clamping check for four dates |
| Preset links built with `url_for` | 🟢 Yes. Dropping `None` for "All Time" is checked, not assumed. |
| Both dates absent behaves like Step 05 | 🟢 Yes |
| Reversed range: flash and fall back | 🟢 Yes, rendered directly with no redirect |
| One valid date means no filter, no flash | 🟢 Yes |
| Active-state rules, preset wins | 🟢 Yes, with checks for each case |
| CSS variables, no inline styles | 🟢 Yes, with a check on `profile.html` and `profile.css` |
| `url_for` for every internal link | 🟢 Yes |

## 🟢 Decisions the plan added (not in the spec)

None contradict the spec:
- Query helpers also ignore a filter if only one date reaches them, and accept date objects or ISO strings.
- Unpadded dates such as `2026-3-5` are accepted and normalised.
- No caption describing the applied range, because the spec doesn't ask for one.
- Flash messages reuse the existing `.auth-error` and `.auth-success` styles.

## 🟡 Issues

1. **The plan trims spaces, but says it follows the spec exactly.** The plan's "strict reading of valid" says a value is valid if `strptime` accepts it "after trimming spaces, exactly as the spec says". The spec doesn't mention trimming. A literal reading would treat `" 2026-01-01 "` as malformed and drop the whole filter. The plan and the code accept it. The effect is tiny, because a browser date input never sends spaces, but the plan's wording contradicts itself.
2. **The plan's verification has no explicit ₹ check.** The spec's checklist says all amounts keep the ₹ symbol under a filter. The plan has no matching item. The scratch script did check it, so the requirement was met, just not planned.
3. **The filter has no automated tests in the project.** The spec lists no tests and says to create no files, and the plan follows that. All 74 checks live in a scratch script outside the repo, so nothing in the project will catch a regression in the filter. The spec's "so tests can substitute a fixed date" has no tests to use it.
4. **Small wording slip.** The plan's Reuse section says "`begin`/`finally` connection handling". The code uses `try`/`finally`.

## 🟢 Checks that passed

- Every spec requirement appears in the plan, and nothing in the plan contradicts the spec apart from issue 1.
- All 16 verification steps in the plan were run and passed, including the clamping dates, the active-state cases, the 10 invalid-input patterns, user isolation, and the copy of the real database.
- The 26 existing tests pass from the project root and from another directory. The Step 02, 03 and 05 scripts still pass.
- The real database is unchanged by the checks: 2 users, 8 expenses, same modification time and size.

## Not covered by either document

- **Row limit versus count:** the transaction table shows at most 10 rows, but the stats count every expense in the range. A filtered view with 15 expenses shows "15" and 10 rows. This predates the filter but is more visible with it.
- **Browser behaviour:** the layout and the look of the active state were not checked in a browser.
- **Saved preset links:** a bookmarked preset keeps its old dates, so days later it shows as a custom range. The plan notes this as a risk.

## Recommended fixes

- Reword the plan's validation note to say trimming is an addition, or remove the trimming.
- Add the ₹ check to the plan's verification list.
- Consider moving the filter checks into a `tests/` file, for example `tests/test_date_filter.py`. This needs a decision from you, because the spec says to create no files.
