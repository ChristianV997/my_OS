# MarketOS v4

Autonomous decision system with causal learning and delayed feedback.

## Run

```bash
pip install -r requirements.txt
python backend/main.py
```

## Modules
- Decision Engine (signals + bandit + causal)
- Learning (velocity, acceleration, advantage)
- Causal Graph (correlation-based)
- Delayed Rewards (time-aware updates)
- Production Integration Layer (Meta/Shopify ingestion, profit loop, control API, alerts)

## Status
Core loop integrated with execution bridge + control surface.
