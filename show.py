#!/usr/bin/env python3
"""Print review-queue emails by number: ./show.py 7 [12 13 ...]. Numbers from workdata/<name>-review.md."""
import json, sys
name = 'workdata/Total-260824'
idx = json.load(open(f'{name}-review-index.json'))
recs = {json.loads(l)['message_id']: json.loads(l) for l in open(f'{name}.jsonl')}
for n in sys.argv[1:]:
    e = recs[idx[n]]
    print(f"===== #{n}  {e['date'][:16]}  from {e.get('from_name')} <{e.get('from_email')}>\nto: {', '.join(e.get('to',[]))[:200]}\nsubject: {e['subject']}\nattachments: {[a.get('filename') for a in e.get('attachments',[])]}\n\n{e['body'][:3000]}\n")
