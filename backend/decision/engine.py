import random


def decide(state):

    return [
        {"action": "test", "score": random.random()}
        for _ in range(5)
    ]
