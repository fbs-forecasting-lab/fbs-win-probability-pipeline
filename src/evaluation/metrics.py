"""Descriptive binary-probability evaluation; no calibration fitting."""

import numpy as np
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss


def evaluate_probabilities(labels, probabilities):
    """Score home-win probabilities; ties at 0.5 predict a home win."""
    y = np.asarray(labels)
    p = np.asarray(probabilities, dtype=float)
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p) or not len(y):
        raise ValueError("Evaluation requires matching nonempty one-dimensional arrays.")
    if not np.isin(y, [0, 1]).all() or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Evaluation requires binary labels and finite probabilities in [0, 1].")
    scores = {
        "brier_score": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "accuracy": float(accuracy_score(y, p >= 0.5)),
    }
    # Left-inclusive bins, except the last also includes 1.0. Integer bin
    # indices avoid cumulative floating-point drift in repeated addition.
    indices = np.minimum((p * 10).astype(int), 9)
    calibration = []
    for index in range(10):
        selected = indices == index
        count = int(selected.sum())
        calibration.append({
            "lower": index / 10, "upper": (index + 1) / 10,
            "upper_inclusive": index == 9, "count": count,
            "mean_predicted_probability": float(p[selected].mean()) if count else None,
            "observed_home_win_rate": float(y[selected].mean()) if count else None,
        })
    return scores, calibration
