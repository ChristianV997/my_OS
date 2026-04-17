import numpy as np


def roas_velocity(history):
    if len(history) < 2:
        return 0
    return history[-1] - history[-2]


def roas_acceleration(history):
    if len(history) < 3:
        return 0
    v1 = history[-1] - history[-2]
    v2 = history[-2] - history[-3]
    return v1 - v2


def advantage(actual, counterfactual):
    return actual - counterfactual
