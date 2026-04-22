def detect_transition(prev_regime, current_regime):
    if prev_regime is None:
        return False
    return prev_regime != current_regime
