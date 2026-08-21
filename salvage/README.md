# salvage/ — material recovered from the retired `mailRead` repo

Provenance: `gianboc/mailRead` @ 31fb7da, salvaged 2026-08-21 before the repo was
deleted (local clone + GitHub). mailRead was the April 2026 unread-mail triage
project; its triage goal is a non-goal here (see PLAN.md), but two assets carry over:

- `export_PST.py` — Outlook COM extractor (pywin32, Windows-side). Proven in April
  2026 on a 19.8 GB / ~50,873-email PST. **Fallback only**: the pipeline standard is
  `readpst` in WSL. Reach for this if readpst ever disappoints (fidelity, encoding,
  attachment extraction). Note its limits vs our parser: 3000-char body previews,
  no Message-ID / threading fields.
- `taxonomy-seed.md` — the categorization spec from mailRead's context file:
  category schema, project/paper codenames, key-sender table, sender-domain hints.
  Seed material for the Phase 2 ledger tagger (one-line gist + probable project tag).
  Snapshot of May 2026 — refresh names/tags against the vault's `projectTags.md`
  before use.
