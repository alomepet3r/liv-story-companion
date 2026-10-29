# Modal Deploy Runbook — Story Companion shell

**Status: PREPARED, NOT YET DEPLOYED.** The wrapper (`deploy/modal_app.py`)
is written and syntax-checked. Nothing in this runbook has been executed
against a live Modal account yet — the local check stopped at
`py_compile` because the Modal SDK isn't installed here and no account
exists. Steps below run in order, exactly once, when the account is ready.

What gets deployed: the existing Day 1 app, **unchanged** — `server/`
(stdlib HTTP server) + `web/` (consent gate + conversation UI), served
through Modal's `@modal.web_server`. One container is pinned warm
(`min_containers=1`) so demo days have zero cold starts.

---

## (a) Petro — account (already in progress)

1. Create the Modal account at modal.com (workspace for the hackathon).
2. Add a payment method to the workspace (Starter plan is $0/mo +
   compute; a payment method on file is required to use Modal).
3. Nothing else is Petro's — token, secret, deploy, and verification
   below are agent steps once the token hand-off (b) is done.

## (b) API token — creation and SECURE hand-off

The agent deploys with a Modal API token (a token **ID** `ak-…` plus a
token **secret** `as-…`). Treat the secret like a password.

1. In the Modal dashboard: **Settings → API Tokens → Create token**.
   Name it something recognisable, e.g. `hackathon-deploy`.
2. **Hand-off — pick ONE of these, never chat:**
   - **Preferred:** deliver the token ID + secret through Muse's
     **Secure Vault** capture flow, so the agent retrieves it from the
     vault at deploy time; or
   - **Alternative:** Petro runs the token-set command himself on his
     own machine / in the agent's terminal session (step c1) and the
     secret never travels anywhere.
3. **Do NOT paste the token secret (or the Meta API key) into any chat.**
   Not this one, not any other. If one is ever pasted by accident, treat
   it as exposed: delete that token in the dashboard and create a new one.

## (c) Deploy — exact commands

Run from the repo root (`fireside-build/`), in the deploy environment
(Hugo's VM terminal):

```bash
# c0. One-time: install the Modal CLI/SDK in the DEPLOY environment only
#     (never committed to the repo; the app itself stays stdlib-only).
pip install modal

# c1. Authenticate with the token from step (b).
#     Interactive alternative (opens a browser sign-in):  modal token new
modal token set --token-id <ak-...> --token-secret <as-...>   # values from the vault / Petro's hand, never from chat

# c2. Create the secret that carries the Meta API key.
#     The value is typed by the human at the terminal — it is NOT in the
#     repo, NOT in .env-in-image (the image contains only server/ + web/),
#     and must not be pasted into chat either.
modal secret create meta-model-api MODEL_API_KEY=<the hackathon Meta API key>

# c3. Deploy.
modal deploy deploy/modal_app.py
```

`modal deploy` prints the public URL, of the form
`https://<workspace>--story-companion-serve.modal.run` — record it in
DAY1/DAY2 status notes once live.

Sanity notes: the secret name `meta-model-api` and key name
`MODEL_API_KEY` must match `deploy/modal_app.py` and `server/config.py`
exactly. `modal secret list` confirms the secret exists (it never shows
the value).

## (d) Verify the live URL

With the URL from step c3:

1. **Consent page:** open the URL in a browser → the consent screen
   loads (cream page, one primary button, the qualified
   "Yours. Always." sovereignty line).
   Command-line equivalent:
   `curl -s -o /dev/null -w "%{http_code}\n" <URL>/` → expect `200`.
2. **Health:** `curl -s <URL>/api/health` → expect `{"ok": true}`.
3. **Chat, canned mode (expected while the Meta credit is still 402):**
   ```bash
   curl -s -X POST <URL>/api/chat -H 'Content-Type: application/json' \
     -d '{"consent": true, "session_id": "smoke", "message": ""}'
   ```
   → expect a greeting with `"mode": "canned"`. That is CORRECT for now:
   the endpoint tries live Spark first and falls back automatically.
   Once the organizer credit lands, the same check should start
   returning `"mode": "live"` with no redeploy of the UI (a fresh
   container may be needed so the client re-initialises — restart via
   `modal app stop` + `modal deploy`, or wait for container recycle).
4. **Consent gate:** repeat step 3 with `"consent": false` → expect
   HTTP 403. The gate is enforced server-side, not just in the page.

## (e) Budget cap + watching the $30 Starter credit

1. Dashboard → **Settings → Usage / Billing**: set the workspace
   **monthly budget limit** (a sensible cap for the event window is
   $30 — i.e. don't let spend run past the included Starter credit —
   or lower; hitting the cap pauses compute, it does not bill beyond it
   silently). Check this setting exists and note its value in the
   status notes at deploy time; if the dashboard labels differ, use the
   closest equivalent spend-limit control and record what was set.
2. Expected burn: one minimal warm container ≈ **$4–6/month** (estimate
   from Modal's published per-second rates, see HOSTING-OPTIONS.md) —
   comfortably inside the $30/mo Starter credit, expected out-of-pocket
   **$0**. The $100 event-partner credit is a bonus if it applies to
   hosting; the plan does not depend on it.
3. During the event: glance at **Usage** after each build day. If usage
   trends above the estimate (e.g. extra containers spawning), check
   for stray apps (`modal app list`) before assuming the worst.

## (f) Rollback / teardown

- **Redeploy a previous state (rollback):** `git checkout <last-good-commit>`,
  then `modal deploy deploy/modal_app.py` again. Modal serves the new
  deployment as soon as it's up.
- **Stop the app entirely (teardown):** `modal app stop story-companion`
  — stops all containers and the public URL goes dark. The code and
  secret remain; a later `modal deploy` brings it back.
- **Remove the secret:** dashboard → Secrets → delete `meta-model-api`
  (or `modal secret list` to confirm names first). Do this if the app
  is retired for good.
- **After Nov 4:** edit `min_containers` back to `0` in
  `deploy/modal_app.py` and redeploy, so the app scales to zero when
  idle instead of holding a warm container.

---

### Pre-flight facts (verified locally, Oct 26, 2026)

- `.env` is covered by `.gitignore` (`# Secrets — never commit` section)
  AND sits at the repo root, outside the `server/` and `web/`
  directories the image copies — it cannot enter the image.
- The wrapper file contains **no secret values** — only the secret's
  name (`meta-model-api`) and the env key name (`MODEL_API_KEY`).
- `python3 -m py_compile deploy/modal_app.py` passes (syntax valid).
  The Modal SDK is not installed in this environment, so an
  import/live-deploy test has NOT been run — first real test is step
  (c) with the account + token in hand.
