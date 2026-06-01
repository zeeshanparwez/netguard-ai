"""
Markov chain math — pure functions with no FastAPI or pandas dependency.
All functions accept numpy arrays and plain Python lists; nothing HTTP-specific.
"""

from typing import List, Optional

import numpy as np

from backend.config import VALID_STATES


def compute_failure_curves(
    transition_matrix: np.ndarray,
    states: List[str],
    hours: int = 168,
) -> dict:
    """
    Cumulative failure probability for each non-failure starting state over N hours.

    Algorithm:
      1. Start with 100% probability mass in the chosen state.
      2. Each step: multiply vector by the transition matrix (one Markov step).
      3. Accumulate the mass that lands in Failure.
      4. Zero out the Failure bucket so it is not double-counted next step.

    Returns:
        { "Healthy": [p_hour1, p_hour2, ...], "Warning": [...], ... }
    """
    failure_idx = states.index("Failure") if "Failure" in states else len(states) - 1
    curves: dict = {}

    for start_idx, start_state in enumerate(states):
        if start_idx == failure_idx:
            continue

        vec = np.zeros(len(states))
        vec[start_idx] = 1.0
        cumulative = 0.0
        probs: List[float] = []

        for _ in range(hours):
            vec = vec @ transition_matrix
            new_fail = float(vec[failure_idx])
            cumulative += new_fail
            probs.append(round(min(cumulative, 1.0), 4))

            # Remove absorbed mass to avoid double-counting in future steps
            if new_fail > 0:
                surviving = 1.0 - new_fail
                if surviving > 0:
                    for j in range(len(states)):
                        if j != failure_idx:
                            vec[j] = vec[j] / surviving * (1.0 - new_fail)
                vec[failure_idx] = 0.0

        curves[start_state] = probs

    return curves


def compute_mttf(
    transition_matrix: np.ndarray,
    states: List[str],
) -> dict:
    """
    Mean Time to Failure via the absorbing Markov chain fundamental matrix.

    Formula: N = (I − Q)⁻¹
      Q  = sub-matrix of transient → transient transitions
      N  = fundamental matrix (expected visits to each transient state)
      t  = N.sum(axis=1) → expected steps before absorption (= MTTF in hours)

    Returns:
        { "Healthy": 33.7, "Warning": 31.9, ... } or None if matrix is singular.
    """
    n = len(states)

    # Absorbing states: self-loop probability >= 0.99
    absorbing = [i for i in range(n) if transition_matrix[i, i] >= 0.99]
    if not absorbing:
        absorbing = [n - 1]

    transient = [i for i in range(n) if i not in absorbing]
    if not transient:
        return {}

    Q = transition_matrix[np.ix_(transient, transient)]

    try:
        N = np.linalg.inv(np.eye(len(transient)) - Q)
        t = N.sum(axis=1)
        return {
            states[transient[i]]: round(float(t[i]), 2)
            for i in range(len(transient))
        }
    except np.linalg.LinAlgError:
        return {states[transient[i]]: None for i in range(len(transient))}


def estimate_transition_matrix(state_sequence: List[str]) -> np.ndarray:
    """
    Maximum likelihood estimate of the transition matrix from observed state sequences.

    Counts every consecutive (from_state → to_state) pair, then normalises
    each row to sum to 1. Rows with zero observed transitions receive a
    uniform distribution to prevent NaN values.

    Returns:
        np.ndarray of shape (len(VALID_STATES), len(VALID_STATES))
    """
    n   = len(VALID_STATES)
    idx = {s: i for i, s in enumerate(VALID_STATES)}
    counts = np.zeros((n, n))

    for i in range(len(state_sequence) - 1):
        from_s, to_s = state_sequence[i], state_sequence[i + 1]
        if from_s in idx and to_s in idx:
            counts[idx[from_s]][idx[to_s]] += 1

    row_sums = counts.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1   # avoid division by zero for unseen states
    return counts / row_sums


def validate_matrix(
    matrix_list: List[List[float]],
    states: List[str],
) -> Optional[str]:
    """
    Validate a user-supplied transition matrix.
    Returns an error message string if invalid, or None if OK.
    """
    n = len(states)
    mat = np.array(matrix_list, dtype=float)

    if mat.shape != (n, n):
        return f"Matrix must be {n}×{n} to match {n} states"

    if (mat < 0).any():
        return "Transition probabilities cannot be negative"

    row_sums = mat.sum(axis=1)
    if not np.allclose(row_sums, 1.0, atol=0.02):
        bad = [
            f"{states[i]}={round(float(row_sums[i]), 3)}"
            for i in range(n)
            if abs(float(row_sums[i]) - 1.0) > 0.02
        ]
        return f"These rows don't sum to 1.0: {bad}"

    return None
