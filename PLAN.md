# Astropathica — v0 rebuild plan (laptop)

**Decision (2026-08-21):** development restarts here, on the laptop, now. A working v0 exists on the HOME machine (built 2026-07-11) but was never pushed — origin held only a README — and HOME is unreachable until the Torino return. We do not wait for it: the last ten Stanford days (Aug 21–30) need email findability, and this build delivers it. The HOME code becomes salvage: on **Sep 2** it gets pushed and diffed against this rebuild; anything better is kept.

**The clock:** value must arrive within days, not weeks. That is why the phases below put the **ledger before the search index** — the ledger alone unblocks the email attack.

## Hard constraints (unchanged from v0 — binding)

1. **Read-only, always.** No tool ever modifies or deletes an email. Everything operates on exported dumps; the live mailbox is untouched.
2. **Local only.** `maildata/`, `workdata/`, `db/` are gitignored. Push only if the repo is fully clean of mail content.
3. **No Outlook in the pipeline.** Outlook is the manual export button, nothing more. Conversion happens with `readpst` (pst-utils) in WSL; everything downstream is pure Python.
4. **Azure Graph is dead.** POLITO's tenant blocks user-level consent. Do not retry it.

## The reference doctrine this serves (ratified 2026-08-20)

Context: Outlook search is unreliable for Gianluca — this is a hard fact, not a preference. Therefore Outlook is used for *storage only*, and finding always happens in systems we own.

1. **One reference folder** in Outlook (`zzReference`), no subfolders, moved to with one keystroke (Quick Step). Storage loses nothing; finding never depends on Outlook.
2. **Everything left after action-extraction is reference by definition.** Bulk moves, no per-email categorization, inbox reaches zero fast.
3. **The ledger is the finding aid**: one machine-written line per email (date, sender, what it is, probable project tag) in a single greppable file. Built from PST exports. This exists *before* any search index and is useful on its own.
4. **Attachments are handled separately** — they are the only content not findable by text search over bodies. Extract them, keep the few that matter in project Dropbox folders, leave the rest in a flat store pointed at by the ledger.
5. Month-granularity subfolders (`zzRef/2026-05`) are allowed if one bucket ever feels unsafe. Topic folders never.
6. Per-project email citations (one line: date, sender, subject, in the project's Obsidian note) only for critical emails, and only once search works.

## What exists and what it taught

| Asset | Where | State |
|---|---|---|
| HOME v0: `1-convert.sh` (readpst→mbox) → `2-parse.py` (mbox→JSONL: full bodies, message_id/in_reply_to/references, from/to/cc, date, folder, attachments flag) → `3-ingest.py` (ChromaDB, multilingual embedder, 1 email = 1 chunk, union-find thread_id) → `server.py` (MCP: email_search, email_thread, email_stats) | HOME machine, unpushed | Verified 2026-07-11 on 779 emails (June PST). Salvage Sep 2. |
| `salvage/export_PST.py` (Outlook COM extractor) + `salvage/taxonomy-seed.md` (category schema, sender/domain/project maps for the Phase-2 tagger) | this repo, `salvage/` | Salvaged 2026-08-21 from `gianboc/mailRead` (repo then deleted). COM extractor works (proven on 19.8 GB in April) but the route was consciously abandoned for readpst — fallback only. |
| Lessons from v0 (recorded in the Obsidian WI) | — | Dense-only retrieval is weak on acronyms → this rebuild is **hybrid (BM25 + dense) from day one**. Outlook quoted-header stripping is imperfect → keep the stripper conservative. `message_id` is the dedup key for repeated exports. Embedder must be multilingual (IT + EN mail): paraphrase-multilingual-MiniLM-L12-v2. |

## Rebuild phases

Each phase is one working session in this repo. Say "phase N" and Claude builds it against this plan; Gianluca supplies the PST exports and reviews outputs.

- **Phase 1 — Acquire + convert + parse.** Manual PST export of one small folder from Outlook → `readpst` → mbox → parse to JSONL (full bodies, message_id, threading fields, attachment inventory: filename/size/type per email — content comes in Phase 4). Verify counts against Outlook's own folder count.
- **Phase 2 — The ledger.** From the JSONL, generate the one-line-per-email catalog (markdown or CSV: date, sender, subject, one-line gist, probable project tag — gist and tag from an LLM pass, batched). Deliverable: a file Gianluca can grep and read. **This phase is the speed goal — it makes the reference archive findable this week.**
- **Phase 3 — Index + search.** Hybrid retrieval: BM25 + multilingual dense embeddings, keyed on message_id; CLI with sender/date filters and thread grouping. (v0's design plus the BM25 half it lacked.)
- **Phase 4 — Attachments.** Extract attachment content from the PST (`readpst` saves attachments; verify fidelity) → flat store with hash names → ledger rows per file; one LLM-assisted session routes the keepers into project Dropbox folders.
- **Phase 5 — MCP server.** Same three tools as v0 (email_search, email_thread, email_stats), for Claude Code and Claude Desktop.
- **Phase 6 — Scale + steady state.** Full-mailbox export including `zzReference`; monthly re-export with message_id dedup; **Sep 2: push HOME v0, diff, salvage.** After that, the monthly re-export is the only recurring cost.

## Non-goals

No triage/classification of unread mail (that was mailRead's goal; the August hand-massacre did it better). No automation of Outlook itself. No cloud anything.

## The test run — unread 2024 (set 2026-08-21)

Gianluca's condition, verbatim in spirit: *a bucket of 3,000 emails I cannot interrogate is not reference, it is a landfill.* So the doctrine is tested on the unread-2024 slice of the Inbox **in two halves, both must pass**:

- **Half A — extraction.** `embers.py` splits the slice mechanically (To-me-direct, power senders, deadline vocabulary, threads Gianluca replied in). Claude drafts gist + proposed verdict per ember; Gianluca decides each (action / waiting / nothing). Then Gianluca skims 30 random non-embers: **zero live commitments among them, or the filter is too weak.**
- **Half B — retrieval.** After the ledger + search exist over the same slice, Gianluca asks real questions of the 2024 pile ("what did X send about Y", "the email with the Z deadline") and the right emails must come back, in under a minute, without Outlook. **If this fails, nothing gets bulk-moved** — the reference doctrine depends on finding, and finding must be demonstrated before it is trusted.

Only after both halves pass does the 2024 block move to `zzReference`, and only then does the same procedure run on 2025–26.

## Lifetimes (clarified 2026-08-21 after the test run)

- **Permanent, monthly:** export → readpst → parse (Message-ID dedup) → index update. Search (BM25 + dense → Claude reads the hits) is Astropathica proper; no LLM in the pipeline, only at query time.
- **Switched off at regime (decision 2026-08-21):** the ledger gist + tag pass. Possible as a ~$0.50/month plain-language catalog, but the index answers the same need; the ledger is frozen as the bankruptcy artifact. Regime = export → convert → parse → index, no LLM.
- **One-off:** the ledger verdict column (ACTION / WAITING / REFERENCE / NOISE) — the 2026 backlog-bankruptcy tool. Once inbox-zero runs by hand at arrival, it is dead code.
- **Dead:** `embers.py` — mechanical ember filter, refuted on the real inbox 2026-08-21 (73% flagged, ~20% of the "safe" pile live); kept as the record of the test.
