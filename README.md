# MarketOS v4

Autonomous decision system with causal learning and delayed feedback.

## Run

```bash
pip install -r requirements.txt
python backend/main.py
```

## Integrations and CI-safe fallbacks

- Shopify and Meta Ads integrations automatically use simulated fallback data when credentials or SDKs are unavailable.
- Set `SHOPIFY_SHOP_URL`, `SHOPIFY_ACCESS_TOKEN`, `META_ACCESS_TOKEN`, and `META_AD_ACCOUNT_ID` to enable live API reads.
- Core validation: `python -m compileall -q .` and `pytest tests/ -v`.

## Modules
- Decision Engine (signals + bandit + causal)
- Learning (velocity, acceleration, advantage)
- Causal Graph (correlation-based)
- Delayed Rewards (time-aware updates)

## Status
Core loop integrated. Next: multi-horizon prediction.
