from collections import Counter

# Default mapping for the current character. Character-specific mappings
# will be introduced when the character selector is implemented.
DEFAULT_DICE_CONFIG = {
    1: "A",
    2: "A",
    3: "A",
    4: "B",
    5: "B",
    6: "C",
}

# Master objective library.
# For combination objectives, "letters" specifies minimum counts, not exact
# counts. For example, BBBCC also satisfies BBBC.
OBJECTIVES = {
    "small_straight": {
        "name": "Small Straight",
        "type": "straight",
        "dice_required": 4,
    },
    "large_straight": {
        "name": "Large Straight",
        "type": "straight",
        "dice_required": 5,
    },
    "mini_ultimate": {
        "name": "Mini Ultimate",
        "type": "letter",
        "letter": "C",
        "minimum": 4,
    },
    "ultimate": {
        "name": "Ultimate",
        "type": "letter",
        "letter": "C",
        "minimum": 5,
    },
    "BBBC": {
        "name": "BBBC",
        "type": "combination",
        "letters": {"B": 3, "C": 1},
    },
    "AAACC": {
        "name": "AAACC",
        "type": "combination",
        "letters": {"A": 3, "C": 2},
    },
    "AAABB": {
        "name": "AAABB",
        "type": "combination",
        "letters": {"A": 3, "B": 2},
    },
    "CCC": {
        "name": "CCC",
        "type": "combination",
        "letters": {"C": 3},
    },

    # Newly added objectives
    "ABCC": {
        "name": "ABCC",
        "type": "combination",
        "letters": {"A": 1, "B": 1, "C": 2},
    },
    "ABBCC": {
        "name": "ABBCC",
        "type": "combination",
        "letters": {"A": 1, "B": 2, "C": 2},
    },
    "BBB": {
        "name": "BBB",
        "type": "combination",
        "letters": {"B": 3},
    },
    "BBBB": {
        "name": "BBBB",
        "type": "combination",
        "letters": {"B": 4},
    },
    "ACCC": {
        "name": "ACCC",
        "type": "combination",
        "letters": {"A": 1, "C": 3},
    },
    "AACC": {
        "name": "AACC",
        "type": "combination",
        "letters": {"A": 2, "C": 2},
    },
    "AABC": {
        "name": "AABC",
        "type": "combination",
        "letters": {"A": 2, "B": 1, "C": 1},
    },
    "AABB": {
        "name": "AABB",
        "type": "combination",
        "letters": {"A": 2, "B": 2},
    },
    "BBBCC": {
        "name": "BBBCC",
        "type": "combination",
        "letters": {"B": 3, "C": 2},
    },
    "ABBB": {
        "name": "ABBB",
        "type": "combination",
        "letters": {"A": 1, "B": 3},
    },
    "BBCC": {
        "name": "BBCC",
        "type": "combination",
        "letters": {"B": 2, "C": 2},
    },
}


def has_straight(roll, required_length):
    """Return True when the roll contains the required consecutive values."""
    unique_values = sorted(set(roll))
    for start in range(len(unique_values) - required_length + 1):
        window = unique_values[start:start + required_length]
        if all(
            window[index] + 1 == window[index + 1]
            for index in range(required_length - 1)
        ):
            return True
    return False


def _roll_letters(roll, dice_config):
    """Translate die numbers into their configured letters."""
    return Counter(dice_config[value] for value in roll)


def has_letter_combination(roll, letter, minimum, dice_config):
    """Check whether at least 'minimum' dice map to the requested letter."""
    counts = _roll_letters(roll, dice_config)
    return counts[letter] >= minimum


def has_combination(roll, required_letters, dice_config):
    """Check minimum counts for every letter in a combination objective."""
    counts = _roll_letters(roll, dice_config)
    return all(
        counts[letter] >= minimum
        for letter, minimum in required_letters.items()
    )


def evaluate_objective(roll, objective, dice_config=None):
    """Evaluate one objective against a five-die roll."""
    if dice_config is None:
        dice_config = DEFAULT_DICE_CONFIG

    objective_type = objective["type"]

    if objective_type == "straight":
        return has_straight(roll, objective["dice_required"])

    if objective_type == "letter":
        return has_letter_combination(
            roll,
            objective["letter"],
            objective["minimum"],
            dice_config,
        )

    if objective_type == "combination":
        return has_combination(
            roll,
            objective["letters"],
            dice_config,
        )

    raise ValueError(f"Unknown objective type: {objective_type}")


def evaluate_all_objectives(roll, dice_config=None):
    """Return a dictionary showing whether each library objective is achieved."""
    if dice_config is None:
        dice_config = DEFAULT_DICE_CONFIG

    return {
        objective_id: evaluate_objective(roll, objective, dice_config)
        for objective_id, objective in OBJECTIVES.items()
    }
