# COSTS — measured, per model, for the triage pass (step 3)

Setup: vault bootstrap as cached system prompt (~146k tokens tokenized), 25 emails per call (~30k tokens),
via OpenRouter. Costs are OpenRouter-reported per call, **with cache hits** (first call of a run pays the
cache write, ~3× one call). Extrapolations assume the 2026-08-21 corpus: 1,298 unread / 5,358 Inbox-2026.
Re-measure when the bootstrap or batch size changes — the bootstrap read dominates for cheap models.

| Model (OpenRouter id) | $/M in / out | per 25-email call | 1,298 unread | 5,358 inbox-2026 | sec/call | Quality note (50-email head-to-head, 2026-08-21) |
|---|---|---|---|---|---|---|
| `anthropic/claude-opus-5` | 5 / 25 | **$0.35** | ≈ $18 | ≈ $76 (≈ $38 with `:batch`) | ~63 | Safer triager: follows "unsure → ACTION"; cites bootstrap precisely; missed 1/50 already-captured action |
| `anthropic/claude-fable-5` | 10 / 50 | ≈ $0.70 (est.) | ≈ $36 | ≈ $150 (≈ $75 batch) | — | not tested |
| `anthropic/claude-sonnet-5` | 2 / 10 (intro) | ≈ $0.15 (est.) | ≈ $8 | ≈ $32 | — | not tested |
| `deepseek/deepseek-v4-pro` | 0.50 / 1.0 | **$0.027** | ≈ $1.5 | ≈ $6 | ~150 | 42/50 verdict agreement with Opus; caught the 1 Opus miss; but guesses "likely resolved" on 5 self-notes → needs a tightened addendum; output longer, hit 8k cap once (now 16k + salvage) |
| `deepseek/deepseek-v4-flash` | 0.075 / 0.15 | ≈ $0.005 (est.) | ≈ $0.3 | ≈ $1 | — | not tested |

Lever besides the model: **batch size**. The cached bootstrap is re-read every call; 50 emails/call halves that share (Opus ≈ $0.26/25 emails equivalent).

Comparison artefacts: `workdata/asd-compare.md` (gitignored — contains mail).
