---
name: spendly-ui-designer
description: Design and build UI for Spendly, a personal expense tracker made with Flask, Jinja2 and vanilla CSS. Use this skill whenever the user asks to design, create, build, redesign, restyle or improve any Spendly page, section or component (anything in templates/ or static/), including requests like "make the profile page look better" or "design a reports page", even when Spendly isn't named but the context is clearly this project.
---

# Spendly UI Designer

Build UI that looks like it already belongs in Spendly: server-rendered Jinja2 templates, plain CSS and a little vanilla JS. No React, Vue, Tailwind, Bootstrap, preprocessors or icon libraries unless the user asks for them.

## Read first

- `templates/base.html`, and the template you are changing (or the closest existing one).
- `static/css/style.css` (design tokens and shared components), plus `profile.css` or `landing.css` if the page uses it.
- The matching spec in `.claude/specs/`. Specs are the source of truth for page behaviour. If a design request conflicts with a spec, say so before changing it.

The CSS files win if anything below differs from them.

## What the app has

| Route | Template | Styles besides `style.css` |
|---|---|---|
| `/` | `landing.html` | `landing.css` |
| `/register`, `/login` | `register.html`, `login.html` | none |
| `/profile` | `profile.html`: user card, date filter, stats, transaction table, category breakdown | `profile.css` |
| `/expenses/add` | `add_expense.html`: full-page form | none |
| `/expenses/<id>/edit` | `edit_expense.html`: full-page form | none |
| `/terms`, `/privacy` | `terms.html`, `privacy.html` | none |

Logout and delete (POST only) have no page of their own.

The layout is a top navbar, main content and a footer. There is no dashboard page or sidebar. The app records expenses only: it has no income, balance, savings or budget data (the landing page preview is a marketing mock). Don't design widgets that need data the app lacks unless the user asks for that feature, and then say what backend work it needs.

## Design tokens

Declared in `:root` in `style.css`.

| Purpose | Variables |
|---|---|
| Text | `--ink`, `--ink-soft`, `--ink-muted`, `--ink-faint` |
| Surfaces | `--paper` (page), `--paper-warm`, `--paper-card` |
| Accent (dark green) | `--accent`, `--accent-light` |
| Second accent (amber) | `--accent-2`, `--accent-2-light` |
| Errors and delete | `--danger`, `--danger-light` |
| Borders | `--border`, `--border-soft` |
| Fonts | `--font-display` (DM Serif Display: titles, large figures), `--font-body` (DM Sans: everything else) |
| Radius | `--radius-sm` 6px (inputs, buttons), `--radius-md` 12px (cards), `--radius-lg` 20px (large panels); pills use `999px` |
| Width | `--max-width` 1200px, `--auth-width` 440px (the profile page is 960px) |

Category colours live in `profile.css` as `--cat-<name>` and `--cat-<name>-bg`.

- Colours in new rules come from variables. No hex values in templates or CSS rules; declare a new colour as a variable in `:root`. The hex values already in `landing.css` and a few `style.css` rules are old exceptions: don't copy them.
- `landing.css` (`sp-` classes) has its own look. Follow it only when editing the landing page.
- No inline styles. The one exception is `style="display:inline"` on the delete forms (spec 09).
- Cards are separated by borders rather than shadows. Space in `rem`, matching the neighbouring rules.

## Reuse these classes

| Need | Classes |
|---|---|
| Form page | `.auth-section` > `.auth-container` > `.auth-header` (`.auth-title`, `.auth-subtitle`), `.auth-card`, `.auth-switch` for the link below |
| Form fields | `.form-group` with `label` and `.form-input`; `.btn-submit` |
| Flash messages | `.auth-error`, `.auth-success` (copy the flash loop from an existing template) |
| Buttons, global | `.btn-primary`, `.btn-ghost`, `.btn-delete` |
| Buttons, profile | `.btn-add`, `.btn-edit`, `.filter-apply` |
| Cards and stats | `.profile-card`, `.section-head`, `.section-title`, `.stats-row`, `.stat-card`, `.stat-label`, `.stat-value` |
| Tables | `.table-wrap` > `.tx-table`; `.tx-amount` right-aligns amounts with tabular figures |
| Categories | `.badge .badge-<name>`, `.bar .bar-<name>` (lowercase category name) |

Classes marked profile, and the card, table and category classes, are in `profile.css`. A page that uses them must link it.

## Templates and data

- Every page extends `base.html`. Blocks: `title`, `head` (page CSS), `content`, `scripts`.
- Money: `{{ value|inr }}` (₹1,234.50). Dates: `{{ value|short_date }}`. Pass raw values from Python and format in the template. Amount inputs are labelled "Amount (₹)".
- Categories: loop over the `categories` list the route passes in (`CATEGORIES`). Never type the list into a template.
- Links and form actions use `url_for`.
- Shared styles go in `style.css`, profile styles in `profile.css`. A new page stylesheet is linked through the `head` block and uses a class prefix.
- JavaScript goes in `static/js/main.js` or the page's `scripts` block. Don't add inline event handlers; the delete `confirm()` is the one spec 09 allows.
- The app has no icon library (the brand mark is a text character). Ask before adding one or any other CDN script, and pin an exact version.

## Accessibility

- Normal text needs a contrast of at least 4.5:1. On the light surfaces `--ink`, `--ink-soft`, `--ink-muted`, `--accent` and `--danger` pass. `--ink-faint` and `--accent-2` fail: don't use them for text on light backgrounds, even where older rules do. Each category colour passes on its own `-bg`.
- Every input has a `<label for="...">`.
- Keyboard focus must stay visible. `.form-input` and `.filter-date` swap the outline for an accent border; never remove an outline without a replacement.
- Don't rely on colour alone to carry meaning.

## Narrow screens

- Existing breakpoints are 900px, 700px (profile) and 600px.
- Stack cards and put tables inside `.table-wrap`.
- Below 600px every navbar link except `.nav-cta` is hidden, so a page reachable only from the navbar needs another route to it on phones.

## Workflow

1. Give a short UI plan (2-5 bullets) and state your assumptions. Ask only when the answer changes the result, such as page versus dialog.
2. Edit the files in the repo. Show code without editing only if the user asks for a mock-up.
3. Keep what tests and specs rely on: element ids (the profile sections are `user-info`, `filter-bar`, `summary-stats`, `transactions`, `category-breakdown`), class names and form field names.
4. Run `python -m pytest`.
5. Check the page at desktop and about 375px wide: `python app.py`, then http://localhost:5001. The demo login `demo@spendly.com` / `demo123` exists when the database was seeded fresh. Adding, editing or deleting while checking changes the database, so set `SPENDLY_DB_PATH` to a temporary file first. If you could not view the page, say so.
6. Report the files changed, any route or template variable changes, and the test result.

## Avoid

- Gradients, shadows or extra accent colours where a solid fill or border works.
- More than one main action in a view.
- Icon-only or clever controls where a labelled button is clearer.
