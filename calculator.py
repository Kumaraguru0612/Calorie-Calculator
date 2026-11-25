"""Core BMR, TDEE, macro calculation, input validation, and safety warnings."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

ACTIVITY_LEVELS: dict[str, dict[str, Any]] = {
    "sedentary": {
        "label": "Sedentary",
        "description": "Little or no structured exercise, mostly desk work",
        "multiplier": 1.2,
    },
    "light": {
        "label": "Lightly Active",
        "description": "Light exercise or sports 1–3 days per week",
        "multiplier": 1.375,
    },
    "moderate": {
        "label": "Moderately Active",
        "description": "Moderate exercise or sports 3–5 days per week",
        "multiplier": 1.55,
    },
    "very_active": {
        "label": "Very Active",
        "description": "Hard exercise or sports 6–7 days per week",
        "multiplier": 1.725,
    },
    "extra_active": {
        "label": "Extra Active",
        "description": "Very hard daily training or physically demanding job",
        "multiplier": 1.9,
    },
}

GOALS: dict[str, dict[str, Any]] = {
    "lose": {
        "label": "Lose Weight",
        "short_label": "Fat Loss",
        "sign": -1,
    },
    "maintain": {
        "label": "Maintain Weight",
        "short_label": "Maintenance",
        "sign": 0,
    },
    "gain": {
        "label": "Gain Weight",
        "short_label": "Weight Gain",
        "sign": 1,
    },
}

PACES: dict[str, dict[str, Any]] = {
    "mild": {
        "label": "Gentle",
        "kcal_delta": 250,
        "weekly_kg": 0.23,
        "weekly_lb": 0.5,
    },
    "standard": {
        "label": "Standard",
        "kcal_delta": 500,
        "weekly_kg": 0.45,
        "weekly_lb": 1.0,
    },
    "aggressive": {
        "label": "Intensive",
        "kcal_delta": 750,
        "weekly_kg": 0.68,
        "weekly_lb": 1.5,
    },
}

MACRO_PROFILES: dict[str, dict[str, Any]] = {
    "goal_optimal": {
        "label": "Goal-Optimized",
        "description": "Adapts protein and carbohydrate ratio to your selected goal.",
        "splits": {
            "lose": {"protein": 0.30, "carbs": 0.40, "fat": 0.30},
            "maintain": {"protein": 0.25, "carbs": 0.45, "fat": 0.30},
            "gain": {"protein": 0.25, "carbs": 0.50, "fat": 0.25},
        },
    },
    "balanced": {
        "label": "Balanced (30/40/30)",
        "description": "Steady 30% protein, 40% carbs, 30% fat split.",
        "splits": {
            "lose": {"protein": 0.30, "carbs": 0.40, "fat": 0.30},
            "maintain": {"protein": 0.30, "carbs": 0.40, "fat": 0.30},
            "gain": {"protein": 0.30, "carbs": 0.40, "fat": 0.30},
        },
    },
    "high_protein": {
        "label": "Higher Protein (35/35/30)",
        "description": "Prioritizes satiety and lean tissue support.",
        "splits": {
            "lose": {"protein": 0.35, "carbs": 0.35, "fat": 0.30},
            "maintain": {"protein": 0.35, "carbs": 0.35, "fat": 0.30},
            "gain": {"protein": 0.35, "carbs": 0.35, "fat": 0.30},
        },
    },
    "lower_carb": {
        "label": "Lower Carb (30/25/45)",
        "description": "Reduced carbohydrates with higher dietary fat.",
        "splits": {
            "lose": {"protein": 0.30, "carbs": 0.25, "fat": 0.45},
            "maintain": {"protein": 0.30, "carbs": 0.25, "fat": 0.45},
            "gain": {"protein": 0.30, "carbs": 0.25, "fat": 0.45},
        },
    },
}

MIN_AGE = 15
MAX_AGE = 100
MIN_WEIGHT_KG = 30.0
MAX_WEIGHT_KG = 300.0
MIN_WEIGHT_LB = 66.0
MAX_WEIGHT_LB = 660.0
MIN_HEIGHT_CM = 100.0
MAX_HEIGHT_CM = 250.0
MIN_SAFE_CALORIES = {"female": 1200, "male": 1500}

LB_TO_KG = 0.45359237
INCH_TO_CM = 2.54


@dataclass(frozen=True)
class ValidatedInput:
    """Normalized user input ready for calorie and macro calculations."""

    unit_system: str
    sex: str
    age: int
    weight_kg: float
    height_cm: float
    activity_level: str
    goal: str
    pace: str
    macro_profile: str


def _parse_finite_float(raw_value: Any, field_label: str) -> tuple[float | None, str | None]:
    if raw_value is None or isinstance(raw_value, bool):
        return None, f"{field_label} is required."
    text = str(raw_value).strip()
    if not text:
        return None, f"{field_label} is required."
    try:
        num = float(text)
    except ValueError:
        return None, f"{field_label} must be a valid number."
    if not math.isfinite(num):
        return None, f"{field_label} must be a finite number."
    return num, None


def _parse_strict_int(raw_value: Any, field_label: str) -> tuple[int | None, str | None]:
    if raw_value is None or isinstance(raw_value, bool):
        return None, f"{field_label} is required."
    text = str(raw_value).strip()
    if not text:
        return None, f"{field_label} is required."
    try:
        if "." in text:
            return None, f"{field_label} must be a whole number."
        num = int(text)
    except ValueError:
        return None, f"{field_label} must be a whole number."
    return num, None


def validate_inputs(raw_data: Mapping[str, Any]) -> tuple[ValidatedInput | None, dict[str, str]]:
    """Validate and normalize raw form or JSON inputs.

    Returns a tuple of (ValidatedInput or None, field_errors dict).
    """
    errors: dict[str, str] = {}

    unit_system = str(raw_data.get("unit_system", "metric")).strip().lower()
    if unit_system not in {"metric", "imperial"}:
        errors["unit_system"] = "Unit system must be metric or imperial."

    sex = str(raw_data.get("sex", "")).strip().lower()
    if sex not in {"male", "female"}:
        errors["sex"] = "Please select biological sex (male or female)."

    age, age_err = _parse_strict_int(raw_data.get("age"), "Age")
    if age_err:
        errors["age"] = age_err
    elif age is not None and not (MIN_AGE <= age <= MAX_AGE):
        errors["age"] = f"Age must be between {MIN_AGE} and {MAX_AGE} years."

    weight_kg: float | None = None
    height_cm: float | None = None

    if unit_system == "metric":
        weight_val, w_err = _parse_finite_float(raw_data.get("weight_kg"), "Weight (kg)")
        if w_err:
            errors["weight_kg"] = w_err
        elif weight_val is not None and not (MIN_WEIGHT_KG <= weight_val <= MAX_WEIGHT_KG):
            errors["weight_kg"] = (
                f"Weight must be between {int(MIN_WEIGHT_KG)} and {int(MAX_WEIGHT_KG)} kg."
            )
        else:
            weight_kg = weight_val

        height_val, h_err = _parse_finite_float(raw_data.get("height_cm"), "Height (cm)")
        if h_err:
            errors["height_cm"] = h_err
        elif height_val is not None and not (MIN_HEIGHT_CM <= height_val <= MAX_HEIGHT_CM):
            errors["height_cm"] = (
                f"Height must be between {int(MIN_HEIGHT_CM)} and {int(MAX_HEIGHT_CM)} cm."
            )
        else:
            height_cm = height_val
    elif unit_system == "imperial":
        weight_lb, w_err = _parse_finite_float(raw_data.get("weight_lb"), "Weight (lbs)")
        if w_err:
            errors["weight_lb"] = w_err
        elif weight_lb is not None and not (MIN_WEIGHT_LB <= weight_lb <= MAX_WEIGHT_LB):
            errors["weight_lb"] = (
                f"Weight must be between {int(MIN_WEIGHT_LB)} and {int(MAX_WEIGHT_LB)} lbs."
            )
        elif weight_lb is not None:
            weight_kg = weight_lb * LB_TO_KG

        feet, ft_err = _parse_strict_int(raw_data.get("height_ft"), "Height (feet)")
        inches_raw = raw_data.get("height_in", "0")
        if str(inches_raw).strip() == "":
            inches_raw = "0"
        inches, in_err = _parse_finite_float(inches_raw, "Height (inches)")

        if ft_err:
            errors["height_ft"] = ft_err
        elif feet is not None and not (3 <= feet <= 8):
            errors["height_ft"] = "Feet must be between 3 and 8."

        if in_err:
            errors["height_in"] = in_err
        elif inches is not None and not (0.0 <= inches < 12.0):
            errors["height_in"] = "Inches must be between 0 and 11.9."

        if "height_ft" not in errors and "height_in" not in errors and feet is not None and inches is not None:
            converted_cm = ((feet * 12) + inches) * INCH_TO_CM
            if not (MIN_HEIGHT_CM <= converted_cm <= MAX_HEIGHT_CM):
                errors["height_ft"] = "Combined height must correspond to 100–250 cm."
            else:
                height_cm = converted_cm

    activity_level = str(raw_data.get("activity_level", "")).strip().lower()
    if activity_level not in ACTIVITY_LEVELS:
        errors["activity_level"] = "Please select a valid activity level."

    goal = str(raw_data.get("goal", "")).strip().lower()
    if goal not in GOALS:
        errors["goal"] = "Please select a valid goal (lose, maintain, or gain)."

    pace_raw = str(raw_data.get("pace", "standard")).strip().lower() or "standard"
    if pace_raw not in PACES:
        errors["pace"] = "Please select a valid pace (mild, standard, or aggressive)."

    macro_raw = str(raw_data.get("macro_profile", "goal_optimal")).strip().lower() or "goal_optimal"
    if macro_raw not in MACRO_PROFILES:
        errors["macro_profile"] = "Please select a valid macro distribution style."

    if errors or age is None or weight_kg is None or height_cm is None:
        return None, errors

    return (
        ValidatedInput(
            unit_system=unit_system,
            sex=sex,
            age=age,
            weight_kg=weight_kg,
            height_cm=height_cm,
            activity_level=activity_level,
            goal=goal,
            pace=pace_raw,
            macro_profile=macro_raw,
        ),
        {},
    )


def calculate_mifflin_st_jeor_bmr(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """Compute Basal Metabolic Rate (kcal/day) using the Mifflin-St Jeor equation."""
    base = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age)
    if sex == "male":
        return base + 5.0
    if sex == "female":
        return base - 161.0
    raise ValueError(f"Unsupported sex: {sex}")


def calculate_macros(target_calories: int, goal: str, macro_profile: str) -> dict[str, dict[str, int]]:
    """Compute daily macro targets in grams, calories, and percentage shares."""
    effective_calories = max(target_calories, 0)
    split = MACRO_PROFILES[macro_profile]["splits"][goal]

    protein_pct = round(split["protein"] * 100)
    carbs_pct = round(split["carbs"] * 100)
    fat_pct = 100 - protein_pct - carbs_pct

    protein_kcal = round(effective_calories * split["protein"])
    carbs_kcal = round(effective_calories * split["carbs"])
    fat_kcal = max(effective_calories - protein_kcal - carbs_kcal, 0)

    return {
        "protein": {
            "grams": round(protein_kcal / 4.0),
            "calories": protein_kcal,
            "percent": protein_pct,
            "kcal_per_gram": 4,
        },
        "carbs": {
            "grams": round(carbs_kcal / 4.0),
            "calories": carbs_kcal,
            "percent": carbs_pct,
            "kcal_per_gram": 4,
        },
        "fat": {
            "grams": round(fat_kcal / 9.0),
            "calories": fat_kcal,
            "percent": fat_pct,
            "kcal_per_gram": 9,
        },
    }


def build_safety_warnings(
    *,
    sex: str,
    age: int,
    bmr: int,
    tdee: int,
    target_calories: int,
    raw_target_calories: float,
    goal: str,
    pace: str,
    daily_delta: int,
) -> list[dict[str, str]]:
    """Generate clinical and nutritional safety warnings based on inputs and outputs."""
    warnings: list[dict[str, str]] = []
    safe_floor = MIN_SAFE_CALORIES[sex]

    if raw_target_calories < safe_floor:
        sex_label = "men" if sex == "male" else "women"
        warnings.append(
            {
                "level": "danger",
                "title": "Below Minimum Recommended Calorie Intake",
                "message": (
                    f"Your calculated target ({target_calories:,} kcal/day) falls below the "
                    f"generally recommended minimum of {safe_floor:,} kcal/day for {sex_label}. "
                    "Very low-calorie diets increase the risk of nutrient deficiencies, fatigue, "
                    "gallstones, and lean muscle loss. Consider choosing a gentler pace or "
                    "maintaining your weight, and consult a physician before eating below this threshold."
                ),
            }
        )

    if goal == "lose" and raw_target_calories < bmr:
        warnings.append(
            {
                "level": "warning",
                "title": "Target Is Below Basal Metabolic Rate (BMR)",
                "message": (
                    f"Your target ({target_calories:,} kcal/day) is lower than your estimated BMR "
                    f"({bmr:,} kcal/day), which represents the energy your body needs at complete rest. "
                    "Sustained intake below BMR should only be undertaken with clinical supervision."
                ),
            }
        )

    if goal == "lose" and (pace == "aggressive" or (tdee > 0 and abs(daily_delta) / tdee > 0.25)):
        warnings.append(
            {
                "level": "warning",
                "title": "Aggressive Calorie Deficit",
                "message": (
                    "A daily deficit larger than 500 kcal or exceeding 25% of TDEE may be harder to "
                    "sustain and can accelerate loss of lean muscle tissue alongside body fat."
                ),
            }
        )

    if goal == "gain" and pace == "aggressive":
        warnings.append(
            {
                "level": "info",
                "title": "Large Calorie Surplus",
                "message": (
                    "A +750 kcal/day surplus may lead to faster body fat accumulation alongside muscle "
                    "gain. A +250 to +500 kcal/day surplus is commonly preferred for leaner weight gain."
                ),
            }
        )

    if age < 18:
        warnings.append(
            {
                "level": "warning",
                "title": "Adolescent Nutritional Guidance",
                "message": (
                    "Predictive calorie equations are primarily calibrated for adults. Because growth "
                    "and development require additional energy, individuals under 18 should consult a "
                    "pediatrician or registered dietitian before modifying calorie intake."
                ),
            }
        )

    return warnings


def calculate_plan(validated: ValidatedInput) -> dict[str, Any]:
    """Run the full calorie, TDEE, macro, and safety evaluation for validated input."""
    bmr_exact = calculate_mifflin_st_jeor_bmr(
        sex=validated.sex,
        weight_kg=validated.weight_kg,
        height_cm=validated.height_cm,
        age=validated.age,
    )
    activity_meta = ACTIVITY_LEVELS[validated.activity_level]
    tdee_exact = bmr_exact * activity_meta["multiplier"]

    goal_meta = GOALS[validated.goal]
    pace_meta = PACES[validated.pace]

    daily_delta = goal_meta["sign"] * pace_meta["kcal_delta"]
    raw_target = tdee_exact + daily_delta

    bmr = round(bmr_exact)
    tdee = round(tdee_exact)
    target_calories = max(round(raw_target), 0)

    macros = calculate_macros(target_calories, validated.goal, validated.macro_profile)
    warnings = build_safety_warnings(
        sex=validated.sex,
        age=validated.age,
        bmr=bmr,
        tdee=tdee,
        target_calories=target_calories,
        raw_target_calories=raw_target,
        goal=validated.goal,
        pace=validated.pace,
        daily_delta=daily_delta,
    )

    weekly_change_kg = round(goal_meta["sign"] * pace_meta["weekly_kg"], 2)
    weekly_change_lb = round(goal_meta["sign"] * pace_meta["weekly_lb"], 2)

    return {
        "bmr": bmr,
        "tdee": tdee,
        "target_calories": target_calories,
        "daily_delta": daily_delta,
        "safe_minimum": MIN_SAFE_CALORIES[validated.sex],
        "activity_label": activity_meta["label"],
        "activity_multiplier": activity_meta["multiplier"],
        "goal_key": validated.goal,
        "goal_label": goal_meta["label"],
        "goal_short_label": goal_meta["short_label"],
        "pace_key": validated.pace,
        "pace_label": pace_meta["label"] if validated.goal != "maintain" else "Maintenance",
        "macro_profile_label": MACRO_PROFILES[validated.macro_profile]["label"],
        "weekly_change_kg": weekly_change_kg,
        "weekly_change_lb": weekly_change_lb,
        "weight_kg_normalized": round(validated.weight_kg, 1),
        "height_cm_normalized": round(validated.height_cm, 1),
        "macros": macros,
        "warnings": warnings,
    }
