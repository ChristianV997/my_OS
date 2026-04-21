# DropshippingOS

Autonomous operating loop focused on three pillars:
- Automated market research
- Dropshipping execution
- Publicity/advertising optimization

## Run

```bash
pip install -r requirements.txt
python backend/main.py
```

## Modules
- Automated Market Research: causal graph updates + regime detection
- Dropshipping: Shopify ingestion with CI-safe fallback data
- Publicity / Advertising: Meta Ads ingestion with CI-safe fallback data
- Decision Engine: signals + bandit weighting + confidence calibration
- Learning: velocity, acceleration, advantage, delayed rewards

## Research records schema (Pillar A)
Canonical persisted fields:
- `id` (uuid)
- `topic` (required string)
- `intent` (`buy` | `research` | `compare` | `unknown`)
- `velocity` (float)
- `competition` (0..1 float)
- `source` (adapter name)
- `freshness_ts` (ISO timestamp)
- `confidence` (0..1 float)
- `raw` (source payload JSON)
- `created_at`, `updated_at` (timestamps)
- `dedupe_key` (`{source}:{topic}:{YYYY-MM-DD-HH}`)

## Status
Core loop is aligned to market research, dropshipping, and publicity workflows with graceful degradation in CI/offline environments.
