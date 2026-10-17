# HANDOFF — where things stand

**Corpus:** `workdata/corpus.jsonl` → `261017-Full.jsonl`, a clean full export of 2026-10-17 (51,197 emails, 2015 → 2026-10-17). Source PST in `maildata/261017-Full.pst`. The August review queue (`Total-260824-ledger.*`, `-review.*`) is frozen history; it still joins to the corpus by Message-ID.

**To refresh:** export the delta (wizard filter `Received: last month` or `this month` — never a typed date), quit Outlook, then `1-convert.sh` → `2-parse.py` → `6-merge.py corpus-new.jsonl 261017-Full.jsonl <delta>.jsonl`. Every few months replace the corpus with a clean full export (`Received: anytime`) instead. Details and pitfalls: `experience/EXPERIENCE.md`.

**Finding:** `q.py workdata/corpus.jsonl word [word…]`; attachments come out of `workdata/261017-Full/**/mbox` with `mailbox` + `get_payload(decode=True)`. No index yet (Phase 3 unbuilt).
