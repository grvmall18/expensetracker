# Code Review Report: Spendly (Expense_Tracker_Basic)

**Scope:** `app.py`, `database/db.py`, `templates/*.html`, `static/css/*.css`, `static/js/main.js`, `requirements.txt`, `.gitignore`.
**Method:** Static read of the source. I did not run the test suite (there are no tests yet) or exercise the pages in a browser.

## Summary

The front end is in reasonable shape: the landing, terms, privacy and auth pages render, and the new video modal is wired correctly. The main gaps are on the back end. Sign-in and registration cannot submit yet, the database layer is empty, and the privacy policy makes a claim about password hashing that the app does not yet implement.

## High priority

### 1. Login and register forms cannot submit
- **Where:** `app.py` (`/login`, `/register`); `templates/login.html:20`, `templates/register.html:20`.
- **Problem:** Both routes accept only GET, but both forms use `method="POST"` to the same URLs. A submit will return **405 Method Not Allowed**.
- **Fix:** Accept POST in both routes. The handlers can be stubs until Steps 2 and 3 are built.

### 2. Privacy policy claims passwords are hashed
- **Where:** `templates/privacy.html`, section 3 (Data Storage).
- **Problem:** The text says passwords are "stored in hashed form". There is no user model or password storage yet, so this is not true today.
- **Fix:** Reword it until hashing is implemented, or implement hashing (for example `werkzeug.security.generate_password_hash`, which is already available through the Flask dependency).

### 3. Database layer is empty
- **Where:** `database/db.py` contains only comments.
- **Problem:** `get_db()`, `init_db()` and `seed_db()` are not implemented, so nothing persists. `expense_tracker.db` is in `.gitignore`, so this is expected at this stage, but nothing in the app uses the database yet.
- **Fix:** Implement these as part of the database setup step.

## Medium priority

### 4. `debug=True` in the entry point
- **Where:** `app.py:65`, `app.run(debug=True, port=5001)`.
- **Problem:** The Werkzeug debugger allows arbitrary code execution if the app is reachable from outside. It is fine for local development but should not reach a deployed environment.
- **Fix:** Read the debug flag from an environment variable, defaulting to off.

### 5. Placeholder routes return plain strings
- **Where:** `app.py:39-61` (`/logout`, `/profile`, `/expenses/...`).
- **Problem:** These are intentional stubs, but any link to them shows raw text. This is acceptable as scaffolding.
- **Fix:** No action needed now. Replace each one when its step is built.

### 6. Pytest is listed as a runtime dependency
- **Where:** `requirements.txt` lines 3-4 (`pytest`, `pytest-flask`).
- **Problem:** Test tools are installed alongside the app in every environment.
- **Fix:** Move them to a `requirements-dev.txt`. There are no tests yet, so this can wait.

### 7. "See how it works" does nothing without JavaScript
- **Where:** `templates/landing.html`, the `#how-it-works-open` link with `href="#"`.
- **Problem:** Without JS the link goes to `#` and does nothing. The modal script calls `preventDefault`, so this only matters for users with JS disabled.
- **Fix:** Acceptable as is. Optionally link to a real section or a video page as a fallback.

### 8. Modal does not trap keyboard focus
- **Where:** `templates/landing.html`, the video modal script.
- **Problem:** When the modal is open, Tab can move focus to the page behind it. Escape and close work, and the video stops on close.
- **Fix:** Add a simple focus trap, or mark the rest of the page `inert` while the modal is open.

## Low priority

### 9. Unused legacy hero styles
- **Where:** `static/css/style.css` still contains `.hero`, `.hero-inner`, `.hero-visual`, `.mock-card`, `.mock-bar-*` and the matching responsive rules.
- **Problem:** They are no longer referenced by any template after the hero redesign. The `.hero-badge` and `.hero-title` rules are still used by the legal pages.
- **Fix:** Remove the unused rules.

### 10. Hard-coded date on legal pages
- **Where:** `templates/terms.html` and `templates/privacy.html`, "Last updated: November 2026".
- **Fix:** Update the date whenever the text changes, or keep it in one place.

### 11. Placeholder contact details
- **Where:** `templates/privacy.html`, `support@spendly.example`.
- **Fix:** Replace with a real address before launch.

### 12. Privacy policy omits YouTube
- **Where:** `templates/privacy.html`, section 4 (Third Party Services).
- **Problem:** It lists only Google Fonts. The landing page now loads YouTube embeds, which send data to YouTube.
- **Fix:** Add YouTube to that section.

### 13. Placeholder README and sample content
- **Where:** `README.md` contains only the project name. The login and register placeholders use a real-looking name and email (`nitish@example.com`).
- **Fix:** Expand the README when the project is ready to share.

## Things that are done well
- Templates extend `base.html` and use `url_for` throughout, so route changes stay in one place.
- The modal closes on the close button, a click outside, and Escape, and clears the iframe `src` so the video stops.
- `.gitignore` covers `expense_tracker.db`, virtual environments and caches.
- Pinned dependency versions in `requirements.txt`.

## Suggested order
1. Accept POST on `/login` and `/register` (item 1).
2. Fix or implement the password-hashing claim (item 2).
3. Build the database layer (item 3).
4. Make `debug` configurable (item 4).
5. Address the low-priority cleanup as convenient.
