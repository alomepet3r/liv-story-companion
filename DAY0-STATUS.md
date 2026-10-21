# Fireside — Day 0 status (Oct 15, 2026)

## Done (Hugo)

- Repo scaffolded at `meta-hackathon-2026/fireside-build/` (local git).
- Meta Model API client (`server/meta_client.py`): OpenAI-compatible
  `POST /v1/chat/completions` at `https://api.meta.ai/v1`, Bearer auth,
  key from `MODEL_API_KEY` env only — never in code.
- Smoke check (`python3 -m server.smoke`): harmless `GET /v1/models`
  read proving the key works.
- Offline unit tests (`tests/`): payload shape, Bearer header, missing-key
  guard. All passing without a key.

## Waiting on Petro

- [ ] Claim the **$150 Meta Model API credits** and create a key
      (https://dev.meta.ai/), then `cp .env.example .env` and run the
      smoke check. Nothing here can call Meta until this exists.
- [ ] Line up **one willing elder** for demo recordings (family ideally).
- [ ] **30-minute vibe-coding taster** one evening before Oct 26.
- [ ] Decide the **GitHub remote**: repo is local-only for now. Private
      vs public is your call before Day 1 (submission needs a demo URL;
      nothing in this repo crosses the IP boundary either way).

## Not started (per plan)

- Day 1 (Oct 26): web app shell in `web/` with Muse Spark chat wired in.

## Update — Oct 20, 2026 (Petro, via screenshot)
- Petro signed in to dev.meta.ai himself (Hugo's browser is policy-blocked at auth.meta.ai). Dashboard shows a project exists and **1 API key — that key is Petro's PLAYGROUND key, unrelated to this hackathon. Do NOT use it.**
- Still needed: a NEW key created for the hackathon (suggested name: nandoluce-hackathon), pasted to Hugo for .env wiring + live smoke test.
- Credits: dashboard shows $0.00 spend, no balance — Billing page check pending (Petro to view/screenshot).
- Context (Petro, Oct 20): the dev.meta.ai project/key = a personal sandbox he is setting up for himself (Meta Model API / Muse exploration). Separate from this hackathon build — keep the two lanes distinct.
- **Key wired (Oct 20, evening):** Petro created the hackathon key and pasted it; stored in repo .env (gitignored, chmod 600). Smoke: **9 models reachable** incl. muse-spark-1.3 (chat), muse-voice-transcribe-1.0, muse-image-1.0, sam-3.1. NOTE: smoke needs env exported (`set -a; . ./.env; set +a`) — config.py reads environment only.
- **BLOCKER: chat returns HTTP 402 Payment Required** — key authenticates and lists models, but generation is refused: the **$150 hackathon credit is NOT on the account yet**. Next step is Petro in dev.meta.ai → Billing: claim the credit (screenshot Billing if no claim is visible or a payment method is demanded). After the claim, re-run one chat call to confirm end-to-end.
