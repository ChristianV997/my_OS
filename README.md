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

## Status
Core loop integrated. Next: multi-horizon prediction.
