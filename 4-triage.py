#!/usr/bin/env python3
"""Step 3: LLM pass over the JSONL -> ledger (gist, tag, verdict per email).
Runs against OpenRouter (OpenAI-compatible endpoint, stdlib urllib only). Key: $OPENROUTER_API_KEY.
The vault bootstrap (config/bootstrap_files.txt) + config/triage_addendum.md form the system prompt,
sent with cache_control so repeated calls pay ~10% for it.
Usage: ./4-triage.py workdata/asd.jsonl [--limit N] [--offset N] [--unread | --read-sample N --seed S] [--folder Inbox] [--year 2026 | --year 2022,2023] [--batch 25] [--model anthropic/claude-opus-5] [--suffix NAME] [--max-cost USD] [--dry-run]
Output: workdata/<name>-ledger.jsonl (append; resumable — already-triaged ids are skipped) and workdata/<name>-ledger.md
"""
import json, os, re, sys, time, urllib.request, datetime
from pathlib import Path

URL = "https://openrouter.ai/api/v1/chat/completions"
BODY_CHARS = 3500   # per email; bodies beyond this are cut (tail is mostly quoted history)

def build_bootstrap():
    parts = []
    for line in Path('config/bootstrap_files.txt').read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        tail = line.startswith('tail30:'); p = Path(line.split(':', 1)[1] if tail else line)
        txt = p.read_text(encoding='utf-8', errors='replace')
        if tail: txt = '\n'.join(txt.splitlines()[-30:])
        parts.append(f"===== BEGIN {p} =====\n{txt}\n===== END {p} =====\n")
    return "SEGMENTUM BOOTSTRAP (reconstructed for the email triage).\n\n" + "\n".join(parts)

def fmt(r):
    body = r['body'][:BODY_CHARS] + (' […cut]' if len(r['body']) > BODY_CHARS else '')
    att = ', '.join(a['filename'] for a in r['attachments'] if a['filename']) or '-'
    return (f"<email id=\"{r['message_id']}\">\ndate: {r['date'][:16]}  read: {r.get('is_read')}\n"
            f"from: {r['from_name']} <{r['from_email']}>\nto: {', '.join(r['to'][:6])}\ncc: {', '.join(r['cc'][:6])}\n"
            f"subject: {r['subject']}\nattachments: {att}\n\n{body}\n</email>")

def call(system, user, model, key):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]},
            {"role": "user", "content": user}],
        "max_tokens": 16000, "temperature": 0,
        "usage": {"include": True},
    }
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/gianboc/astropathica", "X-Title": "astropathica triage"})
    for attempt in range(8):                       # ~25 min of backoff total before giving up
        try:
            with urllib.request.urlopen(req, timeout=600) as resp: return json.load(resp)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='replace')[:300]
            if e.code in (408, 429, 500, 502, 503, 504, 524) and attempt < 7:
                wait = min(300, 15 * 2 ** attempt); print(f"  HTTP {e.code}, retry in {wait}s: {msg[:80]}"); time.sleep(wait); continue
            raise SystemExit(f"HTTP {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            if attempt < 7:
                wait = min(300, 15 * 2 ** attempt); print(f"  network error, retry in {wait}s: {e}"); time.sleep(wait); continue
            raise SystemExit(f"network error: {e}")

def parse_json(text):
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    i, j = text.find('['), text.rfind(']')
    try: return json.loads(text[i:j + 1])
    except json.JSONDecodeError:  # truncated output: salvage the complete objects
        objs = []
        for m in re.finditer(r'\{[^{}]*\}', text[i:]):
            try: objs.append(json.loads(m.group()))
            except json.JSONDecodeError: pass
        if not objs: raise
        print(f"  (truncated output: salvaged {len(objs)} objects)"); return objs

def render(ledger_jsonl, out_md, recs_by_id):
    """Ledger = worksheet JOIN latest export. Rows whose email is gone from the export are dropped;
    read flag comes from the export; verdict shown (with its date) only while the row is not 'done'."""
    rows = [json.loads(l) for l in open(ledger_jsonl, encoding='utf-8')]
    rows = [x for x in rows if x['id'] in recs_by_id]
    rows.sort(key=lambda x: recs_by_id[x['id']]['date'])
    esc = lambda s: str(s).replace('|', '\\|').replace('\n', ' ')
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write("| date | read | verdict (triaged) | tag | from | subject | gist | why |\n|---|---|---|---|---|---|---|---|\n")
        for x in rows:
            r = recs_by_id[x['id']]
            v = '' if x.get('done') else f"{x['verdict']} ({x.get('triaged','')})"
            f.write(f"| {r['date'][:10]} | {'R' if r.get('is_read') else 'U'} | {v} | {x['tag']} | {esc(r.get('from_name') or r.get('from_email',''))} | {esc(r.get('subject','')[:70])} | {esc(x['gist'])} | {esc(x['why']) if not x.get('done') else ''} |\n")

def main():
    a = sys.argv[1:]; path = a[0]
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d
    limit, offset, batch = int(opt('--limit', 0)), int(opt('--offset', 0)), int(opt('--batch', 30))
    model, dry, unread = opt('--model', 'anthropic/claude-opus-5'), '--dry-run' in a, '--unread' in a
    suffix = opt('--suffix', ''); max_cost = float(opt('--max-cost', 0))
    key = os.environ.get('OPENROUTER_API_KEY') or sys.exit("OPENROUTER_API_KEY not set")
    recs = [json.loads(l) for l in open(path, encoding='utf-8')]
    by_id = {r['message_id']: r for r in recs}
    if unread: recs = [r for r in recs if not r.get('is_read')]
    if '--folder' in a: recs = [r for r in recs if r.get('folder','').split('/')[-2:-1] == [opt('--folder','')] or r.get('folder','').endswith('/'+opt('--folder','')+'/mbox')]
    if '--year' in a:
        ys = opt('--year','').split(','); recs = [r for r in recs if (r.get('date') or '')[:4] in ys]
    if '--read-sample' in a:
        import random; random.seed(int(opt('--seed', 1)))
        recs = random.sample([r for r in recs if r.get('is_read')], int(opt('--read-sample', 50)))
    recs.sort(key=lambda r: (r.get('subject_norm') or r.get('subject','').lower(), r['date']))   # thread members adjacent -> same batch
    base = str(Path(path).with_suffix('')); lj, lm = f"{base}-ledger{suffix}.jsonl", f"{base}-ledger{suffix}.md"
    done = {json.loads(l)['id'] for l in open(lj, encoding='utf-8')} if Path(lj).exists() else set()
    todo = [r for r in recs if r['message_id'] not in done][offset:]
    if limit: todo = todo[:limit]
    system = build_bootstrap() + "\n\n" + Path('config/triage_addendum.md').read_text()
    print(f"bootstrap ≈ {len(system)//4:,} tokens (chars/4) | {len(todo)} emails to triage, {len(done)} already done | model {model}")
    # Pack whole threads into batches (never split a thread unless it alone exceeds the batch size).
    tkey = lambda r: r.get('subject_norm') or r.get('subject', '').lower()
    threads, cur = [], []
    for r in todo:
        if cur and tkey(r) != tkey(cur[-1]): threads.append(cur); cur = []
        cur.append(r)
    if cur: threads.append(cur)
    batches, cur = [], []
    for t in threads:
        while len(t) > batch: batches.append(t[:batch]); t = t[batch:]      # oversize thread: split
        if cur and len(cur) + len(t) > batch: batches.append(cur); cur = []
        cur.extend(t)
    if cur: batches.append(cur)
    split = sum(1 for t in threads if len(t) > batch)
    print(f"{len(threads)} threads packed into {len(batches)} batches of <= {batch}; {split} oversize threads split")
    if dry: print(fmt(todo[0]) if todo else 'nothing'); return
    tot_in = tot_cached = tot_out = 0; cost = 0.0
    for i, chunk in enumerate(batches):
        user = f"Triage these {len(chunk)} emails. Return a JSON array with one object per email, same order.\n\n" + "\n\n".join(fmt(r) for r in chunk)
        t0 = time.time(); resp = call(system, user, model, key)
        text = resp['choices'][0]['message']['content']; u = resp.get('usage', {})
        try: items = parse_json(text)
        except Exception as e:
            Path(f"{base}-triage-error-{i+1}.txt").write_text(text); print(f"!! batch {i}: unparseable output saved; {e}"); continue
        got = {x['id']: x for x in items if isinstance(x, dict) and 'id' in x}
        with open(lj, 'a', encoding='utf-8') as f:
            for r in chunk:
                x = got.get(r['message_id'])
                if x: f.write(json.dumps({'id': r['message_id'], 'gist': x.get('gist', ''), 'tag': x.get('tag', ''), 'verdict': x.get('verdict', ''), 'why': x.get('why', ''), 'triaged': datetime.date.today().isoformat()}, ensure_ascii=False) + '\n')
                else: print(f"  missing verdict for {r['message_id']}")
        pin, pout = u.get('prompt_tokens', 0), u.get('completion_tokens', 0)
        cached = (u.get('prompt_tokens_details') or {}).get('cached_tokens', 0)
        c = u.get('cost', 0) or 0; cost += c; tot_in += pin; tot_cached += cached; tot_out += pout
        if max_cost and cost > max_cost: print(f"!! spend ${cost:.2f} > --max-cost {max_cost}: stopping (resumable)"); break
        print(f"batch {i+1}/{len(batches)}: {len(got)}/{len(chunk)} verdicts | in {pin:,} (cached {cached:,}) out {pout:,} | ${c:.3f} | {time.time()-t0:.0f}s")
    render(lj, lm, by_id)
    print(f"TOTAL in {tot_in:,} (cached {tot_cached:,}) out {tot_out:,} | ${cost:.2f} | -> {lm}")

if __name__ == '__main__': main()
