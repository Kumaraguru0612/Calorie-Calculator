"""Automated tests for Calorie Calculator math, validation, warnings, and Flask routes."""

from __future__ import annotations

import pytest

from app import app
from calculator import (
    ACTIVITY_LEVELS,
    calculate_mifflin_st_jeor_bmr,
    calculate_plan,
    validate_inputs,
)


class TestBMRAndTDEE:
    def test_mifflin_st_jeor_male(self) -> None:
        # (10 * 80) + (6.25 * 180) - (5 * 30) + 5 = 800 + 1125 - 150 + 5 = 1780
        bmr = calculate_mifflin_st_jeor_bmr("male", 80.0, 180.0, 30)
        assert bmr == pytest.approx(1780.0)

    def test_mifflin_st_jeor_female(self) -> None:
        # (10 * 60) + (6.25 * 165) - (5 * 28) - 161 = 600 + 1031.25 - 140 - 161 = 1330.25
        bmr = calculate_mifflin_st_jeor_bmr("female", 60.0, 165.0, 28)
        assert bmr == pytest.approx(1330.25)

    @pytest.mark.parametrize("activity_key,meta", ACTIVITY_LEVELS.items())
    def test_tdee_all_activity_levels(self, activity_key: str, meta: dict) -> None:
        validated, errors = validate_inputs(
            {
                "unit_system": "metric",
                "sex": "male",
                "age": "30",
                "weight_kg": "80",
                "height_cm": "180",
                "activity_level": activity_key,
                "goal": "maintain",
            }
        )
        assert errors == {}
        assert validated is not None
        plan = calculate_plan(validated)
        assert plan["bmr"] == 1780
        assert plan["tdee"] == round(1780 * meta["multiplier"])
        assert plan["target_calories"] == plan["tdee"]
        assert plan["daily_delta"] == 0

    def test_goals_lose_maintain_gain(self) -> None:
        base = {
            "unit_system": "metric",
            "sex": "male",
            "age": "30",
            "weight_kg": "80",
            "height_cm": "180",
            "activity_level": "moderate",  # 1780 * 1.55 = 2759
            "pace": "standard",  # 500 kcal
        }

        lose_in, _ = validate_inputs({**base, "goal": "lose"})
        maintain_in, _ = validate_inputs({**base, "goal": "maintain"})
        gain_in, _ = validate_inputs({**base, "goal": "gain"})

        lose_plan = calculate_plan(lose_in)
        maintain_plan = calculate_plan(maintain_in)
        gain_plan = calculate_plan(gain_in)

        assert maintain_plan["target_calories"] == 2759
        assert lose_plan["target_calories"] == 2259
        assert lose_plan["daily_delta"] == -500
        assert gain_plan["target_calories"] == 3259
        assert gain_plan["daily_delta"] == 500

    def test_imperial_conversion(self) -> None:
        # 154.32358 lbs ~ 70 kg; 5 ft 9 in = 69 in = 175.26 cm
        validated, errors = validate_inputs(
            {
                "unit_system": "imperial",
                "sex": "female",
                "age": "25",
                "weight_lb": "154.3",
                "height_ft": "5",
                "height_in": "9",
                "activity_level": "light",
                "goal": "maintain",
            }
        )
        assert errors == {}
        assert validated is not None
        assert validated.weight_kg == pytest.approx(70.0, abs=0.1)
        assert validated.height_cm == pytest.approx(175.26, abs=0.05)


class TestMacrosAndWarnings:
    def test_macro_breakdown_sums_to_target(self) -> None:
        validated, errors = validate_inputs(
            {
                "unit_system": "metric",
                "sex": "female",
                "age": "29",
                "weight_kg": "62",
                "height_cm": "168",
                "activity_level": "moderate",
                "goal": "lose",
                "pace": "standard",
                "macro_profile": "goal_optimal",
            }
        )
        assert errors == {}
        assert validated is not None
        plan = calculate_plan(validated)
        macros = plan["macros"]
        assert macros["protein"]["percent"] + macros["carbs"]["percent"] + macros["fat"]["percent"] == 100
        total_kcal = (
            macros["protein"]["calories"]
            + macros["carbs"]["calories"]
            + macros["fat"]["calories"]
        )
        assert total_kcal == plan["target_calories"]
        assert macros["protein"]["grams"] > 0
        assert macros["carbs"]["grams"] > 0
        assert macros["fat"]["grams"] > 0

    def test_safety_warning_below_minimum_calories_female(self) -> None:
        # Female 50 kg, 155 cm, age 45: BMR = 500 + 968.75 - 225 - 161 = 1082.75
        # Sedentary TDEE = 1299.3; lose aggressive (-750) = 549 -> triggers < 1200, < BMR, aggressive
        validated, errors = validate_inputs(
            {
                "unit_system": "metric",
                "sex": "female",
                "age": "45",
                "weight_kg": "50",
                "height_cm": "155",
                "activity_level": "sedentary",
                "goal": "lose",
                "pace": "aggressive",
            }
        )
        assert errors == {}
        assert validated is not None
        plan = calculate_plan(validated)
        titles = [w["title"] for w in plan["warnings"]]
        assert "Below Minimum Recommended Calorie Intake" in titles
        assert "Target Is Below Basal Metabolic Rate (BMR)" in titles
        assert "Aggressive Calorie Deficit" in titles

    def test_safety_warning_adolescent_and_surplus(self) -> None:
        validated, errors = validate_inputs(
            {
                "unit_system": "metric",
                "sex": "male",
                "age": "16",
                "weight_kg": "65",
                "height_cm": "175",
                "activity_level": "moderate",
                "goal": "gain",
                "pace": "aggressive",
            }
        )
        assert errors == {}
        assert validated is not None
        plan = calculate_plan(validated)
        titles = [w["title"] for w in plan["warnings"]]
        assert "Adolescent Nutritional Guidance" in titles
        assert "Large Calorie Surplus" in titles


class TestValidation:
    @pytest.mark.parametrize(
        "bad_payload,expected_field",
        [
            ({"unit_system": "stone"}, "unit_system"),
            ({"sex": "other", "age": "25", "weight_kg": "70", "height_cm": "175", "activity_level": "light", "goal": "maintain"}, "sex"),
            ({"sex": "male", "age": "12", "weight_kg": "70", "height_cm": "175", "activity_level": "light", "goal": "maintain"}, "age"),
            ({"sex": "male", "age": "25.5", "weight_kg": "70", "height_cm": "175", "activity_level": "light", "goal": "maintain"}, "age"),
            ({"sex": "male", "age": "25", "weight_kg": "nan", "height_cm": "175", "activity_level": "light", "goal": "maintain"}, "weight_kg"),
            ({"sex": "male", "age": "25", "weight_kg": "-10", "height_cm": "175", "activity_level": "light", "goal": "maintain"}, "weight_kg"),
            ({"sex": "male", "age": "25", "weight_kg": "70", "height_cm": "500", "activity_level": "light", "goal": "maintain"}, "height_cm"),
            ({"sex": "male", "age": "25", "weight_kg": "70", "height_cm": "175", "activity_level": "super_athlete", "goal": "maintain"}, "activity_level"),
            ({"sex": "male", "age": "25", "weight_kg": "70", "height_cm": "175", "activity_level": "light", "goal": "bulk"}, "goal"),
            ({"unit_system": "imperial", "sex": "female", "age": "30", "weight_lb": "140", "height_ft": "5", "height_in": "14", "activity_level": "light", "goal": "maintain"}, "height_in"),
        ],
    )
    def test_invalid_inputs_rejected(self, bad_payload: dict, expected_field: str) -> None:
        validated, errors = validate_inputs(bad_payload)
        assert validated is None
        assert expected_field in errors


class TestFlaskApp:
    def test_index_get(self) -> None:
        client = app.test_client()
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Calorie &amp; Macro Calculator" in html
        assert "Medical Disclaimer" in html
        assert "Zero Personal Data Stored" in html
        assert "no-store" in resp.headers.get("Cache-Control", "")
        assert "Set-Cookie" not in resp.headers

    def test_index_post_valid(self) -> None:
        client = app.test_client()
        resp = client.post(
            "/",
            data={
                "unit_system": "metric",
                "sex": "male",
                "age": "30",
                "weight_kg": "80",
                "height_cm": "180",
                "activity_level": "moderate",
                "goal": "maintain",
                "pace": "standard",
                "macro_profile": "goal_optimal",
            },
        )
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "1,780" in html
        assert "2,759" in html
        assert "Set-Cookie" not in resp.headers

    def test_index_post_invalid_returns_400(self) -> None:
        client = app.test_client()
        resp = client.post(
            "/",
            data={
                "unit_system": "metric",
                "sex": "male",
                "age": "5",
                "weight_kg": "-1",
                "height_cm": "180",
                "activity_level": "moderate",
                "goal": "maintain",
            },
        )
        assert resp.status_code == 400
        html = resp.get_data(as_text=True)
        assert "Age must be between 15 and 100 years." in html

    def test_api_calculate_valid_and_invalid(self) -> None:
        client = app.test_client()
        ok_resp = client.post(
            "/api/calculate",
            json={
                "unit_system": "metric",
                "sex": "female",
                "age": 28,
                "weight_kg": 60,
                "height_cm": 165,
                "activity_level": "light",
                "goal": "lose",
                "pace": "mild",
            },
        )
        assert ok_resp.status_code == 200
        payload = ok_resp.get_json()
        assert payload["ok"] is True
        assert payload["result"]["bmr"] == 1330
        assert payload["result"]["tdee"] == 1829
        assert payload["result"]["target_calories"] == 1579

        bad_resp = client.post("/api/calculate", json={"age": "abc"})
        assert bad_resp.status_code == 400
        bad_payload = bad_resp.get_json()
        assert bad_payload["ok"] is False
        assert "age" in bad_payload["errors"]

    def test_health_endpoint(self) -> None:
        client = app.test_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}
