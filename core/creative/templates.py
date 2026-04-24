TEMPLATES = [
    {
        "name": "problem_solution",
        "structure": ["hook", "problem", "solution", "cta"],
    },
    {
        "name": "before_after",
        "structure": ["hook", "before", "after", "cta"],
    },
    {
        "name": "social_proof",
        "structure": ["hook", "review", "benefits", "cta"],
    },
]


def apply_template(script_parts: dict, template: dict) -> str:
    """Assemble script parts in the order defined by *template*."""
    return "\n".join(script_parts.get(p, "") for p in template["structure"])
