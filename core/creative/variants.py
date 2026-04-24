from core.creative.generator import generate_creative


def generate_variants(product: str, base_angle: str) -> list[dict]:
    """Generate creative variants across multiple ad angles."""
    angles = [
        base_angle,
        "problem-solution",
        "social-proof",
        "curiosity hook",
        "before-after",
    ]

    variants = []
    for angle in angles:
        script = generate_creative(product, angle)
        variants.append({"angle": angle, "script": script})

    return variants
