# astropathica

Local, read-only search over an exported Outlook mailbox. Doctrine and phases: `PLAN.md`. Tools explained: `STACK.md`.

## Who does what — the pipeline in one table

| # | Input | Action | Done by | Output | Used for |
|---|---|---|---|---|---|
| 0 | Outlook mailbox | Export (date filter, all folders) | **Gianluca**, by hand, ~monthly | `maildata/<name>.pst` | step 1 |
| 1 | `.pst` | Convert to mbox | **readpst** (deterministic) | `workdata/<name>/…/mbox`, one text file per folder | step 2 only |
| 2 | mbox files | Parse headers, bodies, attachments, read flag | **`2-parse.py`** (deterministic) | `workdata/<name>.jsonl` — one line per email, full body | steps 3, 4, 5 — the single source everything reads |
| 3 | `.jsonl` + vault bootstrap context | **Read each email once**; write gist, project tag, verdict ACTION / WAITING / REFERENCE / NOISE | **LLM** (API, batched) — `4-triage.py` | **the ledger** `ledger.md`: date, sender, subject, gist, tag, verdict per email | 3a, 3b, 3c |
| 3a | ledger, ACTION + WAITING lines only | Confirm / overrule each; write GTD lines | **Gianluca** (10 s/line) + **Claude** typing into nextActions / waitingFor | live GTD files | the burn-down itself |
| 3b | ledger, REFERENCE lines | Bulk-move those emails to `zzReference` | **Gianluca**, in Outlook, select-and-drag | inbox = 0 | done |
| 3c | ledger (all lines) | Scan / grep as table of contents | Gianluca or Claude, any time | "what exists from May about X" in 10 s | quick looks — not the search engine |
| 4 | `.jsonl` bodies + ledger gists | Build two indexes: BM25 (exact words) + dense vectors (meaning, IT/EN) | **`3-index.py`** (deterministic; embedding model runs locally) | `db/` | step 5 |
| 5 | a question | Translate to a query → BM25 + dense → fuse (RRF) → group hits into threads | **Claude** asks; **the index** (deterministic) answers with the top emails | ranked full emails | step 6 |
| 6 | ranked full emails | Read them, reconstruct the story, answer | **Claude** (LLM) | the answer | Gianluca |
| 7 | steps 5–6 | Expose `email_search` / `email_thread` as MCP tools so Claude calls them itself in any chat | **`server.py`** | same as 5–6, no manual commands | steady state |

Three facts the table makes visible: the LLM reads every email exactly once (step 3) and afterwards only what search returns (step 6) — everything in between is deterministic programs. The ledger and the index are two different objects built from the same JSONL: ledger = human-readable catalog + verdicts (triage now, quick looks later); index = machine-searchable bodies (interrogation later); neither replaces the other. Gianluca touches three things only: the export button (0), the ACTION/WAITING review (3a), the drag to `zzReference` (3b).

**Where we are (2026-08-21):** steps 0–2 built and run on the full 2026 inbox (5,358 emails, 1,298 unread; Sent Items still missing from the export). Step 3 next.

## The five files — name, writer, trigger, cost

| Name | File | Written by | Trigger | Cost |
|---|---|---|---|---|
| **export** | `maildata/<name>.pst` | Gianluca, Outlook export wizard | manual, ~monthly | $0 |
| **corpus** | `workdata/<name>.jsonl` | `1-convert.sh` + `2-parse.py` | after every export; rebuilt completely — always "the emails currently in the export" | $0, seconds |
| **worksheet** | `workdata/<name>-ledger.jsonl` | `4-triage.py` — the LLM API call | only for `message_id`s that have no line yet (new mail); append-only, a line is written once and never re-sent | **the only paid step** (see COSTS.md) |
| **ledger** | `workdata/<name>-ledger.md` | `5-ledger.py` — plain script, no LLM | on demand; keeps only worksheet rows whose email is still in the corpus; read flag from the corpus; verdict shown (with triage date) only while the row is not `done` | $0, seconds |
| **index** | `db/` | `3-index.py` (Phase 3, not built) | after every export, new emails only | $0 (local model) |

**A change in the mailbox (read, moved, deleted) costs nothing to propagate:**

```
change in Outlook → export → ./1-convert.sh + ./2-parse.py → ./5-ledger.py        ($0)
new mail only     → ./4-triage.py  (skips every id already in the worksheet)       ($)
```

Deleted emails: their worksheet line stays (harmless; prevents re-triage), their ledger row disappears at the next render. Reviewed ACTION lines: marked `done: <date>` in the worksheet by a one-line script at review time (step 3a; script not yet written) — the ledger then hides the verdict. Action state never lives in the ledger; it lives in the GTD files.

### What happens to each file when the mailbox changes

Nothing is live: no file changes until a script is run. A change in Outlook reaches the repo only through the next export.

**You delete an email in Outlook** → next export lacks it → `2-parse.py`: no line in `asd.jsonl` → `asd-ledger.jsonl`: its line stays, untouched → `5-ledger.py`: row gone from `asd-ledger.md` → `3-index.py` (future): entry removed. GTD files untouched. $0.

**You mark an email read/unread** → next export + `2-parse.py`: `is_read` flips in `asd.jsonl` → `asd-ledger.jsonl`: untouched → `5-ledger.py`: the `read` column changes in `asd-ledger.md`. Nothing else. $0.

**An email triaged ACTION, and the action gets done.** Only during the backlog bankruptcy (the verdict column does not exist at regime). At the review session you rule on each ACTION/WAITING row of `asd-ledger.md`: capture (line written to nextActions/waitingFor), drop, or do-it-now (2-minute rule). In all three cases a one-line script stamps `done: <date>` on that row of `asd-ledger.jsonl` ($0); `5-ledger.py` then hides the verdict. The email is moved to `zzReference` like all the others. Doing the captured action later happens from nextActions, which is the only place action state lives — the ledger is never updated for it.

### Now vs regime

| | Backlog bankruptcy (now) | Regime (after inbox-zero) |
|---|---|---|
| Who decides what is an action | LLM proposes (`4-triage.py`), Gianluca rules | Gianluca, at arrival |
| Verdict column in `asd-ledger.jsonl` | yes, one-off | not produced |
| `4-triage.py` | full pass on the backlog | **not run** (a gist-only monthly catalog is possible, ~$0.50/month, but is switched off by decision 2026-08-21) |
| Monthly chain | — | export → `1-convert.sh` → `2-parse.py` → `3-index.py` — three scripts, $0 |
| `asd-ledger.md` | the review queue + catalog | frozen: the bankruptcy artifact, not updated |

## Requirements

- WSL/Linux with Python 3.10+ (stages 1–2b use the standard library only)
- `readpst` from pst-utils: `sudo apt install -y pst-utils`
- Later phases (search index): `pip install` lines will be added here when they land

## Run

```bash
./1-convert.sh maildata/<file>.pst        # PST -> workdata/<file>/ (mbox per folder)
./2-parse.py   workdata/<file>            # -> workdata/<file>.jsonl
./embers.py    workdata/<file>.jsonl      # (dead — see PLAN Lifetimes) mechanical ember filter
./4-triage.py  workdata/<file>.jsonl      # LLM pass -> <file>-ledger.jsonl (worksheet), paid
./5-ledger.py  workdata/<file>.jsonl      # render <file>-ledger.md from worksheet + corpus, free
```

`maildata/`, `workdata/`, `db/` are gitignored — mail never enters the repo.
