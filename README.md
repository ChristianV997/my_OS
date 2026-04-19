# MarketOS

MarketOS is focused on three pillars:

1. **Automated Market Research**  
   Regime detection and causal updates drive market understanding.
2. **Dropshipping**  
   Shopify order ingestion powers revenue/order signals and optimization.
3. **Publicity / Advertising**  
   Meta Ads campaign spend and bandit-weighted decisions optimize allocation.

## Run

```bash
pip install -r requirements.txt
python backend/main.py
```

## Environment variables

- `META_ACCESS_TOKEN`
- `META_AD_ACCOUNT_ID`
- `SHOPIFY_SHOP_URL`
- `SHOPIFY_ACCESS_TOKEN`
- `DOWHY_ENABLED` (default: `false`)
- `DOWHY_SKIP_REFUTATION` (default: `true`)

## CI/offline behavior

- If Shopify or Meta credentials are missing, integrations automatically use deterministic fallback data.
- Tests block outbound network usage to keep CI deterministic and offline-safe.
- Default causal DoWhy estimation is disabled unless explicitly enabled with `DOWHY_ENABLED=true`.
