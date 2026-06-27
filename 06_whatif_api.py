import os
import joblib
import numpy as np
import pandas as pd
import shap
from flask import Flask, request, jsonify
from flask_cors import CORS

# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)
CORS(app)  # Allow dashboard (any origin) to call this API

# ============================================================
# PATHS
# ============================================================

BASE_PATH = "."
BEST_MODEL_PATH = os.path.join(BASE_PATH, "models", "best_model.pkl")
ENCODER_PATH = os.path.join(BASE_PATH, "models", "encoder.pkl")
SCALER_PATH = os.path.join(BASE_PATH, "models", "scaler.pkl")
X_TRAIN_PATH = os.path.join(BASE_PATH, "X_train.csv")

# ============================================================
# LOAD MODEL + PREPROCESSORS (once at startup)
# ============================================================

print("Loading model and preprocessors...")
model = joblib.load(BEST_MODEL_PATH)
encoder = joblib.load(ENCODER_PATH)
scaler = joblib.load(SCALER_PATH)

X_train = pd.read_csv(X_TRAIN_PATH)
train_columns = X_train.columns.tolist()

# SHAP explainer (created once)
explainer = shap.TreeExplainer(model)

print(f"Model: {model.__class__.__name__}")
print(f"Features: {len(train_columns)}")
print("Ready!\n")

# ============================================================
# HELPER: FEATURE ENGINEERING
# ============================================================

def engineer_features(row):
    """
    Apply the exact same feature engineering as 01_EDA.py
    Input: dict with raw student values
    Output: dict with raw + engineered features
    """
    row = row.copy()

    row["Sleep_Deficit"] = max(0, 8 - row["Sleep_Hours_Per_Night"])

    row["Usage_Age_Ratio"] = (
        row["Avg_Daily_Usage_Hours"] / row["Age"]
    )

    row["Recovery_Capacity"] = (
        row["Sleep_Hours_Per_Night"] * row["Mental_Health_Score"]
    )

    row["Psychosocial_Load"] = (
        row["Avg_Daily_Usage_Hours"] * row["Conflicts_Over_Social_Media"]
    )

    row["Lifestyle_Balance"] = (
        row["Sleep_Hours_Per_Night"] / (row["Avg_Daily_Usage_Hours"] + 1)
    )

    row["Wellness_Ratio"] = (
        (row["Mental_Health_Score"] * row["Sleep_Hours_Per_Night"])
        / (row["Avg_Daily_Usage_Hours"] + 1)
    )

    row["Stress_Density"] = (
        row["Conflicts_Over_Social_Media"]
        / (row["Mental_Health_Score"] + 1)
    )

    return row


# ============================================================
# HELPER: PREPROCESS A SINGLE ROW
# ============================================================

def preprocess_row(raw_input):
    """
    Takes a dict of raw student values, applies feature engineering,
    encoding, and scaling. Returns a DataFrame ready for model.predict().
    """
    # Step 1: Feature engineering
    row = engineer_features(raw_input)

    # Step 2: Create DataFrame
    df = pd.DataFrame([row])

    # Step 3: Binary encoding
    df["Gender"] = df["Gender"].map({"Male": 0, "Female": 1})
    df["Affects_Academic_Performance"] = df["Affects_Academic_Performance"].map(
        {"No": 0, "Yes": 1}
    )

    # Step 4: Ordinal encoding
    df["Academic_Level"] = df["Academic_Level"].map({
        "High School": 0,
        "Undergraduate": 1,
        "Graduate": 2
    })

    # Step 5: One-hot encoding (using saved encoder)
    categorical_columns = [
        "Governorate",
        "Most_Used_Platform",
        "Relationship_Status"
    ]

    encoded = encoder.transform(df[categorical_columns])
    encoded_names = encoder.get_feature_names_out(categorical_columns)
    encoded_df = pd.DataFrame(encoded, columns=encoded_names)

    df = df.drop(columns=categorical_columns).reset_index(drop=True)
    df = pd.concat([df, encoded_df], axis=1)

    # Step 6: Align columns with training data
    for col in train_columns:
        if col not in df.columns:
            df[col] = 0

    df = df[train_columns]

    # Step 7: Scale
    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    df[numeric_columns] = scaler.transform(df[numeric_columns])

    return df


# ============================================================
# HELPER: RISK LABEL + RECOMMENDATIONS
# ============================================================

def get_risk_label(score):
    if score < 4.5:
        return "LOW"
    elif score < 6.5:
        return "MODERATE"
    else:
        return "HIGH"


def get_recommendations(score, raw_input, top_shap_features):
    """
    Generate personalised recommendations based on the prediction
    and the top SHAP features driving the risk.
    """
    recs = []

    if raw_input.get("Avg_Daily_Usage_Hours", 0) > 5:
        recs.append({
            "area": "Screen Time",
            "message": f"Your daily usage ({raw_input['Avg_Daily_Usage_Hours']}h) is high. Try reducing to under 4 hours gradually.",
            "priority": "high"
        })

    if raw_input.get("Sleep_Hours_Per_Night", 8) < 7:
        recs.append({
            "area": "Sleep",
            "message": f"You're sleeping {raw_input['Sleep_Hours_Per_Night']}h/night. Aim for 7-9 hours for better recovery.",
            "priority": "high"
        })

    if raw_input.get("Mental_Health_Score", 10) < 6:
        recs.append({
            "area": "Mental Health",
            "message": "Your mental health score is below average. Consider mindfulness, exercise, or counselling support.",
            "priority": "high"
        })

    if raw_input.get("Conflicts_Over_Social_Media", 0) >= 3:
        recs.append({
            "area": "Social Media Conflicts",
            "message": "Frequent conflicts online can amplify stress. Try muting notifications or limiting comment sections.",
            "priority": "medium"
        })

    if raw_input.get("Avg_Daily_Usage_Hours", 0) > 3 and raw_input.get("Sleep_Hours_Per_Night", 8) < 7:
        recs.append({
            "area": "Digital Curfew",
            "message": "Set a 'no screens' rule 1 hour before bed to improve both sleep and reduce usage.",
            "priority": "high"
        })

    # Check which engineered features are driving risk
    for feat_info in top_shap_features[:3]:
        if feat_info["direction"] == "Increases Risk":
            if feat_info["feature"] == "Stress_Density":
                recs.append({
                    "area": "Stress Management",
                    "message": "Your stress density is high (conflicts relative to mental health). Reducing online conflicts will help.",
                    "priority": "high"
                })
            elif feat_info["feature"] == "Psychosocial_Load":
                recs.append({
                    "area": "Psychosocial Load",
                    "message": "High usage combined with frequent conflicts is your biggest risk factor. Address both together.",
                    "priority": "high"
                })

    if score < 4.5:
        recs.append({
            "area": "Keep It Up",
            "message": "Your digital habits look healthy! Maintain your current balance.",
            "priority": "low"
        })

    # Remove duplicates by area
    seen = set()
    unique_recs = []
    for r in recs:
        if r["area"] not in seen:
            seen.add(r["area"])
            unique_recs.append(r)

    return unique_recs


# ============================================================
# HELPER: GET SHAP EXPLANATION FOR A SINGLE ROW
# ============================================================

def explain_prediction(processed_row):
    """
    Returns the top 5 SHAP features for a single processed row.
    """
    shap_values = explainer.shap_values(processed_row)

    if isinstance(shap_values, list):
        shap_values = shap_values[0]

    shap_array = np.array(shap_values).flatten()

    top_indices = np.argsort(-np.abs(shap_array))[:5]

    results = []
    for rank, idx in enumerate(top_indices, start=1):
        feat_name = train_columns[idx]
        shap_val = float(shap_array[idx])
        results.append({
            "rank": rank,
            "feature": feat_name,
            "shap_value": round(shap_val, 4),
            "direction": "Increases Risk" if shap_val > 0 else "Decreases Risk"
        })

    return results

def get_nl_explanation(top_features):
    """
    Translates SHAP features into a natural language sentence.
    """
    risk_drivers = [f["feature"].replace("_", " ").lower() for f in top_features[:3] if f["direction"] == "Increases Risk"]
    
    if not risk_drivers:
        return "Your habits currently show a healthy balance with no major risk drivers."
    
    if len(risk_drivers) == 1:
        return f"Your addiction score is mainly influenced by your {risk_drivers[0]}."
    else:
        return f"Your addiction score is mainly influenced by your {', '.join(risk_drivers[:-1])} and {risk_drivers[-1]}."


# ============================================================
# HELPER: COUNTERFACTUAL AI (Minimum Viable Change)
# ============================================================

def get_counterfactual(raw_input, current_score):
    """
    Calculates the minimum lifestyle change needed to reach a moderate/low score.
    """
    if current_score < 5.5:
        return {"status": "healthy", "message": "You are already in a healthy range!"}
        
    best_change = None
    min_effort = float('inf')
    
    current_sleep = raw_input.get("Sleep_Hours_Per_Night", 8)
    current_usage = raw_input.get("Avg_Daily_Usage_Hours", 4)
    
    # Grid search: try increasing sleep (up to +4h) and decreasing usage (down to 1h)
    for sleep_add in np.arange(0, 4.5, 0.5):
        for usage_sub in np.arange(0, current_usage, 0.5):
            if sleep_add == 0 and usage_sub == 0:
                continue
                
            test_input = raw_input.copy()
            test_input["Sleep_Hours_Per_Night"] = min(9.0, current_sleep + sleep_add) # Cap at 9h
            test_input["Avg_Daily_Usage_Hours"] = max(1.0, current_usage - usage_sub) # Floor at 1h
            
            test_processed = preprocess_row(test_input)
            test_score = float(model.predict(test_processed)[0])
            
            if test_score < 6.0: # Target: get out of HIGH risk
                effort = sleep_add + usage_sub 
                if effort < min_effort:
                    min_effort = effort
                    best_change = {
                        "target_score": round(test_score, 2),
                        "sleep_change": sleep_add,
                        "usage_change": -usage_sub,
                        "new_sleep": test_input["Sleep_Hours_Per_Night"],
                        "new_usage": test_input["Avg_Daily_Usage_Hours"]
                    }
                    
    if best_change:
        changes = []
        if best_change['sleep_change'] > 0:
            changes.append(f"increase sleep by {best_change['sleep_change']} hours")
        if best_change['usage_change'] < 0:
            changes.append(f"reduce screen time by {abs(best_change['usage_change'])} hours")
            
        msg = f"Minimum change to reach healthy score ({best_change['target_score']}): " + " and ".join(changes) + "."
        best_change["message"] = msg
        return best_change
    else:
        return {"status": "difficult", "message": "Significant changes across multiple habits (including mental health/conflicts) are needed."}

# ============================================================
# HELPER: BEHAVIOURAL RISK INDEX
# ============================================================
def get_risk_index(raw_input):
    sleep = raw_input.get("Sleep_Hours_Per_Night", 8)
    usage = raw_input.get("Avg_Daily_Usage_Hours", 4)
    mental = raw_input.get("Mental_Health_Score", 10)
    
    burnout_score = (usage / (sleep + 0.1)) + ((10 - mental) / 2)
    burnout_risk = "HIGH" if burnout_score > 4 else "MODERATE" if burnout_score > 2 else "LOW"
    
    sleep_risk = "HIGH" if sleep < 6 else "MODERATE" if sleep < 7.5 else "LOW"
    mental_risk = "HIGH" if mental < 5 else "MODERATE" if mental < 7 else "LOW"
    
    return {
        "Burnout_Risk": burnout_risk,
        "Sleep_Risk": sleep_risk,
        "Mental_Health_Risk": mental_risk
    }


# ============================================================
# API ENDPOINT: /predict
# ============================================================

@app.route("/predict", methods=["POST"])
def predict():
    """
    Accepts raw student data, returns:
      - predicted addiction score
      - risk level
      - behavioural risk index
      - top 5 SHAP features
      - natural language explanation
      - personalised recommendations
      - counterfactual (minimum change needed)
    """
    try:
        data = request.get_json()

        # Required fields
        required = [
            "Age", "Gender", "Academic_Level", "Governorate",
            "Avg_Daily_Usage_Hours", "Most_Used_Platform",
            "Affects_Academic_Performance", "Sleep_Hours_Per_Night",
            "Mental_Health_Score", "Relationship_Status",
            "Conflicts_Over_Social_Media"
        ]

        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        # Preprocess
        processed = preprocess_row(data)

        # Predict
        score = float(model.predict(processed)[0])
        risk = get_risk_label(score)
        
        # Risk Index
        risk_index = get_risk_index(data)

        # Explain
        top_features = explain_prediction(processed)
        nl_explanation = get_nl_explanation(top_features)

        # Recommendations
        recs = get_recommendations(score, data, top_features)
        
        # Counterfactual AI
        counterfactual = get_counterfactual(data, score)

        return jsonify({
            "predicted_score": round(score, 2),
            "risk_level": risk,
            "behavioural_risk_index": risk_index,
            "natural_language_explanation": nl_explanation,
            "top_features": top_features,
            "recommendations": recs,
            "counterfactual_goal": counterfactual,
            "engineered_scores": {
                "Recovery_Capacity": round(data["Sleep_Hours_Per_Night"] * data["Mental_Health_Score"], 2),
                "Psychosocial_Load": round(data["Avg_Daily_Usage_Hours"] * data["Conflicts_Over_Social_Media"], 2),
                "Lifestyle_Balance": round(data["Sleep_Hours_Per_Night"] / (data["Avg_Daily_Usage_Hours"] + 1), 2),
                "Stress_Density": round(data["Conflicts_Over_Social_Media"] / (data["Mental_Health_Score"] + 1), 2),
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# API ENDPOINT: /whatif
# ============================================================

@app.route("/whatif", methods=["POST"])
def whatif():
    """
    Accepts 'current' and 'adjusted' student data.
    Returns both predictions side-by-side so the user can see
    the impact of changing habits.
    """
    try:
        data = request.get_json()

        if "current" not in data or "adjusted" not in data:
            return jsonify({
                "error": "Request must include 'current' and 'adjusted' objects"
            }), 400

        current = data["current"]
        adjusted = data["adjusted"]

        # Process current
        current_processed = preprocess_row(current)
        current_score = float(model.predict(current_processed)[0])
        current_risk = get_risk_label(current_score)
        current_shap = explain_prediction(current_processed)

        # Process adjusted
        adjusted_processed = preprocess_row(adjusted)
        adjusted_score = float(model.predict(adjusted_processed)[0])
        adjusted_risk = get_risk_label(adjusted_score)
        adjusted_shap = explain_prediction(adjusted_processed)

        # Calculate change
        score_change = adjusted_score - current_score
        improved = score_change < 0

        # What changed
        changes = []
        for key in current:
            if current[key] != adjusted[key]:
                changes.append({
                    "field": key,
                    "from": current[key],
                    "to": adjusted[key]
                })

        return jsonify({
            "current": {
                "predicted_score": round(current_score, 2),
                "risk_level": current_risk,
                "top_features": current_shap
            },
            "adjusted": {
                "predicted_score": round(adjusted_score, 2),
                "risk_level": adjusted_risk,
                "top_features": adjusted_shap
            },
            "comparison": {
                "score_change": round(score_change, 2),
                "improved": improved,
                "changes_made": changes,
                "message": (
                    f"Score changed by {score_change:+.2f}. "
                    + ("Great improvement!" if improved else "This adjustment increased the risk.")
                )
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# API ENDPOINT: /options (for dropdown menus)
# ============================================================

@app.route("/options", methods=["GET"])
def options():
    """
    Returns valid values for categorical fields.
    Useful for building dropdown menus in the dashboard.
    """
    return jsonify({
        "Gender": ["Male", "Female"],
        "Academic_Level": ["High School", "Undergraduate", "Graduate"],
        "Governorate": [
            "Assiut", "Aswan", "Beheira", "Cairo", "Dakahlia", "Fayoum",
            "Gharbia", "Giza", "Ismailia", "Luxor", "Minya", "Monufia",
            "Port Said", "Qalyubia", "Qena", "Red Sea", "Sharqia",
            "Sohag", "Suez", "Alexandria"
        ],
        "Most_Used_Platform": [
            "Facebook", "Instagram", "KakaoTalk", "LINE", "LinkedIn",
            "Snapchat", "TikTok", "Twitter", "VKontakte", "WeChat",
            "WhatsApp", "YouTube"
        ],
        "Relationship_Status": ["Single", "In Relationship", "Complicated"],
        "Affects_Academic_Performance": ["Yes", "No"],
        "numeric_ranges": {
            "Age": {"min": 15, "max": 30, "step": 1},
            "Avg_Daily_Usage_Hours": {"min": 0, "max": 12, "step": 0.5},
            "Sleep_Hours_Per_Night": {"min": 3, "max": 12, "step": 0.5},
            "Mental_Health_Score": {"min": 1, "max": 10, "step": 1},
            "Conflicts_Over_Social_Media": {"min": 0, "max": 5, "step": 1}
        }
    })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MINDBALANCE AI PLATFORM API")
    print("=" * 70)
    print()
    print("Endpoints:")
    print("  POST /predict  - Predict score, SHAP, Counterfactual AI, Risk Index")
    print("  POST /whatif   - Compare current vs adjusted habits")
    print("  GET  /options  - Get valid dropdown values")
    print()
    print("Starting server on http://localhost:5000")
    print("=" * 70)

    app.run(host="0.0.0.0", port=5000, debug=False)
