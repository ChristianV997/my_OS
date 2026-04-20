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

## Status
Core loop is aligned to market research, dropshipping, and publicity workflows with graceful degradation in CI/offline environments.
