import pandas as pd
import numpy as np
import joblib

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

# ============================================================
# LOAD TEST DATA
# ============================================================

TEST_PATH = "C:/Users/Khush/Desktop/HACKATHON/test.csv"

df = pd.read_csv(TEST_PATH)

# ============================================================
# REMOVE UNUSED COLUMN
# ============================================================

if "Country" in df.columns:
    df.drop(columns=["Country"], inplace=True)

# ============================================================
# FEATURE ENGINEERING
# ============================================================

df["Sleep_Deficit"] = np.maximum(
    0,
    8 - df["Sleep_Hours_Per_Night"]
)

df["Usage_Age_Ratio"] = (
    df["Avg_Daily_Usage_Hours"]
    / df["Age"]
)

df["Recovery_Capacity"] = (
    df["Sleep_Hours_Per_Night"]
    * df["Mental_Health_Score"]
)

df["Psychosocial_Load"] = (
    df["Avg_Daily_Usage_Hours"]
    * df["Conflicts_Over_Social_Media"]
)

df["Lifestyle_Balance"] = (
    df["Sleep_Hours_Per_Night"]
    / (df["Avg_Daily_Usage_Hours"] + 1)
)

df["Wellness_Ratio"] = (
    df["Mental_Health_Score"]
    * df["Sleep_Hours_Per_Night"]
) / (
    df["Avg_Daily_Usage_Hours"] + 1
)

df["Stress_Density"] = (
    df["Conflicts_Over_Social_Media"]
    /
    (
        df["Mental_Health_Score"] + 1
    )
)

# ============================================================
# BINARY ENCODING
# ============================================================

df["Gender"] = df["Gender"].map({
    "Male": 0,
    "Female": 1
})

df["Affects_Academic_Performance"] = (
    df["Affects_Academic_Performance"].map({
        "No": 0,
        "Yes": 1
    })
)

# ============================================================
# ORDINAL ENCODING
# ============================================================

academic_map = {
    "High School": 0,
    "Undergraduate": 1,
    "Graduate": 2
}

df["Academic_Level"] = (
    df["Academic_Level"].map(
        academic_map
    )
)

# ============================================================
# SEPARATE FEATURES/TARGET
# ============================================================

y_test = df["Addicted_Score"]

X_test = df.drop(
    columns=["Addicted_Score"]
)

# ============================================================
# LOAD ENCODER
# ============================================================

encoder = joblib.load(
    "C:/Users/Khush/Desktop/HACKATHON/models/encoder.pkl"
)

categorical_columns = [
    "Governorate",
    "Most_Used_Platform",
    "Relationship_Status"
]

encoded = encoder.transform(
    X_test[categorical_columns]
)

encoded = pd.DataFrame(
    encoded,
    columns=encoder.get_feature_names_out(
        categorical_columns
    ),
    index=X_test.index
)

X_test = X_test.drop(
    columns=categorical_columns
)

X_test = pd.concat(
    [
        X_test,
        encoded
    ],
    axis=1
)

# ============================================================
# LOAD SCALER
# ============================================================

scaler = joblib.load(
    "C:/Users/Khush/Desktop/HACKATHON/models/scaler.pkl"
)

numeric_columns = X_test.select_dtypes(
    include="number"
).columns

X_test[numeric_columns] = scaler.transform(
    X_test[numeric_columns]
)

# ============================================================
# LOAD MODEL
# ============================================================

model = joblib.load(
    "C:/Users/Khush/Desktop/HACKATHON/models/best_model.pkl"
)

# ============================================================
# PREDICT
# ============================================================

predictions = model.predict(
    X_test
)

# ============================================================
# EVALUATION
# ============================================================

mae = mean_absolute_error(
    y_test,
    predictions
)

mse = mean_squared_error(
    y_test,
    predictions
)

rmse = np.sqrt(mse)

r2 = r2_score(
    y_test,
    predictions
)

print("=" * 70)
print("HACKATHON TEST RESULTS")
print("=" * 70)

print(f"MAE  : {mae:.4f}")
print(f"MSE  : {mse:.4f}")
print(f"RMSE : {rmse:.4f}")
print(f"R²   : {r2:.4f}")

# ============================================================
# SAVE RESULTS
# ============================================================

results = pd.DataFrame({
    "Actual": y_test,
    "Predicted": predictions,
    "Residual": y_test - predictions
})

OUTPUT = "C:/Users/Khush/Desktop/HACKATHON/results/hackathon_test_predictions.csv"

results.to_csv(
    OUTPUT,
    index=False
)

print("\nSaved predictions to:")
print(OUTPUT)

# ============================================================
# SUMMARY
# ============================================================

print("\nFirst 10 Predictions\n")

print(results.head(10))

print("\nAverage Residual:",
      round(results["Residual"].mean(),4))

print("Std Residual:",
      round(results["Residual"].std(),4))

print("="*70)