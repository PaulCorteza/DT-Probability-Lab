
from itertools import combinations, combinations_with_replacement, product
from functools import lru_cache

from objectives import (
    OBJECTIVES,
    evaluate_objective,
    DEFAULT_DICE_CONFIG
)


# --------------------------------------------------
# 1. PRE-COMPUTE ALL UNIQUE OBJECTIVE RESULTS
# --------------------------------------------------

# The app may supply a hero-specific objective registry at runtime.
# Keep the engine's registry independent from the fixed objectives.py defaults.
OBJECTIVE_IDS = tuple(OBJECTIVES.keys())
OBJECTIVE_BITS = {
    objective_id: 1 << index
    for index, objective_id in enumerate(OBJECTIVE_IDS)
}


def configure_objectives(objective_registry):
    """Configure the registry, clearing caches only when definitions change."""
    global OBJECTIVES, OBJECTIVE_IDS, OBJECTIVE_BITS
    new_registry = dict(objective_registry)

    # Streamlit may call this repeatedly during the same rerun. Avoid destroying
    # expensive caches when the registry has not actually changed.
    if new_registry == OBJECTIVES:
        return

    OBJECTIVES = new_registry
    OBJECTIVE_IDS = tuple(OBJECTIVES.keys())
    OBJECTIVE_BITS = {
        objective_id: 1 << index
        for index, objective_id in enumerate(OBJECTIVE_IDS)
    }
    build_objective_lookup.cache_clear()
    _cached_one_reroll_state.cache_clear()


@lru_cache(maxsize=32)
def build_objective_lookup(dice_config_items, roll_length):

    dice_config = dict(dice_config_items)

    lookup = {}

    # Generate every unique combination, ignoring dice order
    for roll in combinations_with_replacement(
        range(1, 7),
        roll_length
    ):

        result_mask = 0

        for objective_id in OBJECTIVE_IDS:

            objective = OBJECTIVES[objective_id]

            if evaluate_objective(
                roll,
                objective,
                dice_config
            ):
                result_mask |= OBJECTIVE_BITS[objective_id]

        lookup[roll] = result_mask

    return lookup


def get_objective_lookup(dice_config, roll_length):

    config_key = tuple(sorted(dice_config.items()))

    return build_objective_lookup(
        config_key,
        roll_length
    )


def get_objective_mask(roll, lookup):

    return lookup[tuple(sorted(roll))]


# Enumerate unordered reroll multisets with their permutation multiplicity.
def _weighted_unordered_rolls(number_of_dice):
    total = 6 ** number_of_dice
    for values in combinations_with_replacement(range(1, 7), number_of_dice):
        counts = [values.count(face) for face in range(1, 7)]
        denominator = math.prod(math.factorial(count) for count in counts)
        weight = math.factorial(number_of_dice) // denominator
        yield values, weight, total

import math

# --------------------------------------------------
# 2. OPTIMAL ONE-REROLL CALCULATION
# --------------------------------------------------

# Cache complete one-reroll evaluations across calls (canonical state + config).
# This cache is deliberately bounded to avoid unbounded memory growth.
@lru_cache(maxsize=50000)
def _cached_one_reroll_state(roll_key, objective_ids, dice_config_key):
    return _calculate_best_reroll(
        list(roll_key), list(objective_ids), dict(dice_config_key),
        include_objective_probabilities=True
    )


def _calculate_best_reroll(
    roll,
    objective_ids,
    dice_config,
    include_objective_probabilities=True
):

    lookup = get_objective_lookup(
        dice_config,
        len(roll)
    )

    selected_mask = 0

    for objective_id in objective_ids:
        selected_mask |= OBJECTIVE_BITS[objective_id]

    best_probability = -1
    best_dice_indices = ()
    best_successful_outcomes = 0
    best_total_outcomes = 1

    # Try rerolling 0, 1, 2, 3, 4 or 5 dice

    for number_to_reroll in range(len(roll) + 1):

        for dice_indices in combinations(
            range(len(roll)),
            number_to_reroll
        ):

            successful_outcomes = 0
            total_outcomes = 6 ** number_to_reroll

            for new_values, weight, _total in _weighted_unordered_rolls(number_to_reroll):
                new_roll = sorted(roll[index] for index in range(len(roll)) if index not in dice_indices) + list(new_values)
                result_mask = get_objective_mask(new_roll, lookup)
                if result_mask & selected_mask:
                    successful_outcomes += weight

            probability = successful_outcomes / total_outcomes

            if probability > best_probability:

                best_probability = probability
                best_dice_indices = dice_indices
                best_successful_outcomes = successful_outcomes
                best_total_outcomes = total_outcomes

    # Calculate individual objective probabilities
    # under the best combined strategy

    objective_probabilities = {}

    if include_objective_probabilities:

        objective_success_counts = {
            objective_id: 0
            for objective_id in objective_ids
        }

        number_to_reroll = len(best_dice_indices)

        for new_values, weight, _total in _weighted_unordered_rolls(number_to_reroll):
            new_roll = sorted(roll[index] for index in range(len(roll)) if index not in best_dice_indices) + list(new_values)
            result_mask = get_objective_mask(new_roll, lookup)
            for objective_id in objective_ids:
                if result_mask & OBJECTIVE_BITS[objective_id]:
                    objective_success_counts[objective_id] += weight

        objective_probabilities = {
            objective_id: count / best_total_outcomes
            for objective_id, count
            in objective_success_counts.items()
        }

    return {
        "probability": best_probability,
        "dice_to_reroll": [
            index + 1
            for index in best_dice_indices
        ],
        "objective_probabilities": objective_probabilities,
        "successful_outcomes": best_successful_outcomes,
        "total_outcomes": best_total_outcomes
    }


def calculate_best_one_reroll(
    roll,
    objective_id,
    dice_config=None
):

    if dice_config is None:
        dice_config = DEFAULT_DICE_CONFIG

    result = _calculate_best_reroll(
        roll,
        [objective_id],
        dice_config,
        include_objective_probabilities=False
    )

    return {
        "probability": result["probability"],
        "dice_to_reroll": result["dice_to_reroll"]
    }


def calculate_best_one_reroll_for_objectives(
    roll,
    objective_ids,
    dice_config=None
):

    if dice_config is None:
        dice_config = DEFAULT_DICE_CONFIG

    if not objective_ids:
        raise ValueError("Select at least one objective")

    return _calculate_best_reroll(
        roll,
        objective_ids,
        dice_config
    )


# --------------------------------------------------
# 3. ANALYZE SECOND-REROLL OPTIONS
# --------------------------------------------------

def analyze_second_reroll_options(
    roll,
    first_dice_to_reroll,
    objective_ids,
    dice_config=None
):

    if dice_config is None:
        dice_config = DEFAULT_DICE_CONFIG

    dice_indices = [
        index - 1
        for index in first_dice_to_reroll
    ]

    total_probability = 0
    total_outcomes = 0
    branches = []

    # Cache exact ordered rolls within this analysis
    branch_cache = {}

    for new_values in product(
        range(1, 7),
        repeat=len(dice_indices)
    ):

        new_roll = roll.copy()

        for index, new_value in zip(
            dice_indices,
            new_values
        ):
            new_roll[index] = new_value

        roll_key = tuple(new_roll)

        if roll_key not in branch_cache:

            branch_cache[roll_key] = _cached_one_reroll_state(
                tuple(new_roll), tuple(objective_ids),
                tuple(sorted(dice_config.items()))
            )

        second_result = branch_cache[roll_key]

        total_probability += second_result["probability"]
        total_outcomes += 1

        branches.append({
            "roll": new_roll,
            "probability": second_result["probability"],
            "dice_to_reroll": second_result["dice_to_reroll"],
            "objective_probabilities": second_result[
                "objective_probabilities"
            ],
            "first_outcome_probability": (
                1 / (6 ** len(dice_indices))
            )
        })

    return {
        "expected_probability": total_probability / total_outcomes,
        "first_dice_to_reroll": first_dice_to_reroll,
        "total_outcomes": total_outcomes,
        "branches": branches
    }


# --------------------------------------------------
# 4. OPTIMAL TWO-REROLL STRATEGY
# --------------------------------------------------

def find_best_two_reroll_strategy(
    roll,
    objective_ids,
    dice_config=None
):

    if dice_config is None:
        dice_config = DEFAULT_DICE_CONFIG

    if not objective_ids:
        raise ValueError("Select at least one objective")

    best_probability = -1
    best_first_dice = []
    best_objective_probabilities = {}

    strategy_comparison = []

    # Cache second-reroll results for equivalent rolls
    cache = {}

    # Try every possible first-reroll selection

    for number_to_reroll in range(len(roll) + 1):

        for dice_indices in combinations(
            range(len(roll)),
            number_to_reroll
        ):

            probability_sum = 0

            objective_probability_totals = {
                objective_id: 0
                for objective_id in objective_ids
            }

            total_outcomes = 0

            for new_values in product(
                range(1, 7),
                repeat=number_to_reroll
            ):

                new_roll = roll.copy()

                for index, new_value in zip(
                    dice_indices,
                    new_values
                ):
                    new_roll[index] = new_value

                cache_key = (
                    tuple(sorted(new_roll)),
                    tuple(objective_ids),
                    tuple(sorted(dice_config.items()))
                )

                if cache_key not in cache:

                    second_result = _cached_one_reroll_state(
                        tuple(new_roll), tuple(objective_ids),
                        tuple(sorted(dice_config.items()))
                    )

                    cache[cache_key] = {
                        "probability": second_result["probability"],
                        "objective_probabilities": second_result[
                            "objective_probabilities"
                        ]
                    }

                second_result = cache[cache_key]

                probability_sum += second_result["probability"]

                for objective_id in objective_ids:

                    objective_probability_totals[objective_id] += (
                        second_result["objective_probabilities"].get(
                            objective_id,
                            0
                        )
                    )

                total_outcomes += 1

            combined_probability = (
                probability_sum / total_outcomes
            )

            objective_probabilities = {
                objective_id: probability / total_outcomes
                for objective_id, probability
                in objective_probability_totals.items()
            }

            first_dice = [
                index + 1
                for index in dice_indices
            ]

            strategy_comparison.append({
                "dice_to_reroll": first_dice,
                "probability": combined_probability
            })

            if combined_probability > best_probability:

                best_probability = combined_probability
                best_first_dice = first_dice
                best_objective_probabilities = objective_probabilities

    # Calculate the decision tree only once,
    # after identifying the optimal first reroll.

    best_tree = analyze_second_reroll_options(
        roll,
        best_first_dice,
        objective_ids,
        dice_config
    )

    return {
        "probability": best_probability,
        "first_dice_to_reroll": best_first_dice,
        "objective_probabilities": best_objective_probabilities,
        "strategy_comparison": strategy_comparison,
        "branches": best_tree["branches"]
    }
