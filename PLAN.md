# Astropathica — PLAN

Local, read-only search over the exported POLITO mailbox, and the one-off tool that empties the backlog into GTD.

Three words are used with fixed meanings throughout this repo:

| Word | Meaning | Where it lives |
|---|---|---|
| **Step** | one stage of the *pipeline* — a program run (or a manual act) that turns one file into the next. Steps are numbered 0–7 and run in order every time mail is processed. | § 2 below; full table in `README.md` |
| **Phase** | one unit of *building* the code — a working session that makes a step exist. Phases are numbered 1–6 and are done once. | § 3 below |
| **The burn** | the *schedule* for emptying the backlog: which steps run on which day this week. | § 4 below |

Everything learned by running (numbers, pitfalls, what failed) is in `experience/EXPERIENCE.md`, not here. This file says what to do; that file says what happened.

---

## 1. Constraints and doctrine

**Hard constraints (binding):**
1. **Read-only, always.** No tool modifies or deletes an email. Everything runs on exported copies; the live mailbox is untouched.
2. **Local only.** `maildata/`, `workdata/`, `db/` are gitignored. Push only when the repo holds no mail content.
3. **No Outlook in the pipeline.** Outlook is the export button and the final drag, nothing more. Conversion is `readpst` in WSL; everything downstream is Python.
4. **Azure Graph is dead.** POLITO blocks user-level consent. Do not retry.

**Reference doctrine (ratified 2026-08-20):** Outlook search is unreliable for Gianluca — a fact. So Outlook is *storage*, finding happens in a system we own.
- One reference folder in Outlook, `zzReference`, no subfolders. Everything that is not an action goes there in bulk; nothing is categorised per email.
- Finding is done by the index (step 4–5), never by Outlook. Therefore **no bulk move before search is demonstrated** — an archive you cannot interrogate is a landfill.
- Attachments are the one thing text search misses; they get their own step (step 6), later.

---

## 2. The pipeline — steps

The factory line. Each step reads the previous step's output file. `README.md` carries the detailed table (inputs, outputs, cost per step); this is the short form.

| Step | Who | What | Output |
|---|---|---|---|
| 0 | Gianluca, Outlook | Export the mailbox (all folders) to a `.pst`. **Quit Outlook before copying** — it keeps the file locked. | `maildata/<name>.pst` |
| 1 | `1-convert.sh` | `readpst`: proprietary PST → plain-text mbox, one file per folder. | `workdata/<name>/…/mbox` |
| 2 | `2-parse.py` | mbox → **one JSONL line per email**: date, from/to/cc, subject, full body, read flag, attachment names, folder, message_id. The single source every later step reads. | `workdata/<name>.jsonl` |
| 3 | `4-triage.py` — **LLM, paid, one-off** | Reads each email once; writes gist, project tag, and a verdict: ACTION / WAITING / REFERENCE / NOISE. The system prompt is the vault bootstrap (`config/bootstrap_files.txt` + `config/triage_addendum.md`), cached by the API — **do not edit it during a run** (an edit rebuilds the cache at full price). Resumable: already-triaged ids are skipped. | `workdata/<name>-ledger.jsonl` (worksheet) |
| 3′ | `5-ledger.py` — free | Renders the worksheet as a readable table. | `workdata/<name>-ledger.md` (**the ledger**) |
| 3a | Gianluca + Claude | **The review**: ACTION and WAITING lines only, ~10 s each — capture (→ nextActions / waitingFor), drop, or do now. REFERENCE and NOISE are never looked at. | GTD files updated |
| 3b | Gianluca, Outlook | **The drag**: select all → `zzReference`. Inbox = 0. Only after step 5 has passed its test. | empty inbox |
| 4 | `3-index.py` | Search index over all bodies: BM25 (exact words — names, acronyms, codes) + multilingual dense vectors (meaning, IT/EN), keyed on message_id. | `db/` |
| 5 | `q.py` | A question → BM25 + dense → fused ranking → hits grouped by thread. Claude reads the hits and answers. | an answer |
| 6 | (later) | Attachments: extract from the mbox to a flat store; keepers routed to project Dropbox folders. | files |
| 7 | `server.py` (later) | MCP server exposing `email_search` / `email_thread` / `email_stats`, so any Claude chat can call step 5 itself. | steady state |

**Now vs regime.** Step 3 (the LLM pass) runs **once**, on the backlog: it is the bankruptcy tool. After inbox-zero, Gianluca triages at arrival by hand and the recurring chain is **export → 1 → 2 → 4**, three commands, no LLM, $0, monthly. The ledger is then frozen as a historical artifact. (`embers.py` — a mechanical pre-filter — is dead: refuted on the real inbox, see EXPERIENCE.)

---

## 3. Building the code — phases

| Phase | Builds step(s) | State |
|---|---|---|
| 1 — Acquire + convert + parse | 0, 1, 2 | ✅ done 2026-08-21. Verified on the full 2026 mailbox (7,268 emails). 3 messages fail to parse (`list index out of range`), undiagnosed. |
| 2 — Ledger | 3, 3′, 3a | ✅ done 2026-08-21 (triage + render + review flow). The `done`-stamp helper for step 3a is still to write. |
| 3 — Index + search | 4, 5 | ⬜ **next build.** BM25 + dense (paraphrase-multilingual-MiniLM-L12-v2), CLI with sender/date filters, thread grouping. |
| 4 — Attachments | 6 | ⬜ later. |
| 5 — MCP server | 7 | ⬜ later. |
| 6 — Scale + steady state | monthly chain | ⬜ after the burn: monthly re-export with message_id dedup; README documents the three-command chain. **Sep 2:** push the unpushed HOME v0 (built 2026-07-11: same steps 1–2, ChromaDB index, MCP server) and salvage anything better. |

Salvaged from the abandoned `mailRead` repo, in `salvage/`: an Outlook-COM extractor (fallback if readpst ever fails) and a taxonomy seed for tags.

---

## 4. The burn — week of Aug 24–30, 2026

Goal: leave Sunday with the Inbox at zero, every commitment in GTD, and search working over the archive. Corpus: `Total-260824.pst`, the whole mailbox (~20 GB, 2022 → today).

| Day | Programs (Claude runs) | Gianluca | $ |
|---|---|---|---|
| **Mon 24** | Steps 1–2 on the full PST (~1 h). Completeness check: starts 2022, Inbox + Sent Items present, counts match Outlook. Launch step 3 on **2026 unread Inbox** (~1 h unattended). | Quit Outlook. Clear the paid step. | ≈ $18 |
| **Tue 25** | Step 3′ → ledger. Launch step 3 on **2022–25 unread Inbox**. Write the `done`-stamp helper. | Step 3a on the 2026 ledger (~1–1.5 h). | ≈ $15–25 |
| **Wed 26** | Phase 3: build steps 4–5. | Step 3a on the 2022–25 ledger. Then the **search test**: 5 real questions, right emails back in < 1 min. | $0 |
| **Thu 27** | Fix what the test exposed. | Buffer. | $0 |
| **Fri 28** | — | **Step 3b — the drag.** Inbox → `zzReference`. Re-export (step 0). | $0 |
| **Sat 29** | Steps 1–2–4 on the post-move export; README carries the monthly chain; commit + push. | — | $0 |
| **Sun 30** | — | Leave. | — |

Scope rule: the LLM reads **unread** mail only. Read mail is treated as handled (measured: ~1 real action per 50 read emails — EXPERIENCE). Model: Opus 5 — the pass that must not miss a commitment runs once; ≈ $35–45 total.

Slack: Wednesday is the only build day. If the index slips, Thursday's triage review still happens and the drag moves to Saturday.
