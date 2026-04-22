from backend.monitoring.failure_classifier import classify_failure


def test_failure_classifier_runs():
    result = classify_failure()

    assert isinstance(result, str)
    assert len(result) > 0
