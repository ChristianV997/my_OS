from simulation.replay import deterministic_event_id


def test_deterministic_event_id_is_stable():

    row = {
        "product": "LED Lamp",
        "hook": "This changed everything",
        "angle": "viral",
        "platform": "tiktok",
        "label": "WINNER",
        "ts": 123456,
    }

    a = deterministic_event_id(row)
    b = deterministic_event_id(row)

    assert a == b


def test_deterministic_event_id_changes_with_payload():

    row_a = {
        "product": "LED Lamp",
        "hook": "A",
        "angle": "viral",
        "platform": "tiktok",
        "label": "WINNER",
        "ts": 123456,
    }

    row_b = {
        "product": "LED Lamp",
        "hook": "B",
        "angle": "viral",
        "platform": "tiktok",
        "label": "WINNER",
        "ts": 123456,
    }

    assert deterministic_event_id(row_a) != deterministic_event_id(row_b)
