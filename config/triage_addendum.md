# Triage addendum — read after the bootstrap above

You are triaging Gianluca Boccardo's POLITO inbox (address gianluca.boccardo@polito.it) for the 2026 backlog bankruptcy. The bootstrap above is the live state of his work: people, projects, tags, what is already captured in nextActions/waitingFor, what is resolved. Use it — a sender's importance, a project's liveness, and whether a loop is already closed all come from there, not from the email text alone.

For EACH email produce one JSON object:
- "id": the message_id as given
- "gist": one line, ≤ 25 words, in the email's language (IT or EN), saying what the email IS and what it wants, concretely (names, amounts, dates)
- "tag": the most probable project tag from projectTags.md (e.g. IND:18, 32A1:BATCAT, 32C:ELECTRANT, TEACH, DEPT, ADM, PERSONAL, STANDALONE). Use NOISE for newsletters/notifications/spam.
- "verdict": exactly one of
  - ACTION — Gianluca must do something that is NOT already captured in nextActions.md (check!)
  - WAITING — someone owes him something, not already in waitingFor.md
  - REFERENCE — worth keeping, nothing to do (FYI, CC'd threads, closed loops, resolved items, calendar accepts)
  - NOISE — newsletters, automated notifications, vendor mail, mailing-list chatter, spam
- "why": ≤ 15 words justifying the verdict, citing the bootstrap when relevant ("already in nextActions under IND:05", "loop resolved 08-20")

Rules: the email date matters — a deadline in the past is REFERENCE unless the consequence is still live. Calendar accept/decline notifications are REFERENCE. Student grade-registration requests are ACTION under TEACH unless older than 60 days. Reviewer invitations are ACTION (decline is also an action). When unsure between ACTION and REFERENCE, choose ACTION — Gianluca reviews ACTION lines, never REFERENCE lines.

Output: a JSON array only, no prose, no code fences.

If you mark REFERENCE because the action is already captured in nextActions.md or waitingFor.md, quote that line verbatim in "why". Never mark REFERENCE on a guess that something was "likely resolved": if the email itself shows no resolution, it is ACTION.
