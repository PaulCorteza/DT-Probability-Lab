"""Exact probability calculations for a five-die Dice Throne-style roll."""

from itertools import product
from collections import Counter


def is_success(roll, target):
    """Return True if a completed five-die roll meets the selected target."""
    counts = Counter(roll)

    if target == "Three of a kind":
        return max(counts.values()) >= 3
    if target == "Four of a kind":
        return max(counts.values()) >= 4
    if target == "Five of a kind":
        return max(counts.values()) == 5
    if target == "At least four sixes":
        return counts[6] >= 4
    if target == "Small straight (1–5)":
        return set(range(1, 6)).issubset(set(roll))
    if target == "Large straight (2–6)":
        return set(range(2, 7)).issubset(set(roll))

    raise ValueError(f"Unknown target: {target}")


def probability_for_keep(current_roll, keep_indices, target):
    """
    Calculate the exact probability of reaching target after rerolling
    every die whose index is not in keep_indices.
    """
    kept = [current_roll[i] for i in keep_indices]
    reroll_count = len(current_roll) - len(kept)

    if reroll_count == 0:
        return float(is_success(current_roll, target))

    successes = 0
    total = 6 ** reroll_count

    for new_values in product(range(1, 7), repeat=reroll_count):
        final_roll = list(kept)
        final_roll.extend(new_values)
        if is_success(final_roll, target):
            successes += 1

    return successes / total


def best_strategy(current_roll, target):
    """Try every possible set of dice to keep and return the best strategy."""
    best_probability = -1.0
    best_keep = []

    # There are 2^5 = 32 possible keep/reroll decisions.
    for mask in range(1 << len(current_roll)):
        keep_indices = [
            i for i in range(len(current_roll))
            if mask & (1 << i)
        ]
        probability = probability_for_keep(current_roll, keep_indices, target)

        # On a tie, prefer keeping more dice (fewer unnecessary rerolls).
        if (
            probability > best_probability + 1e-12
            or (
                abs(probability - best_probability) <= 1e-12
                and len(keep_indices) > len(best_keep)
            )
        ):
            best_probability = probability
            best_keep = keep_indices

    return best_keep, best_probability
