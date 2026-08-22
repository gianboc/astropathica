#!/usr/bin/env python3
"""grep-level finder over a JSONL: ./q.py file.jsonl word [word...]  (all words must appear, case-insens., in from/subject/body)"""
import json,sys,re
R=[json.loads(l) for l in open(sys.argv[1],encoding='utf-8')]; W=[w.lower() for w in sys.argv[2:]]
for r in sorted(R,key=lambda r:r['date']):
    hay=(r['from_name']+' '+r['from_email']+' '+r['subject']+' '+r['body']).lower()
    if all(w in hay for w in W):
        i=hay.find(W[0]); snip=re.sub(r'\s+',' ',r['body'][max(0,i-200):i+400])
        print(f"## {r['date'][:10]} | {r['from_name']} | {r['subject'][:80]}\n   to={r['to'][:3]} cc={len(r['cc'])}\n   …{snip}…\n")
