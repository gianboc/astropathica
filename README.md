# astropathica

Local, read-only search over an exported Outlook mailbox. Doctrine and phases: `PLAN.md`. Tools explained: `STACK.md`.

## Requirements

- WSL/Linux with Python 3.10+ (stages 1–2b use the standard library only)
- `readpst` from pst-utils: `sudo apt install -y pst-utils`
- Later phases (search index): `pip install` lines will be added here when they land

## Run

```bash
./1-convert.sh maildata/<file>.pst        # PST -> workdata/<file>/ (mbox per folder)
./2-parse.py   workdata/<file>            # -> workdata/<file>.jsonl
./embers.py    workdata/<file>.jsonl      # -> <file>-embers.md + <file>-sample.md
```

`maildata/`, `workdata/`, `db/` are gitignored — mail never enters the repo.
