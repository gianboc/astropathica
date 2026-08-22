# EXPERIENCE — operational facts earned by running astropathica

Descriptive, dated, public-safe. What the code taught us by running, not by reading.

- **readpst preserves the read flag** as a `Status: RO` header on read messages (absent on unread); `2-parse.py` maps it to `is_read`. Verified on a 5,358-message Inbox: 1,298 unread. (observed 2026-08-21)
- **Outlook's export wizard exports only what the local cache holds.** Exporting the mailbox root while Outlook Classic was still syncing produced a PST with Inbox but no Sent Items (the folder showed no item count in the dialog). Wait for counts next to every folder before exporting. (2026-08-21)
- **Some Italian mail servers localize the Date header** (`Sab, 22 Ago 2026 …`), which `email.utils.parsedate_to_datetime` rejects; without the fallback ~1% of messages had no date. (2026-08-21)
- **A sender/keyword filter cannot separate commitments from reference in an academic inbox.** Four mechanical rules (To-me, known senders, deadline words, threads replied in) flagged 73% of 1,298 unread and still left ~20% live items in the "safe" pile (sampled 40). The distinction is in the body; only a reader gets it. (2026-08-21)
- **Triage pass cost is dominated by the cached context, not the emails.** With a ~146k-token system prompt (the vault state) cached, a 25-email call on Opus 5 via OpenRouter costs ~$0.30 ($0.35 first measured) and ~65 s; the same on DeepSeek V4 Pro ~$0.027 and ~150 s. Every edit to the system prompt invalidates the cache: one extra ~$1.15 write on Opus. Freeze the prompt before a long run. (2026-08-21)
- **DeepSeek V4 Pro writes longer JSON than Opus** and truncated a 25-email batch at an 8k output cap; raised to 16k and added salvage of complete objects from a truncated array. (2026-08-21)
- **Opus 5 vs DeepSeek V4 Pro on the same 50 emails:** 42/50 verdict agreement, 37/50 tag agreement. DeepSeek caught one already-captured action Opus missed; DeepSeek marked five self-notes "likely resolved" without evidence (the expensive error direction for a review queue). (2026-08-21)
- **A random sample of 50 *read* emails contained 4 LLM-flagged actions (8%)**, of which the owner judged 3 as handled off-system — ~1/50 real. "Read" ≈ handled in this mailbox. (2026-08-21)
