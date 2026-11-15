
from probability_engine import calculate_best_one_reroll
from probability_engine import find_best_two_reroll_strategy

roll = [4, 5, 6, 6, 1]

for objective_id in [
    "small_straight",
    "large_straight",
    "mini_ultimate",
    "ultimate",
    "BBBC",
    "AAACC",
    "AAABB",
    "CCC"
]:

    result = calculate_best_one_reroll(
        roll,
        objective_id
    )

    print("\nObjective:", objective_id)

    print(
        "Best probability:",
        round(result["probability"] * 100, 2),
        "%"
    )

    print(
        "Reroll dice:",
        result["dice_to_reroll"]
    )


from probability_engine import calculate_best_one_reroll_for_objectives

selected_objectives = ["BBBC", "CCC", "AAACC"]

result = calculate_best_one_reroll_for_objectives(
    roll,
    selected_objectives
)

print("\nMULTIPLE OBJECTIVE ANALYSIS")

print(
    "Combined probability:",
    round(result["probability"] * 100, 2),
    "%"
)

print("Recommended dice to reroll:", result["dice_to_reroll"])

print(
    "Successful outcomes:",
    result["successful_outcomes"],
    "/",
    result["total_outcomes"]
)

print("\nIndividual objective probabilities:")

for objective_id, probability in result["objective_probabilities"].items():

    print(
        objective_id,
        ":",
        round(probability * 100, 2),
        "%"
    )


from probability_engine import analyze_second_reroll_options

roll = [4, 5, 6, 6, 1]

selected_objectives = ["BBBC", "CCC", "AAACC"]

result = analyze_second_reroll_options(
    roll,
    [3, 5],
    selected_objectives
)

print("\nSECOND REROLL ANALYSIS")

print(
    "First reroll dice:",
    result["first_dice_to_reroll"]
)

print(
    "Expected final probability:",
    round(result["expected_probability"] * 100, 2),
    "%"
)

print("Possible first-reroll outcomes:", result["total_outcomes"])

print("\nDECISION TREE BRANCHES")

for branch in result["branches"]:

    print(
        "Roll:", branch["roll"],
        "| Second reroll:", branch["dice_to_reroll"],
        "| Probability:",
        round(branch["probability"] * 100, 2),
        "%"
    )

print("\nOPTIMAL TWO-REROLL STRATEGY")

result = find_best_two_reroll_strategy(
    roll,
    selected_objectives
)

print(
    "Best first reroll:",
    result["first_dice_to_reroll"]
)

print(
    "Final probability:",
    round(result["probability"] * 100, 2),
    "%"
)

print("\nIndividual objective probabilities:")

for objective_id, probability in result["objective_probabilities"].items():

    print(
        objective_id,
        ":",
        round(probability * 100, 2),
        "%"
    )

print("\nAlternative first-reroll strategies:")

for strategy in sorted(
    result["strategy_comparison"],
    key=lambda x: x["probability"],
    reverse=True
)[:5]:

    print(
        "Reroll:", strategy["dice_to_reroll"],
        "| Probability:",
        round(strategy["probability"] * 100, 2),
        "%"
    )

print("\nOPTIMAL DECISION TREE")

print(
    "Total branches:",
    len(result["branches"])
)

for branch in result["branches"][:10]:

    print(
        "First result:", branch["roll"],
        "| Second reroll:", branch["dice_to_reroll"],
        "| Final probability:",
        round(branch["probability"] * 100, 2),
        "%"
    )