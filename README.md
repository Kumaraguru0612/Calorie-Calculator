# Calorie Calculator

A stateless Python 3 & Flask web application for estimating daily calorie needs (BMR & TDEE) and macronutrient targets using the **Mifflin-St Jeor** equation.

## Features

- **Mifflin-St Jeor BMR**: Computes Basal Metabolic Rate accurately for male and female inputs.
- **TDEE Activity Multipliers**: Supports 5 activity tiers from Sedentary (`×1.2`) to Extra Active (`×1.9`).
- **Flexible Goals & Paces**: Lose weight, maintain weight, or gain weight with Gentle (`250 kcal`), Standard (`500 kcal`), or Intensive (`750 kcal`) daily adjustments.
- **Macronutrient Breakdown**: Displays daily grams, calories, and percentage shares for Protein, Carbohydrates, and Fat across Goal-Optimized, Balanced, Higher Protein, and Lower Carb profiles.
- **Metric & Imperial Units**: Supports `kg / cm` and `lbs / ft + in` with strict server-side validation.
- **Safety Warnings & Medical Disclaimers**: Flags calorie targets below clinical minimums (`1,200 kcal` women / `1,500 kcal` men), targets below BMR, aggressive deficits/surpluses, and adolescent inputs.
- **Privacy First**: Completely stateless—no database, no session cookies, no analytics, and no personal data stored or logged.

## Project Structure

```text
calorie-calculator-python/
├── .gitignore
├── README.md
├── requirements.txt
├── app.py
├── calculator.py
├── static/
│   └── css/
│       └── styles.css
├── templates/
│   └── index.html
└── tests/
    └── test_calculator.py
```

## Local Setup & Run

1. Open a terminal in the project folder:
   ```powershell
   cd path\to\calorie-calculator-python
   ```
2. Create and activate a virtual environment (if not already created):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Start the Flask app:
   ```powershell
   python app.py
   ```
5. Open your browser at:
   `http://127.0.0.1:5000`

## Running Tests

```powershell
.\.venv\Scripts\pytest.exe -v
```

## Medical Disclaimer

Calculations are educational estimates based on the Mifflin-St Jeor equation and general population activity factors. They are not medical or nutritional advice. Consult a qualified healthcare professional or registered dietitian before making significant dietary changes.
