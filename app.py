"""Flask web application for the stateless Calorie Calculator."""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from calculator import (
    ACTIVITY_LEVELS,
    GOALS,
    MACRO_PROFILES,
    PACES,
    calculate_plan,
    validate_inputs,
)

DEFAULT_FORM_DATA: dict[str, str] = {
    "unit_system": "metric",
    "sex": "female",
    "age": "",
    "weight_kg": "",
    "height_cm": "",
    "weight_lb": "",
    "height_ft": "",
    "height_in": "",
    "activity_level": "moderate",
    "goal": "maintain",
    "pace": "standard",
    "macro_profile": "goal_optimal",
}


def create_app() -> Flask:
    """Create and configure the Calorie Calculator Flask application."""
    app = Flask(__name__)

    @app.after_request
    def apply_privacy_headers(response: Response) -> Response:
        """Prevent caching of user-submitted health metrics and harden responses."""
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.route("/", methods=["GET", "POST"])
    def index() -> tuple[str, int] | str:
        form_data = dict(DEFAULT_FORM_DATA)
        errors: dict[str, str] = {}
        result: dict[str, Any] | None = None
        status_code = 200

        if request.method == "POST":
            for key in DEFAULT_FORM_DATA:
                if key in request.form:
                    form_data[key] = request.form.get(key, "").strip()

            validated, errors = validate_inputs(form_data)
            if validated is not None:
                result = calculate_plan(validated)
            else:
                status_code = 400

        return (
            render_template(
                "index.html",
                form_data=form_data,
                errors=errors,
                result=result,
                activity_levels=ACTIVITY_LEVELS,
                goals=GOALS,
                paces=PACES,
                macro_profiles=MACRO_PROFILES,
            ),
            status_code,
        )

    @app.route("/api/calculate", methods=["POST"])
    def api_calculate() -> tuple[Response, int]:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return (
                jsonify(
                    {
                        "ok": False,
                        "errors": {"request": "Request body must be a valid JSON object."},
                    }
                ),
                400,
            )

        validated, errors = validate_inputs(payload)
        if validated is None:
            return jsonify({"ok": False, "errors": errors}), 400

        return jsonify({"ok": True, "result": calculate_plan(validated)}), 200

    @app.route("/health", methods=["GET"])
    def health() -> tuple[Response, int]:
        return jsonify({"status": "ok"}), 200

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
