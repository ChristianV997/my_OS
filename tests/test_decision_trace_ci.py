def compute_score(w, c, v, a, conf):
    return (w + c + v + a) * conf


def test_final_score_changes_with_components():
    base = compute_score(1, 1, 1, 1, 1)

    # vary each component
    variations = [
        compute_score(2, 1, 1, 1, 1),
        compute_score(1, 2, 1, 1, 1),
        compute_score(1, 1, 2, 1, 1),
        compute_score(1, 1, 1, 2, 1),
        compute_score(1, 1, 1, 1, 0.5),
    ]

    for v in variations:
        assert v != base, "Final score not sensitive to component change"
