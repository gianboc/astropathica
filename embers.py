#!/usr/bin/env python3
"""Half A of the test: split a JSONL slice into embers (possible commitments) and non-embers.
Mechanical rules only — no reading, no LLM. Usage: ./embers.py workdata/<name>.jsonl [--sample 30] [--seed 1] [--unread]
Writes <name>-embers.md (ranked, with the rules that fired) and <name>-sample.md (random non-embers to skim).
Rules: TO   = my address in To (not only Cc)
       PWR  = sender matches config/power_senders.txt
       DL   = deadline vocabulary (config/deadline_words.txt) in subject or body head
       THR  = thread (subject_norm or References) containing a message I sent
"""
import json, random, sys
from pathlib import Path

def load(p): return [l.strip().lower() for l in Path(p).read_text().splitlines() if l.strip() and not l.startswith('#')]

def main(path, sample=30, seed=1, unread=False):
    me=set(load('config/me.txt')); pwr=load('config/power_senders.txt'); dl=load('config/deadline_words.txt')
    recs=[json.loads(l) for l in open(path,encoding='utf-8')]
    if unread: recs=[r for r in recs if not r.get('is_read')]
    my_threads={r['subject_norm'] for r in recs if r['from_email'] in me}
    my_ids={r['message_id'] for r in recs if r['from_email'] in me}
    embers=[]; rest=[]
    for r in recs:
        if r['from_email'] in me: continue      # my own mail is never an ember
        fired=[]
        if me & set(r['to']): fired.append('TO')
        who=(r['from_name']+' '+r['from_email']).lower()
        if any(p in who for p in pwr): fired.append('PWR')
        head=(r['subject']+' '+r['body'][:1500]).lower()
        if any(w in head for w in dl): fired.append('DL')
        if r['subject_norm'] in my_threads or my_ids & set(r['references']) or r['in_reply_to'] in my_ids: fired.append('THR')
        (embers if fired else rest).append((fired,r))
    order={'THR':0,'PWR':1,'TO':2,'DL':3}
    embers.sort(key=lambda x:(min(order[f] for f in x[0]), x[1]['date']))
    def line(r,tag=''): return f"- {r['date'][:10]} | {r['from_name'] or r['from_email']} | {r['subject'][:90]}{tag}"
    base=Path(path).with_suffix(''); base=Path(str(base)+('-unread' if unread else ''))
    Path(f'{base}-embers.md').write_text('\n'.join(line(r,f"  `{'+'.join(f)}`") for f,r in embers)+'\n',encoding='utf-8')
    random.seed(seed); pick=random.sample(rest,min(sample,len(rest)))
    Path(f'{base}-sample.md').write_text('\n'.join(line(r) for _,r in pick)+'\n',encoding='utf-8')
    n=len(recs); ne=len(embers)
    print(f"{n} emails: {ne} embers ({100*ne/max(n,1):.0f}%), {len(rest)} non-embers; sample of {len(pick)} written")
    for k in order: print(f"  {k}: {sum(1 for f,_ in embers if k in f)}")
    print(f"-> {base}-embers.md, {base}-sample.md")

if __name__=='__main__':
    a=sys.argv[1:]; s=int(a[a.index('--sample')+1]) if '--sample' in a else 30; sd=int(a[a.index('--seed')+1]) if '--seed' in a else 1
    main(a[0],s,sd,'--unread' in a)
