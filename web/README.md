# web/

The Day 1 app shell (built Oct 26, 2026). A single page, two screens:

- **index.html** — Screen 1: the consent gate (plain-language copy,
  the qualified sovereignty line ("Your stories are yours, always.
  You can delete anything, anytime. The only time we could not
  delete something is if a court, or the law protecting a child,
  required us to keep it…"), and a ~30-second consent script to read aloud for
  recorded sessions). Screen 2: the conversation — large-type,
  accessibility-first chat.
- **styles.css** — design tokens from the brief: cream paper `#FBF7EF`,
  charcoal `#2B2622`, ember red `#9D2224` for the single primary action
  only; serif display headings, readable sans body (19px+), WCAG 2.2 AA
  pairings.
- **app.js** — the consent gate in the browser (nothing is shown or
  sent before agreement) and the chat calls to `POST /api/chat`. The
  server enforces the same consent gate, so the page cannot be
  bypassed.

The in-app header reads **"Story Companion"** — a neutral working
label. No public product name is used in the app until the name
decision closes (organizer permission + clearance, by Nov 2).

Served by `server/app.py` — see the repo `DAY1-STATUS.md` for how to
run it and what was verified.
