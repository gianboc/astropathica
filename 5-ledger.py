#!/usr/bin/env python3
"""Render the ledger (readable markdown) = worksheet JOIN current corpus. No LLM, no cost.
Usage: ./5-ledger.py workdata/asd.jsonl [--suffix NAME]
Reads  workdata/asd.jsonl            (corpus: emails currently in the export)
       workdata/asd-ledger{suffix}.jsonl  (worksheet: one LLM-written line per message_id, append-only)
Writes workdata/asd-ledger{suffix}.md      (ledger: rows whose email still exists; read flag from corpus;
                                            verdict shown with its triage date only while not 'done')
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
triage = __import__('4-triage')
a = sys.argv[1:]; path = a[0]; suffix = a[a.index('--suffix') + 1] if '--suffix' in a else ''
by_id = {json.loads(l)['message_id']: json.loads(l) for l in open(path, encoding='utf-8')}
base = str(Path(path).with_suffix('')); lj, lm = f"{base}-ledger{suffix}.jsonl", f"{base}-ledger{suffix}.md"
n_ws = sum(1 for _ in open(lj, encoding='utf-8'))
triage.render(lj, lm, by_id)
n_led = sum(1 for _ in open(lm, encoding='utf-8')) - 2
print(f"worksheet {n_ws} lines -> ledger {n_led} rows ({n_ws - n_led} dropped: email no longer in corpus) -> {lm}")
