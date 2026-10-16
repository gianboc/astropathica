#!/usr/bin/env python3
"""Step 6 (steady state): merge several parsed exports into one corpus, deduplicated on Message-ID.
Stdlib only. Usage: ./6-merge.py out.jsonl old.jsonl [newer.jsonl ...]
Files are read in the order given; a later file wins on collision (its folder / is_read are the
current ones — mail dragged to zzReference or read since the last export shows up that way).
Overlap between exports is free: re-exporting an already-parsed month adds nothing."""
import json, sys
from pathlib import Path

def main(out, srcs):
    recs = {}; order = []; stats = []
    for s in srcs:
        n = new = 0
        for line in open(s, encoding='utf-8'):
            r = json.loads(line); mid = r['message_id']; n += 1
            if mid not in recs: order.append(mid); new += 1
            recs[mid] = r
        stats.append((Path(s).name, n, new))
    rows = sorted((recs[m] for m in order), key=lambda r: r['date'])
    with open(out, 'w', encoding='utf-8') as fo:
        for r in rows: fo.write(json.dumps(r, ensure_ascii=False) + '\n')
    for name, n, new in stats: print(f'{n:7d} read  {new:7d} new   {name}')
    dated = [r['date'][:10] for r in rows if r['date']]
    print(f'{len(rows)} emails -> {out}   ({min(dated)} → {max(dated)})')

if __name__ == '__main__':
    if len(sys.argv) < 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
