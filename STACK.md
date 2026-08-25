# STACK — how each step is built, tool by tool

Companion to `PLAN.md`, which defines the vocabulary (**steps** = pipeline stages, run every time; **phases** = build sessions, done once). This file answers "what tool does step N use, and why that one". Step numbers are PLAN's. Every step is a separate file that reads the previous step's output from disk, so any step can be re-run alone and inspected by hand.

## The shape

```
Outlook (Windows)        WSL / Python                                                    money
─────────────────        ────────────────────────────────────────────────────────        ─────
step 0  .pst export ──► step 1  readpst ──► mbox per folder ──► step 2  2-parse.py ──► JSONL
(manual)                (pst-utils)                            (stdlib)                 $0
                                                                    │
                                          ┌─────────────────────────┼──────────────────────────┐
                                          ▼                         ▼                          ▼
                                 step 3  4-triage.py         step 4  3-index.py          step 6  attachments
                                 LLM → worksheet → ledger    BM25 + dense → db/          (later)
                                 (one-off, PAID)             (monthly, $0)
                                          │                         │
                                          ▼                         ▼
                                 step 3a review (Gianluca)   step 5  q.py  →  step 7  server.py (MCP)
                                 step 3b drag → zzReference  (ask questions, $0)
```

Nothing writes back to Outlook. The mailbox is only ever *read*, and only through a file it exported.

## Step 0 — the export: Outlook → `.pst`  (manual · built by Microsoft)

**What a PST is.** Outlook's own container: one binary file holding folders, messages, attachments and per-message properties, including the read/unread flag. It is the most faithful export Outlook offers: CSV drops received dates, Message-IDs and threading; "Save as .msg" is one file per mail and needs Outlook to read it back.
**Why manual.** Every programmatic route was tried and closed: Microsoft Graph is blocked by the POLITO tenant (admin consent); Outlook COM automation (kept as `salvage/export_PST.py`) works but ties the pipeline to a running Windows Outlook and truncates bodies. The export wizard is the button — pressed once a month at regime. Two pitfalls, both recorded in EXPERIENCE: the date filter is `MM/DD` whatever the locale, and Outlook holds a lock on the file until it is quit.

## Step 1 — `1-convert.sh`: `.pst` → mbox  (built · Phase 1)

**Tool: `readpst`** from **pst-utils / libpst** (apt package, GPL, C): an open-source, reverse-engineered PST reader maintained since ~2004. It walks the folder tree and writes each folder as an **mbox** file — the 1970s Unix mail format: one text file, messages concatenated, each starting with a `From ` line, each in standard RFC 5322 form. Flags: `-r` (a directory per folder), `-8` (UTF-8), `-w` (overwrite), `-j 0` (single process, deterministic order).
**Why mbox.** The next step then needs no library at all — Python ships an mbox parser. readpst's whole value is turning a proprietary format into one every tool on Earth can read. Measured: the 19.7 GB full mailbox converts in ~15 min.

## Step 2 — `2-parse.py`: mbox → JSONL  (built · Phase 1 · stdlib only)

**Tools:** `mailbox` (iterates an mbox), `email` with `policy.default` (headers, MIME parts, charsets, base64/quoted-printable), `email.utils` (addresses, dates → ISO 8601, with a fallback for Italian-localised `Date:` headers), `html.parser` (HTML-only bodies → text), `hashlib`, `json`, `re`.
**Output: JSONL** — one JSON object per line, one line per email. It streams (no need to hold 50k emails in memory), greps, and diffs; every later step reads it. Fields: `message_id`, `in_reply_to`, `references` (the three headers that make threading possible with no heuristics), `date`, `from_name`/`from_email`, `to[]`, `cc[]`, `subject`, `subject_norm` (Re:/Fwd:/R:/I: stripped, lower-cased — the fallback thread key), `folder`, `is_read` (from readpst's `Status: RO` header), `body`, `attachments[]` (name, size, MIME type — contents are step 6).
**Design choices.** Body = `text/plain` part if present, else HTML rendered — never both. A *conservative* quoted-tail stripper cuts only at unambiguous reply markers (`-----Original Message-----`, `Da:/Inviato:`, `From:/Sent:`, `On … wrote:`, `Il … ha scritto:`) — aggressive stripping was shown to eat real content; leftover quotes only cost index size.
**Dedup key:** `Message-ID`. Monthly re-exports overlap; the same ID is skipped. Messages without one get a stable synthetic ID hashed from date+from+subject. Measured: 49,412 emails parse in ~12 min; 3 fail (`list index out of range`, undiagnosed).

## Step 3 — `4-triage.py` + `5-ledger.py`: JSONL → ledger  (built · Phase 2 · the paid step)

**Tool: an LLM over the OpenRouter API** (OpenAI-compatible endpoint, called with stdlib `urllib` — no SDK). Default model `anthropic/claude-opus-5`; DeepSeek V4 Pro measured as the cheap alternative (COSTS.md).
**The system prompt** is the vault bootstrap — the same files a Claude session receives at wake-up, listed in `config/bootstrap_files.txt` — plus `config/triage_addendum.md` (the verdict rules). It is sent with `cache_control`, so the API stores it once and every later call re-reads it at ~10% price. That is why the prompt must not be edited during a run: any change invalidates the cache and the next call pays the full write.
**Per call:** 25 emails (bodies cut at 3,500 chars — the tail is quoted history) → JSON out: gist, project tag, verdict (ACTION / WAITING / REFERENCE / NOISE), one-line reason. Selection flags: `--unread`, `--folder Inbox`, `--year 2026` (or `2022,2023`). Resumable: ids already in the worksheet are skipped, so a killed run continues where it stopped.
**Two files:** the **worksheet** `<name>-ledger.jsonl` (append-only, written once per email, never re-sent) and the **ledger** `<name>-ledger.md`, rendered from it by `5-ledger.py` (free, any time: keeps only rows whose email is still in the corpus, shows the verdict until the row is stamped `done`).
**Step 3a** (the review) and **3b** (the drag to `zzReference`) are human acts on the ledger; no tool.

`embers.py` (a four-rule mechanical pre-filter) sits beside these as **dead code**: refuted on the real inbox — a filter cannot tell a commitment from reference; only a reader can. Kept as the record.

## Step 4 — `3-index.py`: JSONL → search index  (not built · Phase 3)

Two retrievers, because email defeats each alone:
- **BM25** (lexical ranking; the algorithm under Lucene/Elasticsearch) — exact tokens: project codes, surnames, acronyms, grant numbers. The HOME v0 lacked this and was weak on precisely those.
- **Dense embeddings** via **sentence-transformers**, model `paraphrase-multilingual-MiniLM-L12-v2` (small, CPU, IT+EN among 50 languages) — meaning-level matches: "the thing with the Norwegians about the patent" finds the email without sharing a word with it. Stored in **ChromaDB** (embedded, local, no server).
Keyed on `message_id`; monthly runs index new ids only. Same stack pattern as the sibling project `lexicanum`; the multilingual model is the one deliberate divergence.

## Step 5 — `q.py`: a question → ranked emails  (not built · Phase 3)

Query → BM25 + dense → **reciprocal-rank fusion** → hits grouped into threads (union-find over `references` + `subject_norm`), filterable by sender and date. Prints full emails; Claude reads them and answers. The CLI and the MCP server share this code so they cannot drift.

## Step 6 — attachments  (not built · Phase 4)

Extract from the mbox (`mailbox` + `get_payload(decode=True)` — verified to work for a handful of files) into a flat store with hash names, one ledger row per file; keepers routed to project Dropbox folders by hand.

## Step 7 — `server.py`: MCP  (not built · Phase 5)

**MCP (Model Context Protocol):** the standard by which Claude Desktop / Claude Code call local tools over stdio. Three tools — `email_search`, `email_thread`, `email_stats` — so any Claude session searches the archive and reconstructs a thread itself. Mirrors lexicanum's server.

## Constraints that shaped every choice

Read-only on the mailbox; everything local (`maildata/`, `workdata/`, `db/` gitignored; nothing cloud); stdlib-first (steps 1–3 need no `pip install` — only readpst from apt; step 4 is the first to need packages); each step's output is a plain file you can open. The doctrine these serve is in PLAN.md § 1.
