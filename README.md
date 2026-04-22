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

## Integrations and CI-safe fallbacks

- Shopify and Meta Ads integrations automatically use simulated fallback data when credentials or SDKs are unavailable.
- Set `SHOPIFY_SHOP_URL`, `SHOPIFY_ACCESS_TOKEN`, `META_ACCESS_TOKEN`, and `META_AD_ACCOUNT_ID` to enable live API reads.
- Core validation: `python -m compileall -q .` and `pytest tests/ -v`.

## Run on Replit

1. Import this repository into Replit.
2. Replit will use `.replit` to install `requirements.txt` and start FastAPI automatically.
3. Open the webview and use:
   - `GET /status` for health
   - `/docs` for interactive API UI

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
