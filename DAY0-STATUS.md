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
