import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from textwrap import dedent

# A small custom component renders the dice and reports clicks back to Python.
dice_cards_component = components.declare_component(
    "dice_cards",
    path=str(Path(__file__).parent / "dice_component_build"),
)
import random
import re
import pandas as pd
from itertools import combinations, product
from collections import Counter

from objectives import OBJECTIVES, DEFAULT_DICE_CONFIG, evaluate_objective
from hero_database import HERO_PROFILES, CARD_OBJECTIVES
import probability_engine as probability_engine_module
from probability_engine import (
    calculate_best_one_reroll,
    calculate_best_one_reroll_for_objectives,
    find_best_two_reroll_strategy,
)


st.set_page_config(
    page_title="Dice Throne Strategy Lab",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Sign-in is temporarily disabled during development.

st.title("🎲 Dice Throne Strategy Lab")
st.caption(
    "Find the strongest reroll strategy for your current roll and selected objectives."
)

st.markdown(
    """
    <style>
    /* Responsive sidebar: allow Streamlit's native collapse/expand control. */
    [data-testid="stSidebar"] [data-testid="stSelectbox"] {
        min-width: 68px !important;
    }

    /* Collapsed launcher: style the button itself, the element we know is visible. */
    [data-testid="stExpandSidebarButton"] {
        position: fixed !important;
        left: 0 !important;
        top: 0 !important;
        height: 100vh !important;
        width: 48px !important;
        z-index: 100000 !important;
        overflow: visible !important;
    }

    /* Reserve space for the collapsed rail so it never covers the app content. */
    body:has([data-testid="stExpandSidebarButton"]) .block-container {
        padding-left: calc(48px + 1rem) !important;
    }
    [data-testid="stExpandSidebarButton"] {
        position: fixed !important;
        left: 0 !important;
        top: 0 !important;
        height: 100vh !important;
        min-height: 100vh !important;
        width: 48px !important;
        min-width: 48px !important;
        max-width: 48px !important;
        padding: 0 !important;
        border-radius: 0 8px 8px 0 !important;
        background: #C93645 !important;
        color: white !important;
        border: 1px solid #C93645 !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.22) !important;
        display: block !important;
        overflow: visible !important;
    }
    /* The native chevron remains visible, near the top of the rail. */
    [data-testid="stExpandSidebarButton"] svg {
        position: absolute !important;
        top: 12px !important;
        left: 12px !important;
        width: 24px !important;
        height: 24px !important;
        transform: rotate(180deg) !important;
    }
    /* Decorative icons are attached to the visible button, not its wrapper. */
    [data-testid="stExpandSidebarButton"]::before {
        content: "👤\\A🎲\\A🎲\\A🎯\\A✨" !important;
        position: absolute !important;
        top: 72px !important;
        left: 0 !important;
        width: 46px !important;
        white-space: pre !important;
        line-height: 2.8 !important;
        font-size: 1.05rem !important;
        text-align: center !important;
        pointer-events: none !important;
    }
    [data-testid="stExpandSidebarButton"]::after {
        content: "Dice/Ability Configuration" !important;
        position: absolute !important;
        left: 50% !important;
        top: 50% !important;
        transform: translate(-50%, -50%) rotate(180deg) !important;
        writing-mode: vertical-rl !important;
        color: white !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em !important;
        white-space: nowrap !important;
        pointer-events: none !important;
    }

    /* On narrow screens, avoid forcing a fixed-width sidebar or columns. */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            min-width: 0 !important;
            max-width: 100vw !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            width: 100% !important;
            min-width: 0 !important;
        }
        .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }
        button, [role="button"] {
            min-height: 44px !important;
        }
    }

    /* Keep ordinary sidebar action buttons at normal height. */
    [data-testid="stSidebar"] div[data-testid="stButton"]:not(.st-key-randomizer_card button) button {
        min-height: 42px;
        height: auto;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# 1. HELPERS
# --------------------------------------------------

def letter_for(number):
    config = globals().get('active_dice_config', DEFAULT_DICE_CONFIG)
    return config[number]


def objective_label(objective_id):
    registry = globals().get("active_objectives", OBJECTIVES)
    return registry[objective_id]["name"]


def percent(value):
    return f"{value * 100:.2f}%"


def reroll_action(dice, roll):
    """Describe rerolls by the face number, never by die position."""
    if not dice:
        return "Keep all five dice"

    counts = Counter(roll[die_number - 1] for die_number in dice)
    parts = []
    for face, count in sorted(counts.items()):
        if count == 1:
            parts.append(f"a {face}")
        elif count == 2:
            parts.append(f"both {face}s")
        else:
            parts.append(f"all {count} {face}s")

    if len(parts) == 1:
        return "Reroll " + parts[0]
    if len(parts) == 2:
        return "Reroll " + " and ".join(parts)
    return "Reroll " + ", ".join(parts[:-1]) + ", and " + parts[-1]


def branch_roll_for_action(branch, fallback_roll):
    """Get the roll associated with a decision-tree branch when available."""
    for key in ("roll", "first_roll_result", "resulting_roll", "dice"):
        candidate = branch.get(key)
        if isinstance(candidate, (list, tuple)) and len(candidate) == 5:
            return candidate
    return fallback_roll


def describe_current_progress(roll, objective):
    """Describe how the current dice match an objective's requirements."""
    objective_type = objective["type"]

    if objective_type == "straight":
        values = sorted(set(roll))
        longest_run = 0
        current_run = 0
        previous = None

        for value in values:
            if previous is not None and value == previous + 1:
                current_run += 1
            else:
                current_run = 1
            longest_run = max(longest_run, current_run)
            previous = value

        target = objective["dice_required"]
        return f"Longest consecutive run: {min(longest_run, target)}/{target}"

    letters = [DEFAULT_DICE_CONFIG[value] for value in roll]
    counts = Counter(letters)

    if objective_type == "letter":
        letter = objective["letter"]
        required = objective["minimum"]
        return f"{letter}: {counts[letter]}/{required}"

    requirements = objective["letters"]
    return " · ".join(
        f"{letter}: {counts[letter]}/{required}"
        for letter, required in requirements.items()
    )


def minimum_dice_to_reroll(roll, objective_id, dice_config):
    """Find the fewest dice positions that must be rerolled to make an objective possible."""
    registry = globals().get("active_objectives", OBJECTIVES)
    objective = registry[objective_id]

    if evaluate_objective(roll, objective, dice_config):
        return 0

    for number_to_reroll in range(1, len(roll) + 1):
        for dice_indices in combinations(range(len(roll)), number_to_reroll):
            for new_values in product(range(1, 7), repeat=number_to_reroll):
                possible_roll = list(roll)

                for index, new_value in zip(dice_indices, new_values):
                    possible_roll[index] = new_value

                if evaluate_objective(possible_roll, objective, dice_config):
                    return number_to_reroll

    return len(roll)


def calculate_fixed_keep_probabilities(roll, keep_dice, selected_objectives, dice_config):
    """
    Calculate exact objective probabilities if every die not marked Keep
    were hypothetically rerolled once. The displayed roll is never changed.
    """
    kept_indices = {die_number - 1 for die_number in keep_dice}
    rerolled_indices = [
        index for index in range(len(roll)) if index not in kept_indices
    ]

    possible_values = product(range(1, 7), repeat=len(rerolled_indices))
    total_outcomes = 6 ** len(rerolled_indices)
    successes = {objective_id: 0 for objective_id in selected_objectives}
    whiff_count = 0

    for new_values in possible_values:
        possible_roll = list(roll)
        for index, new_value in zip(rerolled_indices, new_values):
            possible_roll[index] = new_value

        achieved_any_objective = False
        for objective_id in selected_objectives:
            if evaluate_objective(
                possible_roll, globals().get("active_objectives", OBJECTIVES)[objective_id], dice_config
            ):
                successes[objective_id] += 1
                achieved_any_objective = True

        if not achieved_any_objective:
            whiff_count += 1

    return (
        {
            objective_id: successes[objective_id] / total_outcomes
            for objective_id in selected_objectives
        },
        whiff_count / total_outcomes,
        total_outcomes,
    )


def calculate_first_roll_analysis(
    roll, dice_config, run_two_reroll_analysis, selected_objectives
):
    """Analyze every selected objective; skip two-reroll odds when one-reroll chance is zero."""
    rows = []

    registry = globals().get("active_objectives", OBJECTIVES)
    for objective_id in selected_objectives:
        objective = registry[objective_id]
        one_reroll = calculate_best_one_reroll(
            roll,
            objective_id,
            dice_config,
        )

        rows.append({
            "objective_id": objective_id,
            "name": objective["name"],
            "progress": describe_current_progress(roll, objective),
            "dice_to_reroll": minimum_dice_to_reroll(
                roll,
                objective_id,
                dice_config,
            ),
            "one_reroll_probability": one_reroll["probability"],
            "one_reroll_action": one_reroll["dice_to_reroll"],
            "already_achieved": evaluate_objective(roll, objective, dice_config),
        })

    # Rank by one-reroll probability first, then by closeness.
    rows.sort(key=lambda row: (
        -row["one_reroll_probability"],
        row["dice_to_reroll"],
        row["name"],
    ))

    if run_two_reroll_analysis:
        for row in rows:
            # A second-reroll calculation adds no useful information when
            # the objective has zero probability after the first reroll.
            if row["one_reroll_probability"] <= 0:
                continue
            two_reroll = find_best_two_reroll_strategy(
                roll,
                [row["objective_id"]],
                dice_config,
            )
            row["two_reroll_probability"] = two_reroll["probability"]
            row["two_reroll_action"] = two_reroll["first_dice_to_reroll"]

    return rows


def show_dice_cards(current_roll, reroll_dice=None, show_actions=False, component_key="analysis_dice_cards"):
    """Display the roll using the same hero-specific engraved dice as the sidebar."""
    reroll_dice = reroll_dice or []
    visuals = hero_profile.get("dice_visuals", {})
    backgrounds = visuals.get("backgrounds", ["#E8E8E8"] * 6)
    colors = visuals.get("render_colors", {})
    dice = []
    for die_number, value in enumerate(current_roll, start=1):
        letter = letter_for(value)
        dice.append({
            "number": die_number,
            "value": value,
            "letter": letter,
            "background": backgrounds[value - 1] if len(backgrounds) >= value else "#E8E8E8",
            "ink": colors.get(letter, "#252525"),
            "action": ("REROLL" if die_number in reroll_dice else "KEEP") if show_actions else "",
            "highlight": bool(show_actions and die_number in reroll_dice),
        })
    dice_cards_component(
        dice=dice,
        kept=[False] * len(dice),
        interactive=False,
        key=component_key,
        default=[False] * len(dice),
    )


# --------------------------------------------------
# 2. SIDEBAR: GAME SETUP
# --------------------------------------------------

st.sidebar.markdown("### 🦸 Hero")

hero_names = list(HERO_PROFILES.keys())
selected_hero = st.sidebar.selectbox("Select character", hero_names, index=hero_names.index("Black Widow") if "Black Widow" in hero_names else 0)
hero_profile = HERO_PROFILES[selected_hero]
active_dice_config = dict(hero_profile["dice_config"])

# The source workbook has no six-face mapping for most heroes. Let users correct
# the provisional mapping directly rather than silently treating it as verified.
with st.sidebar.expander("🎲 Edit die-face mapping", expanded=hero_profile["mapping_status"].startswith("Provisional")):
    mapping_cols = st.columns(3)
    for face in range(1, 7):
        active_dice_config[face] = mapping_cols[(face - 1) % 3].selectbox(
            f"Die face {face}", ["A", "B", "C", "D"],
            index=["A", "B", "C", "D"].index(active_dice_config.get(face, "A")),
            key=f"hero_map_{selected_hero}_{face}"
        )

# Update the shared dictionaries used by the existing UI and probability engine.
DEFAULT_DICE_CONFIG.clear()
DEFAULT_DICE_CONFIG.update(active_dice_config)

# Start with generic straight objectives, then append the selected hero's board abilities.
active_objectives = {
    "small_straight": {"name": "Small Straight", "type": "straight", "dice_required": 4, "category": "General"},
    "large_straight": {"name": "Large Straight", "type": "straight", "dice_required": 5, "category": "General"},
}
hero_objective_meta = {}
special_condition_abilities = []
for ability in hero_profile["abilities"]:
    # Preserve every board ability in the database. Special-condition abilities
    # that need six dice or custom game-state logic are shown as reference-only
    # until a dedicated evaluator is implemented.
    if ability.get("objective") is None:
        special_condition_abilities.append(ability)
        continue
    obj = dict(ability["objective"])
    obj.update({"name": f"{ability['name']} ({ability['code']})", "category": "Character ability", "effect": ability["effect"], "symbols": ability["symbols"], "verification": ability["verification"]})
    active_objectives[ability["id"]] = obj
    hero_objective_meta[ability["id"]] = ability


# Build a symbol-name -> A/B/C/D mapping from explicit board ability notation.
# Card objectives are calculation-eligible only when every required symbol can
# be mapped unambiguously to a die-face letter.
def parse_symbol_parts(symbol_text):
    parts = []
    for raw_part in str(symbol_text or "").split("+"):
        raw_part = raw_part.strip()
        match = re.fullmatch(r"(.+?)(?:\s*×\s*(\d+))?", raw_part)
        if match:
            parts.append((match.group(1).strip(), int(match.group(2) or 1)))
    return parts


symbol_to_letter = {}
ambiguous_symbols = set()
for ability in hero_profile["abilities"]:
    code_letters = list(ability["code"])
    symbol_parts = parse_symbol_parts(ability.get("symbols", ""))
    expanded_symbols = []
    for symbol_name, count in symbol_parts:
        expanded_symbols.extend([symbol_name] * count)
    if len(expanded_symbols) == len(code_letters):
        for letter, symbol_name in zip(code_letters, expanded_symbols):
            if symbol_name in symbol_to_letter and symbol_to_letter[symbol_name] != letter:
                ambiguous_symbols.add(symbol_name)
            else:
                symbol_to_letter[symbol_name] = letter
for symbol_name in ambiguous_symbols:
    symbol_to_letter.pop(symbol_name, None)

card_objective_options = {}
card_unmapped_rows = []
for card_index, card in enumerate(CARD_OBJECTIVES.get(selected_hero, []), start=1):
    required = Counter()
    parts = parse_symbol_parts(card.get("symbols", ""))
    can_map = bool(parts)
    for symbol_name, count in parts:
        if symbol_name not in symbol_to_letter:
            can_map = False
            break
        required[symbol_to_letter[symbol_name]] += count
    if can_map:
        oid = f"card_{selected_hero.lower().replace(' ', '_')}_{card_index}"
        if len(required) == 1:
            letter, minimum = next(iter(required.items()))
            definition = {"type": "letter", "letter": letter, "minimum": minimum}
        else:
            definition = {"type": "combination", "letters": dict(required)}
        objective_code = "".join(letter * required[letter] for letter in "ABCD" if required.get(letter, 0))
        definition.update({
            "name": f"{card['name']} ({objective_code})",
            "category": "Additional ability / upgrade",
            "effect": card["effect"],
            "symbols": card["symbols"],
            "verification": card["research_status"],
        })
        active_objectives[oid] = definition
        card_objective_options[oid] = card
    else:
        card_unmapped_rows.append(card)

# The existing calculator operates on a shared objective registry. Reconfigure
# it per selected hero and clear its cached lookup whenever the set changes.
probability_engine_module.configure_objectives(active_objectives)

# Render the six physical die faces inside the actual left sidebar.
with st.sidebar:
    st.markdown("### 🎲 Character Die Faces")
    sidebar_visuals = hero_profile.get("dice_visuals", {})
    sidebar_backgrounds = sidebar_visuals.get("backgrounds", ["#E8E8E8"] * 6)
    sidebar_inks = sidebar_visuals.get("render_colors", {})
    sidebar_dice = [
        {
            "number": face,
            "value": face,
            "letter": active_dice_config.get(face, "A"),
            "background": sidebar_backgrounds[face - 1],
            "ink": sidebar_inks.get(active_dice_config.get(face, "A"), "#252525"),
            "action": "",
        }
        for face in range(1, 7)
    ]
    dice_cards_component(
        dice=sidebar_dice,
        kept=[False] * 6,
        interactive=False,
        columns=3,
        display_mode="key",
        key=f"sidebar_dice_key_{selected_hero}",
        default=[False] * 6,
    )

st.sidebar.markdown("### 🎲 Enter 5 Dice")

# Keep selections are stored separately from the dice values.
# Initialize them before the randomizer and dice controls are created.
default_roll = [4, 5, 6, 6, 1]
for index in range(5):
    keep_key = f"manual_keep_{index + 1}"
    if keep_key not in st.session_state:
        st.session_state[keep_key] = False

def randomize_unkept_dice():
    """Randomize only dice that are not currently marked Keep."""
    for die_index in range(5):
        if not st.session_state[f"manual_keep_{die_index + 1}"]:
            st.session_state[f"die_{die_index + 1}"] = random.randint(1, 6)


# Initialize dice values before the reroll control is rendered so its first
# click can never reference missing session-state keys.
for index in range(5):
    widget_key = f"die_{index + 1}"
    if widget_key not in st.session_state:
        st.session_state[widget_key] = default_roll[index]

dice_columns = st.sidebar.columns(5, gap="small")
roll = []

for index, column in enumerate(dice_columns):
    widget_key = f"die_{index + 1}"
    value = column.selectbox(
        f"Die {index + 1}",
        options=[1, 2, 3, 4, 5, 6],
        key=widget_key,
    )
    roll.append(value)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Character Objectives")

# Basic attacks are three independent, optional scaling tiers. DiceSlayer
# identifies the character's scaling attack; the tier requirements are 3/4/5
# matching symbols. Black Widow uses B (batons). Alchemist has no basic attack.
basic_abilities = [
    ability for ability in hero_profile["abilities"]
    if ability.get("is_basic_attack")
    and ability.get("objective", {}).get("type") == "letter"
    and selected_hero != "Alchemist"
]
selected_basic_ids = []
if basic_abilities:
    basic_ability = basic_abilities[0]
    basic_letter = basic_ability["objective"]["letter"]
    basic_symbol = basic_ability.get("symbols", "matching symbol")
    tier_specs = [
        ("basic", 3, "Basic Attack"),
        ("mid", 4, "Mid Basic Attack"),
        ("max", 5, "Max Basic Attack"),
    ]
    for tier_key, required_count, tier_label in tier_specs:
        objective_id = f"basic_{selected_hero.lower().replace(' ', '_')}_{tier_key}"
        active_objectives[objective_id] = {
            "name": f"{basic_ability['name']} ({tier_label})",
            "type": "letter",
            "letter": basic_letter,
            "minimum": required_count,
            "category": "Basic attack",
            "effect": (
                f"Activation requirement: {required_count} matching {basic_letter} symbols "
                f"({basic_symbol}). DiceSlayer identifies {basic_ability['name']} as this "
                "character's scaling basic attack. See the source ability description for "
                "its scaling effect."
            ),
            "symbols": f"{basic_letter} × {required_count}",
            "verification": basic_ability.get("verification", "DiceSlayer"),
        }
        if st.sidebar.checkbox(
            f"{basic_ability['name']} ({tier_label})",
            value=False,
            key=f"basic_attack_{selected_hero}_{tier_key}",
            help=active_objectives[objective_id]["effect"],
        ):
            selected_basic_ids.append(objective_id)

# Re-register the optional basic-attack tiers before analysis.
probability_engine_module.configure_objectives(active_objectives)

# Ability names remain selectable; their effect text appears only on hover.
board_abilities = [a for a in hero_profile["abilities"] if not a.get("is_basic_attack")]
selected_board_ids = []
for ability in board_abilities:
    oid = ability["id"]
    if ability.get("objective") is not None and oid in active_objectives:
        if st.sidebar.checkbox(
            f"{ability['name']} ({ability['code']})",
            value=True,
            key=f"board_ability_{selected_hero}_{oid}",
            help=ability.get("effect", "No effect description available.")
        ):
            selected_board_ids.append(oid)
    else:
        st.sidebar.checkbox(
            f"{ability['name']} ({ability['code']}) · not calculable",
            value=False,
            disabled=True,
            key=f"special_ability_{selected_hero}_{oid}",
            help=ability.get("effect", "Special-condition ability.")
        )

selected_card_ids = []
if card_objective_options:
    st.sidebar.markdown("### ✨ Additional Objectives")
    for oid, card in card_objective_options.items():
        if st.sidebar.checkbox(
            active_objectives[oid]["name"],
            value=False,
            key=f"card_ability_{selected_hero}_{oid}",
            help=card.get("effect", "No effect description available.")
        ):
            selected_card_ids.append(oid)

if card_unmapped_rows:
    with st.sidebar.expander(f"{len(card_unmapped_rows)} card candidates not yet calculable"):
        for idx, card in enumerate(card_unmapped_rows):
            st.sidebar.checkbox(
                f"{card['name']} · not calculable",
                value=False,
                disabled=True,
                key=f"unmapped_card_{selected_hero}_{idx}",
                help=card.get("effect", "Effect description unavailable.")
            )

# Add mathematical symbol combinations in a separate opt-in section. These are
# possibilities only, not claims that the hero has a printed ability for them.
from itertools import combinations_with_replacement
available_symbols = sorted(set(active_dice_config.values()))
possible_objectives = {}
for length in range(3, 6):
    for combo in combinations_with_replacement(available_symbols, length):
        counts = dict(Counter(combo))
        code = "".join(combo)
        oid = f"possible_{selected_hero.lower().replace(' ', '_')}_{code}"
        if oid in active_objectives:
            continue
        if len(counts) == 1:
            letter, minimum = next(iter(counts.items()))
            definition = {"type": "letter", "letter": letter, "minimum": minimum}
        else:
            definition = {"type": "combination", "letters": counts}
        definition.update({"name": f"Possible combination {code}", "category": "Mathematical possibility", "effect": "No character-board effect assigned; this is a probability-only combination."})
        possible_objectives[oid] = definition

show_possible = st.sidebar.checkbox("Show all mathematically possible symbol combinations", value=False)
if show_possible:
    active_objectives.update(possible_objectives)
    probability_engine_module.configure_objectives(active_objectives)
    selected_possible_ids = st.sidebar.multiselect(
        "Additional possible combinations", options=list(possible_objectives), default=[],
        format_func=lambda oid: possible_objectives[oid]["name"]
    )
else:
    selected_possible_ids = []

# Re-register after optional objective additions and build final selection.
probability_engine_module.configure_objectives(active_objectives)
selected_objectives = selected_basic_ids + selected_board_ids + selected_card_ids + selected_possible_ids

# --------------------------------------------------
# 3. CURRENT ROLL
# --------------------------------------------------

st.subheader("Your current roll")
st.caption(
    "Click a die itself to mark it Keep. Green dice are protected when you "
    "randomize; all other dice receive new values."
)

current_kept = [
    bool(st.session_state[f"manual_keep_{die_number}"])
    for die_number in range(1, 6)
]

active_visuals = hero_profile.get("dice_visuals", {})
active_backgrounds = active_visuals.get("backgrounds", ["#E8E8E8"] * 6)
active_render_colors = active_visuals.get("render_colors", {})
dice_data = [
    {
        "number": die_number,
        "value": roll[die_number - 1],
        "letter": letter_for(roll[die_number - 1]),
        "background": active_backgrounds[roll[die_number - 1] - 1],
        "ink": active_render_colors.get(letter_for(roll[die_number - 1]), "#252525"),
    }
    for die_number in range(1, 6)
]

updated_kept = dice_cards_component(
    dice=dice_data,
    kept=current_kept,
    interactive=True,
    columns=5,
    display_mode="roll",
    key="interactive_dice_cards",
    default=current_kept,
)

# The component returns the updated Keep selections after a click.
if updated_kept is not None and list(updated_kept) != current_kept:
    for die_number, is_kept in enumerate(updated_kept, start=1):
        st.session_state[f"manual_keep_{die_number}"] = bool(is_kept)
    st.rerun()

st.button(
    "🎲 Reroll unkept dice",
    key="main_reroll_unkept",
    type="primary",
    on_click=randomize_unkept_dice,
)

keep_dice = [
    die_number
    for die_number in range(1, 6)
    if st.session_state[f"manual_keep_{die_number}"]
]

# Check whether the current five-die roll already satisfies any selected objective.
current_hits = [
    active_objectives[objective_id]["name"]
    for objective_id in selected_objectives
    if evaluate_objective(
        roll,
        active_objectives[objective_id],
        DEFAULT_DICE_CONFIG,
    )
]

if current_hits:
    st.success("Already hit: " + ", ".join(current_hits))
elif selected_objectives:
    st.info("No objective hit yet — this roll currently misses all selected objectives.")
else:
    st.caption("Select objectives in the sidebar to check whether this roll hits any of them.")

dice_to_simulate = [number for number in range(1, 6) if number not in keep_dice]
if dice_to_simulate:
    simulation_action = (
        "If rerolled: dice " + ", ".join(map(str, dice_to_simulate))
    )
else:
    simulation_action = "All five dice kept — no dice rerolled"

st.caption(simulation_action)

if selected_objectives:
    manual_probabilities, manual_whiff_probability, manual_total = calculate_fixed_keep_probabilities(
        roll,
        keep_dice,
        selected_objectives,
        DEFAULT_DICE_CONFIG,
    )
    manual_rows = [
        {
            "Objective": active_objectives[objective_id]["name"],
            "Chance with this keep selection": percent(probability),
        }
        for objective_id, probability in sorted(
            manual_probabilities.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]
    st.dataframe(
        pd.DataFrame(manual_rows),
        width="stretch",
        hide_index=True,
    )
    st.metric(
        "Whiff chance · no selected objective",
        percent(manual_whiff_probability),
    )
    st.caption(
        f"Calculated exactly across {manual_total:,} possible outcome"
        f"{'' if manual_total == 1 else 's'}. Your current roll remains unchanged."
    )
else:
    st.info("Select at least one objective in the sidebar to see its probability.")



st.markdown("---")
st.subheader("Second Reroll Analysis")
include_second_reroll = st.checkbox(
    "Include second reroll analysis",
    value=True,
    help=(
        "When enabled, the calculator finds the best first reroll and then "
        "optimises the second reroll separately for every possible first-roll outcome."
    ),
)
if include_second_reroll:
    st.caption("Analysis: up to two rerolls, with an adaptive second action.")
else:
    st.caption("Analysis: one reroll only. The second-reroll calculation is skipped.")

analyze = st.button("Analyze strategy", type="primary", width="stretch")

# --------------------------------------------------
# 4. RUN THE REQUESTED ANALYSIS
# --------------------------------------------------

if analyze:
    if not selected_objectives:
        st.warning("Please select at least one objective.")
    else:
        try:
            if include_second_reroll:
                with st.spinner(
                    "Finding the best first reroll and adaptive second-reroll strategy..."
                ):
                    result = find_best_two_reroll_strategy(
                        roll,
                        selected_objectives,
                        DEFAULT_DICE_CONFIG,
                    )

                result["analysis_mode"] = "two_rerolls"

            else:
                with st.spinner("Finding the best one-reroll strategy..."):
                    one_reroll_result = calculate_best_one_reroll_for_objectives(
                        roll,
                        selected_objectives,
                        DEFAULT_DICE_CONFIG,
                    )

                result = {
                    "probability": one_reroll_result["probability"],
                    "first_dice_to_reroll": one_reroll_result["dice_to_reroll"],
                    "objective_probabilities": one_reroll_result[
                        "objective_probabilities"
                    ],
                    "successful_outcomes": one_reroll_result[
                        "successful_outcomes"
                    ],
                    "total_outcomes": one_reroll_result["total_outcomes"],
                    "analysis_mode": "one_reroll",
                }

            with st.spinner("Analyzing your initial roll against every objective..."):
                first_roll_analysis = calculate_first_roll_analysis(
                    roll,
                    DEFAULT_DICE_CONFIG,
                    include_second_reroll,
                    selected_objectives,
                )

            st.session_state["first_roll_analysis"] = first_roll_analysis
            st.session_state["strategy_result"] = result
            st.session_state["analyzed_roll"] = list(roll)
            st.session_state["analyzed_objectives"] = list(selected_objectives)
            st.session_state["analyzed_include_second"] = include_second_reroll
            st.session_state["analysis_error"] = None

        except Exception as exc:
            st.session_state["analysis_error"] = str(exc)


# --------------------------------------------------
# 5. DISPLAY RESULTS
# --------------------------------------------------

if st.session_state.get("analysis_error"):
    st.error(
        "The probability engine returned an error: "
        + st.session_state["analysis_error"]
    )

result = st.session_state.get("strategy_result")
analyzed_roll = st.session_state.get("analyzed_roll")
analyzed_objectives = st.session_state.get("analyzed_objectives")
analyzed_include_second = st.session_state.get("analyzed_include_second")

if result and analyzed_roll is not None:

    inputs_changed = (
        analyzed_roll != roll
        or analyzed_objectives != selected_objectives
        or analyzed_include_second != include_second_reroll
    )

    if inputs_changed:
        st.info(
            "Your inputs have changed. Select **Analyze strategy** to refresh the results."
        )

    else:
        # ------------------------------------------
        # FIRST-ROLL ANALYSIS
        # ------------------------------------------

        first_roll_analysis = st.session_state.get("first_roll_analysis", [])
        st.divider()
        st.header("First Roll Analysis")
        st.caption(
            "Every objective is assessed independently. Closeness means the "
            "minimum number of dice positions you would need to reroll to make "
            "the objective achievable; the one-reroll probability is optimized "
            "specifically for that objective."
        )

        first_roll_rows = []
        for row in first_roll_analysis:
            display_row = {
                "Objective": row["name"],
                "Current progress": row["progress"],
                "Minimum dice to reroll": row["dice_to_reroll"],
                "Best 1-reroll chance": percent(row["one_reroll_probability"]),
                "Best 1-reroll action": reroll_action(row["one_reroll_action"], analyzed_roll),
            }
            if "two_reroll_probability" in row:
                display_row["Best 2-reroll chance"] = percent(
                    row["two_reroll_probability"]
                )
            first_roll_rows.append(display_row)

        st.dataframe(
            pd.DataFrame(first_roll_rows),
            width="stretch",
            hide_index=True,
        )

        if include_second_reroll:
            st.caption(
                "The two-reroll chance is calculated for every objective with "
                "a non-zero chance after the first reroll. Objectives with a "
                "0% first-reroll chance are left blank."
            )
        else:
            st.caption(
                "Two-reroll calculations are skipped because "
                "'Include second reroll analysis' is turned off."
            )

        st.divider()

        is_two_reroll = result["analysis_mode"] == "two_rerolls"
        first_dice = result["first_dice_to_reroll"]

        st.divider()
        st.header("Recommended strategy")

        if is_two_reroll:
            st.caption(
                "Two-reroll analysis · The second-reroll recommendation adapts "
                "to the result of your first reroll."
            )
        else:
            st.caption("One-reroll analysis · The second-reroll calculation was skipped.")

        metric_left, metric_middle, metric_right = st.columns([1.2, 1, 1])

        metric_left.metric(
            "Chance of achieving at least one objective",
            percent(result["probability"]),
        )
        metric_middle.metric(
            "Recommended first action",
            reroll_action(first_dice, analyzed_roll),
        )
        metric_right.metric(
            "Whiff chance · no objective",
            percent(1 - result["probability"]),
        )

        st.markdown(f"**{reroll_action(first_dice, analyzed_roll)}**")
        show_dice_cards(analyzed_roll, first_dice, show_actions=True)

        # ------------------------------------------
        # OBJECTIVE OUTLOOK
        # ------------------------------------------

        st.divider()
        if is_two_reroll:
            st.header("Objective outlook · after two rerolls")
            st.caption(
                "Each percentage is the chance of achieving that individual "
                "objective when following the recommended two-reroll strategy. "
                "The second action adapts to the first-reroll result. These "
                "objectives are not independently optimised."
            )
        else:
            st.header("Objective outlook · after one reroll")
            st.caption(
                "Each percentage is the chance of achieving that individual "
                "objective when following the recommended first-reroll strategy. "
                "These objectives are not independently optimised."
            )

        objective_probabilities = result.get("objective_probabilities", {})
        ranked_objectives = sorted(
            objective_probabilities.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        if ranked_objectives:
            objective_columns = st.columns(min(4, len(ranked_objectives)))
            for index, (objective_id, probability) in enumerate(ranked_objectives):
                column = objective_columns[index % len(objective_columns)]
                column.metric(objective_label(objective_id), percent(probability))

            probability_sum = sum(objective_probabilities.values())
            if probability_sum > result["probability"] + 1e-8:
                st.caption(
                    "Some final rolls satisfy multiple objectives. Individual "
                    "objective probabilities therefore overlap and should not "
                    "be added together."
                )

        # ------------------------------------------
        # ONE-REROLL DETAILS
        # ------------------------------------------

        if not is_two_reroll:
            st.info(
                f"After rerolling, the probability of achieving at least one "
                f"selected objective is **{percent(result['probability'])}**."
            )

        # ------------------------------------------
        # TWO-REROLL DECISION TREE
        # ------------------------------------------

        if is_two_reroll:
            st.divider()
            st.header("Second-reroll strategy")
            st.caption(
                "This summarises the best second action for each possible result "
                "of your first reroll. **Chance of success** is the probability "
                "of completing at least one selected objective after taking that "
                "second action. **Share of first-reroll results** is how often "
                "that action-and-probability combination occurs among all "
                "possible first-reroll results; it is not a success probability."
            )

            branches = result.get("branches", [])

            if not branches:
                st.warning("No decision-tree branches were returned.")
            else:
                st.write(
                    f"There are **{len(branches)} possible first-reroll outcomes**. "
                    "The recommended second action changes depending on the "
                    "result of the first reroll."
                )

                grouped = {}
                for branch in branches:
                    second_dice = branch.get("dice_to_reroll", [])
                    second_action = reroll_action(second_dice, branch_roll_for_action(branch, analyzed_roll))
                    key = (second_action, round(branch["probability"], 10))
                    grouped.setdefault(key, []).append(branch)

                summary_rows = []
                for (second_action, final_probability), group in grouped.items():
                    summary_rows.append({
                        "Recommended second action": second_action,
                        "First-reroll results": len(group),
                        "Chance of success after second action": f"{final_probability * 100:.2f}%",
                        "Share of first-reroll results": (
                            f"{len(group) / len(branches) * 100:.2f}%"
                        ),
                    })

                summary_rows.sort(
                    key=lambda row: (
                        -row["First-reroll results"],
                        -float(
                            row["Chance of success after second action"].rstrip("%")
                        ),
                    )
                )

                st.dataframe(
                    pd.DataFrame(summary_rows),
                    width="stretch",
                    hide_index=True,
                )

                with st.expander("Compare the five best first-reroll strategies"):
                    comparison = sorted(
                        result.get("strategy_comparison", []),
                        key=lambda item: item["probability"],
                        reverse=True,
                    )[:5]

                    comparison_rows = [
                        {
                            "First action": reroll_action(
                                item["dice_to_reroll"], analyzed_roll
                            ),
                            "Final combined probability": percent(
                                item["probability"]
                            ),
                        }
                        for item in comparison
                    ]

                    st.dataframe(
                        pd.DataFrame(comparison_rows),
                        width="stretch",
                        hide_index=True,
                    )

        # ------------------------------------------
        # EXPLANATION
        # ------------------------------------------

        with st.expander("How to read these results"):
            if is_two_reroll:
                st.markdown(
                    """
                    - **Combined probability** is the chance of achieving at
                      least one selected objective after both reroll opportunities.
                    - **Whiff chance** is the probability of achieving none of
                      the selected objectives. It is 100% minus the combined probability.
                    - **Objective outlook** shows the chance of achieving each
                      objective under the same recommended two-reroll strategy.
                    - **First action** is the best opening reroll.
                    - **Second-reroll strategy** groups first-reroll results
                      that lead to the same recommended second action and success
                      probability. Its share column shows how common each group is.
                    - The objective list is currently selected manually.
                      Character profiles can be added later.
                    """
                )
            else:
                st.markdown(
                    """
                    - **Combined probability** is the chance of achieving at
                      least one selected objective after one reroll.
                    - **Whiff chance** is the probability of achieving none of
                      the selected objectives. It is 100% minus the combined probability.
                    - **Objective outlook** shows the chance of achieving each
                      objective under the same recommended one-reroll strategy.
                    - **First action** is the best reroll for the selected
                      objectives considered together.
                    - The second-reroll calculation is not performed.
                    """
                )

else:
    st.divider()
    st.info(
        "Choose your objectives and select **Analyze strategy** to see the "
        "recommended combined strategy. Your manual Keep selection above "
        "updates its hypothetical probabilities independently."
    )


st.caption(
    "Prototype · Current default dice configuration: 1–3 = A, 4–5 = B, 6 = C"
)


# --------------------------------------------------
# APP VERSION
# --------------------------------------------------
from datetime import datetime
from zoneinfo import ZoneInfo

_version_time = datetime.now(ZoneInfo("Europe/Berlin"))
_app_version = f"V1.XX.{_version_time:%m%d.%H%M}"
st.markdown(
    f"""
    <div style="text-align:center; color:#8A8A8A; font-size:0.75rem;
                padding:2rem 0 0.75rem 0; border-top:1px solid rgba(128,128,128,.2);
                margin-top:3rem;">
        Dice Throne Strategy Lab · {_app_version}
    </div>
    """,
    unsafe_allow_html=True,
)
