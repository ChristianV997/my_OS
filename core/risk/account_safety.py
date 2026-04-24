def throttle_launch(num_ads: int) -> str:
    """Return "limit" when too many ads are being launched at once."""
    if num_ads > 5:
        return "limit"
    return "ok"


def warmup_mode(account_age_days: int) -> str:
    """Return spend tier based on account age (new accounts must ramp slowly)."""
    if account_age_days < 7:
        return "low_spend"
    return "normal"
