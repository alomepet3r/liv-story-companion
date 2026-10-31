# web/

The Liv front end. A single page, three screens — consent,
conversation, chapter — each an ink **chassis** at 100dvh
(header pinned, one scroll region, foot pinned), the Sheet's
manners inside it. Design: **the Marriage** (founder ruling,
Oct 31, 2026; spec `design-vet/marriage/marriage.html`) — the
Monolith's machine taught the Sheet's manners, in the Quiet
Neutrals token set (unchanged since Direction B, Oct 29, 2026).

- **index.html** — Screen 1: the consent gate in the chassis
  (the FULL live copy: AI disclosure, the qualified sovereignty
  line — "Your stories are yours, always. You can delete
  anything, anytime. The only time we could not delete
  something is if a court, or the law protecting a child,
  required us to keep it…" — the Three honest things, the
  spoken consent script, both checkboxes gating Begin).
  Screen 2: the conversation — titlebar (wordmark + "Talking
  To Liv"), card-box turns at a centred 720px measure, the
  switchboard foot (asleep meter, write line, the Talk key),
  the guard rail on wide screens / "This sitting" sheet on
  narrow ones, and the hold-to-delete guard. Screen 3: the
  chapter — plan → draft → review with the ribbon graft
  (flame spine, a node generated per row).
- **styles.css** — Quiet Neutrals tokens only (desk, sheet,
  card, ink, tint, action, flame…); measured AA pairings are
  recorded in the file's header comment. Atkinson
  Hyperlegible rides second in the font stack.
- **app.js** — the consent gate in the browser (nothing is
  shown or sent before agreement; the server enforces the
  same gate), chat/media/archive flows, the voice deck
  (one-tap record, Stop = sends, session Wake Lock), the
  honest meter (the recording band's segments light from
  the real microphone level via an AnalyserNode on the
  recorder's stream; nothing claims "listening" at rest),
  the hold-to-delete wiring (2s hold, pointer + keyboard,
  completing runs the unchanged end-session flow), and the
  chapter calls. The visible brand in the app is
  **FireSide**; the companion is **Liv**.

Served by `server/app.py` — see the repo `DAY4-STATUS.md`
(Day 6 section) for the build record and verification.
