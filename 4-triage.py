#!/usr/bin/env python3
"""Step 3: LLM pass over the JSONL -> ledger (gist, tag, verdict per email).
Runs against OpenRouter (OpenAI-compatible endpoint, stdlib urllib only). Key: $OPENROUTER_API_KEY.
The vault bootstrap (config/bootstrap_files.txt) + config/triage_addendum.md form the system prompt,
sent with cache_control so repeated calls pay ~10% for it.
Usage: ./4-triage.py workdata/asd.jsonl [--limit N] [--offset N] [--unread] [--batch 25] [--model anthropic/claude-opus-5] [--suffix NAME] [--dry-run]
Output: workdata/<name>-ledger.jsonl (append; resumable — already-triaged ids are skipped) and workdata/<name>-ledger.md
"""
import json, os, re, sys, time, urllib.request
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
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=600) as resp: return json.load(resp)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='replace')[:300]
            if e.code in (429, 500, 502, 503) and attempt < 3: time.sleep(10 * (attempt + 1)); continue
            raise SystemExit(f"HTTP {e.code}: {msg}")

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
    rows = [json.loads(l) for l in open(ledger_jsonl, encoding='utf-8')]
    rows.sort(key=lambda x: recs_by_id.get(x['id'], {}).get('date', ''))
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write("| date | verdict | tag | from | subject | gist | why |\n|---|---|---|---|---|---|---|\n")
        for x in rows:
            r = recs_by_id.get(x['id'], {})
            esc = lambda s: str(s).replace('|', '\\|').replace('\n', ' ')
            f.write(f"| {r.get('date','')[:10]} | {x['verdict']} | {x['tag']} | {esc(r.get('from_name') or r.get('from_email',''))} | {esc(r.get('subject','')[:70])} | {esc(x['gist'])} | {esc(x['why'])} |\n")

def main():
    a = sys.argv[1:]; path = a[0]
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d
    limit, offset, batch = int(opt('--limit', 0)), int(opt('--offset', 0)), int(opt('--batch', 25))
    model, dry, unread = opt('--model', 'anthropic/claude-opus-5'), '--dry-run' in a, '--unread' in a
    suffix = opt('--suffix', '')
    key = os.environ.get('OPENROUTER_API_KEY') or sys.exit("OPENROUTER_API_KEY not set")
    recs = [json.loads(l) for l in open(path, encoding='utf-8')]
    by_id = {r['message_id']: r for r in recs}
    if unread: recs = [r for r in recs if not r.get('is_read')]
    recs.sort(key=lambda r: r['date'])
    base = str(Path(path).with_suffix('')); lj, lm = f"{base}-ledger{suffix}.jsonl", f"{base}-ledger{suffix}.md"
    done = {json.loads(l)['id'] for l in open(lj, encoding='utf-8')} if Path(lj).exists() else set()
    todo = [r for r in recs if r['message_id'] not in done][offset:]
    if limit: todo = todo[:limit]
    system = build_bootstrap() + "\n\n" + Path('config/triage_addendum.md').read_text()
    print(f"bootstrap ≈ {len(system)//4:,} tokens (chars/4) | {len(todo)} emails to triage, {len(done)} already done | model {model}")
    if dry: print(fmt(todo[0]) if todo else 'nothing'); return
    tot_in = tot_cached = tot_out = 0; cost = 0.0
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        user = f"Triage these {len(chunk)} emails. Return a JSON array with one object per email, same order.\n\n" + "\n\n".join(fmt(r) for r in chunk)
        t0 = time.time(); resp = call(system, user, model, key)
        text = resp['choices'][0]['message']['content']; u = resp.get('usage', {})
        try: items = parse_json(text)
        except Exception as e:
            Path(f"{base}-triage-error-{i}.txt").write_text(text); print(f"!! batch {i}: unparseable output saved; {e}"); continue
        got = {x['id']: x for x in items if isinstance(x, dict) and 'id' in x}
        with open(lj, 'a', encoding='utf-8') as f:
            for r in chunk:
                x = got.get(r['message_id'])
                if x: f.write(json.dumps({'id': r['message_id'], 'gist': x.get('gist', ''), 'tag': x.get('tag', ''), 'verdict': x.get('verdict', ''), 'why': x.get('why', '')}, ensure_ascii=False) + '\n')
                else: print(f"  missing verdict for {r['message_id']}")
        pin, pout = u.get('prompt_tokens', 0), u.get('completion_tokens', 0)
        cached = (u.get('prompt_tokens_details') or {}).get('cached_tokens', 0)
        c = u.get('cost', 0) or 0; cost += c; tot_in += pin; tot_cached += cached; tot_out += pout
        print(f"batch {i//batch+1}: {len(got)}/{len(chunk)} verdicts | in {pin:,} (cached {cached:,}) out {pout:,} | ${c:.3f} | {time.time()-t0:.0f}s")
    render(lj, lm, by_id)
    print(f"TOTAL in {tot_in:,} (cached {tot_cached:,}) out {tot_out:,} | ${cost:.2f} | -> {lm}")

if __name__ == '__main__': main()
