def generate_swot(comp, econ, signal):
    return {
        "strengths": ["high margin"] if econ["margin_pct"] > 0.5 else [],
        "weaknesses": ["high competition"] if comp["ad_density"] > 0.7 else [],
        "opportunities": ["trend rising"] if signal.get("trend_score", 0) > 50 else [],
        "threats": ["saturation"] if comp["competitors"] > 30 else [],
    }
