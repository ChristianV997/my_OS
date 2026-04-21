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

## Status
Core loop is aligned to market research, dropshipping, and publicity workflows with graceful degradation in CI/offline environments.
