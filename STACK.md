# STACK — how this is built, tool by tool

Written 2026-08-21 to answer "cool, how have you done this?". Two columns of truth:
**BUILT** = exists in this repo and was run; **PLANNED** = decided in PLAN.md, not yet written.
Every stage is a separate file that reads the previous stage's output from disk, so any
stage can be re-run alone and inspected by hand.

## The shape of the pipeline

```
Outlook (Windows)          WSL / Python (stdlib only so far)                     later
────────────────           ─────────────────────────────────────────             ─────
  .pst export   ──►  readpst  ──►  mbox per folder  ──►  2-parse.py  ──►  JSONL  ──►  embers.py   (BUILT)
  (manual)           (pst-utils)                         (stdlib)                    ──►  ledger      (PLANNED, Phase 2)
                                                                                     ──►  BM25 + dense index  (PLANNED, Phase 3)
                                                                                     ──►  MCP server  (PLANNED, Phase 5)
```

Nothing in the chain writes back to Outlook. The mailbox is only ever *read*, and only via a file it exported.

## Stage 0 — the export: Outlook → `.pst`  (manual, BUILT by Microsoft)

**What a PST is.** Outlook's own container format: a single binary file holding folders, messages, attachments and per-message properties (including the read/unread flag, `PR_MESSAGE_FLAGS`). It is the most faithful export Outlook offers: CSV drops received dates, Message-IDs and threading; "Save as .msg" is one file per mail and needs Outlook to read back.
**Why manual.** Every programmatic route was tried and closed: Microsoft Graph API is blocked by the POLITO tenant (admin consent required); Outlook COM automation (`pywin32`, kept as `salvage/export_PST.py`) works but ties the pipeline to a running Windows Outlook and yields truncated bodies. The export wizard, with a date filter, is the manual button — pressed once a month in steady state.

## Stage 1 — `1-convert.sh`: `.pst` → mbox  (BUILT)

**Tool: `readpst`** from **pst-utils / libpst** (Debian/Ubuntu package `pst-utils`, GPL, C). An open-source reader of the PST format, reverse-engineered and maintained since ~2004; it walks the PST's folder tree and writes each folder as an **mbox** file — the 1970s Unix mail format: one text file, messages concatenated, each starting with a `From ` line, each message in standard RFC 5322 form (headers + MIME body). Flags used: `-r` (one directory per folder), `-8` (UTF-8), `-w` (overwrite), `-j 0` (single process, deterministic).
**Why mbox and not something modern.** Because the next stage then needs *no library at all* — Python ships an mbox parser. The whole value of readpst is turning a proprietary format into one that every tool on Earth can read.

## Stage 2 — `2-parse.py`: mbox → JSONL  (BUILT, stdlib only)

**Tools: Python 3.10 standard library** — `mailbox` (iterates messages in an mbox), `email` with `email.policy.default` (parses headers and MIME parts: decodes encoded subjects, base64/quoted-printable bodies, charsets), `email.utils` (address lists, RFC-2822 dates → ISO 8601), `html.parser` (turns HTML-only bodies into text), `hashlib`, `json`, `re`.
**Output: JSONL** — one JSON object per line, one line per email. Chosen because it streams (no need to hold 50k emails in memory), greps, and diffs; every later stage reads it. Fields: `message_id`, `in_reply_to`, `references` (the three RFC headers that make threading possible without any heuristics), `date`, `from_name/from_email`, `to[]`, `cc[]`, `subject`, `subject_norm` (Re:/Fwd:/R:/I: prefixes stripped, lower-cased — the fallback thread key), `folder`, `body`, `attachments[]` (filename, size, MIME type — contents come in Phase 4).
**Two deliberate design choices.** (1) Body = `text/plain` part if present, else HTML rendered to text — never both. (2) A *conservative* quoted-tail stripper: cuts only at unambiguous reply markers (`-----Original Message-----`, `Da:/Inviato:`, `From:/Sent:` blocks, `On … wrote:`, `Il … ha scritto:`). Conservative because the previous build taught that aggressive stripping eats real content; leftover quotes cost nothing but index size.
**Dedup key:** `Message-ID`. Monthly re-exports will overlap; the same ID is skipped, so overlapping exports are safe. Messages without one get a synthetic stable ID hashed from date+from+subject.

## Stage 2b — `embers.py`: the extraction half of the test  (BUILT, stdlib only)

Not a search tool — a **mechanical filter** encoding the Two-Speed Doctrine's "query, don't read". Four rules, no judgment, no LLM: `TO` (my address in To, not only Cc), `PWR` (sender matches `config/power_senders.txt`), `DL` (deadline vocabulary from `config/deadline_words.txt` in subject or body head), `THR` (thread in which I myself sent a message — via `References`/`In-Reply-To` or `subject_norm`). Anything firing a rule is an *ember* (a possible commitment — a human decides); everything else is reference by definition. Writes the ranked ember list and a random sample of non-embers for the falsification skim. Config is three plain text files so the rules can be tuned without touching code.

## Phase 2 — the ledger  (PLANNED)

One line per email: `date | sender | subject | one-line gist | probable project tag`, in a single markdown/CSV file. Gist and tag come from an **LLM pass** (Claude, batched ~25 emails per call, JSON out) seeded by `salvage/taxonomy-seed.md`. The ledger is the first *finding aid*: `grep` over it answers "what did X send in May" with no index at all. It exists before, and independently of, any search engine.

## Phase 3 — hybrid search  (PLANNED)

Two retrievers combined, because email fails each alone:
- **BM25** (lexical ranking; the algorithm behind Lucene/Elasticsearch) — exact tokens: project codes, surnames, acronyms, grant numbers. The previous build lacked this and was weak on precisely those.
- **Dense embeddings** via **sentence-transformers** model `paraphrase-multilingual-MiniLM-L12-v2` (small, runs on CPU, trained on IT+EN among 50 languages) — meaning-level matches: "the thing with the Norwegians about the patent" finds Maryam's email without sharing a word with it. Stored in **ChromaDB** (embedded local vector database, no server).
- Scores fused (reciprocal-rank fusion), results grouped by thread (union-find over `references` + `subject_norm`), filterable by sender and date. Same stack pattern as the sibling project `lexicanum`, with the multilingual model as the one deliberate divergence.

## Phase 5 — MCP server  (PLANNED)

**MCP (Model Context Protocol)**: the standard by which Claude Desktop / Claude Code call local tools over stdio. `server.py` exposes three tools — `email_search`, `email_thread`, `email_stats` — so a Claude session can search the archive and reconstruct a thread itself. Mirrors lexicanum's server; shares the retrieval code with the CLI so the two cannot drift.

## Constraints that shaped every choice

Read-only on the mailbox; everything local (`maildata/`, `workdata/`, `db/` gitignored; nothing cloud); stdlib-first (the first three stages need *no* `pip install` — only readpst from apt); each stage's output is a plain file you can open. See PLAN.md for the doctrine these serve.
