# Report: `.claude/plans/04-profile.md` vs `.claude/specs/04-profile.md`

**Overall status: 🟡 Amber.** The plan covers every requirement in the spec, and the implementation followed it. It is Amber for two reasons: the plan makes one deliberate, flagged change to a file the spec doesn't list (`style.css`), and there is one usability gap that neither document covers, the Profile link disappearing on narrow screens.

## Status by spec section

| Spec section | Status | Notes |
|---|---|---|
| Overview | 🟢 Green | The page with four sections, the hardcoded data, and the logged-in navbar are all covered |
| Depends on | 🟢 Green | Steps 01 to 03 are named, and the plan checked the real database read-only |
| Routes | 🟢 Green | `GET /profile` with a redirect to `/login` when logged out |
| Database changes | 🟢 Green | No queries at runtime. The database was read only to choose realistic hardcoded values. |
| Templates | 🟢 Green | Four sections in order, formats for currency, dates and member-since, and the navbar changes |
| Files to change | 🟡 Amber | `app.py` and `base.html` match. The plan also changes `style.css` (see issue 1). |
| Files to create | 🟢 Green | `profile.html` and `profile.css`, as in the spec |
| New dependencies | 🟢 Green | None |
| Rules for implementation | 🟢 Green | All 9 rules covered |
| Definition of done | 🟢 Green | All 11 items map to a verification step |

### Rules, one by one

| Spec rule | In the plan? |
|---|---|
| Raw sqlite3 only, parameterised queries | 🟢 Not needed, since there are no queries. The plan says so. |
| Authentication guard with `session.get("user_id")` | 🟢 Yes |
| All data hardcoded in `app.py` | 🟢 Yes |
| Hardcoded data internally consistent, stats derived from one list | 🟢 Yes, with a check that table and breakdown totals agree |
| CSS variables, hex only in the `:root` block of `profile.css` | 🟢 Yes, with a parsing check |
| No inline styles, native `<progress>` | 🟢 Yes. Colour comes from a custom property set by a class. |
| Templates extend `base.html` | 🟢 Yes |
| One CSS class per category badge | 🟢 Yes, `badge badge-<category>` |
| `url_for` for every internal link | 🟢 Yes |

## Decisions the plan added (not in the spec)

All 🟢 Green, because none contradict the spec:
- The hardcoded data mirrors the real seed data, so Step 05 only swaps the source.
- Formatting filters (`inr`, `short_date`, `month_year`) are registered now.
- The hardcoded name shows for every signed-in account, which the spec asks for.
- Category colours are the plan's own choice, in a single `:root` block.

## 🟡 Issues

1. **`style.css` is changed, but the spec doesn't list it.** The plan adds a `.nav-user` rule there. The reason is sound: the navbar appears on every page, and `profile.css` loads only on the profile page. The plan flags it as a deviation. The spec's file list should be updated to match, or the rule should move into `profile.css` and accept that it styles the name only on that page.
2. **A needed import isn't listed.** The plan says "Import nothing new from Flask", which is true. It doesn't mention the standard-library `datetime` import that the date filters needed.
3. **Day padding isn't defined.** The spec's example is "14 Mar 2026". The plan gives "20 Nov 2026" and the code prints "7 Nov 2026" with no leading zero, but neither document says which form to use for single-digit days.

## 🟡 Gap neither document covers

- **The Profile link is hidden on narrow screens.** `style.css` has a rule that hides every navbar link except the call-to-action button at 600 px wide or less. The Logout button is the call-to-action, so on a phone a signed-in user sees the name and Logout, but no Profile link. Nothing else links to the profile page. The spec and the plan both add the link without checking this.

## 🟢 Checks that passed

- Every spec requirement appears in the plan, and nothing in the plan contradicts the spec.
- Verification covers every Definition of done item, plus section order, consistency between the table, stats and breakdown, and that the real database is untouched. All 38 checks passed when run.
- The plan states openly that the page's appearance was not checked in a browser.

## Plan versus the code today

The plan describes Step 4 as built. Step 5 later replaced the hardcoded data, the `build_stats` and `build_breakdown` helpers and the `month_year` filter with live database queries, as its own spec intended. So the plan no longer matches the current code, by design.

## Recommended fixes

- Add `style.css` to the spec's "Files to change", or move `.nav-user` into `profile.css`.
- Decide whether single-digit days are padded, and say so in the spec.
- Make the Profile link visible on narrow screens, for example by giving it the same treatment as the Logout button, or by showing it in the navbar's small-screen layout.
