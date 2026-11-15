
from objectives import evaluate_all_objectives

test_rolls = [
    [1, 2, 3, 4, 6],
    [1, 2, 3, 4, 5],
    [6, 6, 6, 6, 2],
    [6, 6, 6, 6, 6],
    [1, 2, 3, 3, 5],
    [4, 4, 4, 6, 1],  # BBBC
    [1, 2, 3, 4, 6],  # AAABC - not AAACC
    [1, 2, 3, 5, 6],  # AAABC - not AAACC
    [4, 4, 4, 5, 5],  # BBBB? 
    [6, 6, 6, 1, 2]   # CCC
]

for roll in test_rolls:

    print("\nRoll:", roll)

    results = evaluate_all_objectives(roll)

    for objective, achieved in results.items():

        if achieved:
            print("  SUCCESS:", objective)
