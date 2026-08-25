#!/usr/bin/env python3
"""Stamp review-queue rows done: ./stamp.py 1 2 5-9  (numbers from the review file)."""
import json,sys,datetime
name='workdata/Total-260824'; idx=json.load(open(f'{name}-review-index.json')); ns=set()
for a in sys.argv[1:]:
    if '-' in a: x,y=map(int,a.split('-')); ns|=set(range(x,y+1))
    else: ns.add(int(a))
ids={idx[str(n)] for n in ns}; lj=f'{name}-ledger.jsonl'; rows=[json.loads(l) for l in open(lj)]
for r in rows:
    if r['id'] in ids: r['done']=datetime.date.today().isoformat()
open(lj,'w').write(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)); print('done:',sum(1 for r in rows if r.get('done')))
