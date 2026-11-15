import streamlit as st

from dice_engine import probability_for_keep, best_strategy

st.set_page_config(page_title="Dice Throne Probability Calculator", page_icon="🎲")
st.title("🎲 Dice Throne Probability Calculator")
st.caption("An exact-probability calculator for five six-sided dice.")

st.markdown(
    "Enter your current roll, choose which dice to keep, and calculate "
    "your chance of reaching a target after rerolling the others."
)

targets = [
    "Three of a kind",
    "Four of a kind",
    "Five of a kind",
    "At least four sixes",
    "Small straight (1–5)",
    "Large straight (2–6)",
]

target = st.selectbox("What are you trying to achieve?", targets)

st.subheader("Your current roll")
dice_columns = st.columns(5)
current_roll = []
keep_indices = []

for i, column in enumerate(dice_columns):
    with column:
        value = st.selectbox(
            f"Die {i + 1}",
            options=[1, 2, 3, 4, 5, 6],
            index=0,
            key=f"die_{i}",
        )
        current_roll.append(value)
        keep = st.checkbox("Keep", value=False, key=f"keep_{i}")
        if keep:
            keep_indices.append(i)

st.divider()

if st.button("Calculate my probability", type="primary", use_container_width=True):
    probability = probability_for_keep(current_roll, keep_indices, target)
    st.metric("Chance of success", f"{probability:.2%}")
    st.write(
        f"You are keeping **{len(keep_indices)}** dice and rerolling "
        f"**{5 - len(keep_indices)}**."
    )

st.subheader("Find the optimal strategy")
if st.button("Find best dice to keep", use_container_width=True):
    best_keep, best_probability = best_strategy(current_roll, target)
    st.metric("Best achievable probability", f"{best_probability:.2%}")

    if best_keep:
        st.write("Keep: " + ", ".join(f"Die {i + 1} (value {current_roll[i]})" for i in best_keep))
    else:
        st.write("Reroll all five dice.")

    st.write(
        "The recommendation checks all 32 possible keep/reroll combinations. "
        "If multiple strategies have the same probability, it prefers keeping more dice."
    )

with st.expander("What does 'exact probability' mean?"):
    st.write(
        "Instead of simulating thousands of rolls, the calculator enumerates "
        "every possible result of the dice you reroll. For example, rerolling "
        "two dice has 6 × 6 = 36 equally likely outcomes. It counts how many "
        "of those outcomes meet your target."
    )
