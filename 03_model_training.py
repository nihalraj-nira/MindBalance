import os
import time
import warnings
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.ensemble import (
    RandomForestRegressor,
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    AdaBoostRegressor,
    HistGradientBoostingRegressor,
)
from sklearn.inspection import permutation_importance

warnings.filterwarnings("ignore")

# ============================================================
# PATHS
# ============================================================

BASE_PATH = "."
X_TRAIN_PATH = os.path.join(BASE_PATH, "X_train.csv")
X_TEST_PATH = os.path.join(BASE_PATH, "X_test.csv")
Y_TRAIN_PATH = os.path.join(BASE_PATH, "y_train.csv")
Y_TEST_PATH = os.path.join(BASE_PATH, "y_test.csv")

RESULTS_DIR = os.path.join(BASE_PATH, "results")
MODELS_DIR = os.path.join(BASE_PATH, "models")
FIGURES_DIR = os.path.join(BASE_PATH, "figures")

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

MODEL_COMPARISON_PATH = os.path.join(RESULTS_DIR, "model_comparison.csv")
BEST_MODEL_PATH = os.path.join(MODELS_DIR, "best_model.pkl")
BEST_PREDICTIONS_PATH = os.path.join(RESULTS_DIR, "best_model_predictions.csv")
FEATURE_IMPORTANCE_PATH = os.path.join(RESULTS_DIR, "feature_importance.csv")
TRAINING_TIMES_PATH = os.path.join(RESULTS_DIR, "training_times.csv")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "benchmark_summary.txt")

ACTUAL_PRED_PLOT_PATH = os.path.join(FIGURES_DIR, "actual_vs_predicted.png")
RESIDUAL_PLOT_PATH = os.path.join(FIGURES_DIR, "residual_plot.png")
FEATURE_IMPORTANCE_PLOT_PATH = os.path.join(FIGURES_DIR, "feature_importance.png")

# ============================================================
# LOAD DATA
# ============================================================

X_train = pd.read_csv(X_TRAIN_PATH)
X_test = pd.read_csv(X_TEST_PATH)

y_train = pd.read_csv(Y_TRAIN_PATH).iloc[:, 0].to_numpy().ravel()
y_test = pd.read_csv(Y_TEST_PATH).iloc[:, 0].to_numpy().ravel()

print("=" * 80)
print("DATA LOADED")
print("=" * 80)
print(f"X_train: {X_train.shape}")
print(f"X_test : {X_test.shape}")
print(f"y_train: {y_train.shape}")
print(f"y_test : {y_test.shape}")

feature_names = X_train.columns.tolist()

# ============================================================
# OPTIONAL MODELS
# ============================================================

models = {
    "Linear Regression": LinearRegression(),
    "Decision Tree": DecisionTreeRegressor(random_state=42),
    "KNN": KNeighborsRegressor(n_neighbors=7),
    "SVR": SVR(),
    "Random Forest": RandomForestRegressor(
        n_estimators=400,
        random_state=42,
        n_jobs=-1,
    ),
    "Extra Trees": ExtraTreesRegressor(
        n_estimators=400,
        random_state=42,
        n_jobs=-1,
    ),
    "Gradient Boosting": GradientBoostingRegressor(random_state=42),
    "AdaBoost": AdaBoostRegressor(
        n_estimators=300,
        learning_rate=0.05,
        random_state=42,
    ),
    "Hist Gradient Boosting": HistGradientBoostingRegressor(
        random_state=42
    ),
}

# Try optional SOTA libraries if installed
try:
    from xgboost import XGBRegressor

    models["XGBoost"] = XGBRegressor(
        random_state=42,
        n_estimators=400,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
    )
    print("XGBoost found.")
except Exception:
    print("XGBoost not installed. Skipping.")

try:
    from lightgbm import LGBMRegressor

    models["LightGBM"] = LGBMRegressor(
        random_state=42,
        n_estimators=400,
        learning_rate=0.05,
    )
    print("LightGBM found.")
except Exception:
    print("LightGBM not installed. Skipping.")

try:
    from catboost import CatBoostRegressor

    models["CatBoost"] = CatBoostRegressor(
        random_state=42,
        verbose=False,
        iterations=400,
        learning_rate=0.05,
    )
    print("CatBoost found.")
except Exception:
    print("CatBoost not installed. Skipping.")

# ============================================================
# TRAIN + EVALUATE
# ============================================================

results = []
training_rows = []

best_model_name = None
best_model = None
best_predictions = None
best_r2 = -np.inf

print("\n" + "=" * 80)
print("TRAINING MODELS")
print("=" * 80)

for name, model in models.items():
    print(f"\nTraining: {name}")

    start_train = time.time()
    model.fit(X_train, y_train)
    training_time = time.time() - start_train

    start_pred = time.time()
    predictions = model.predict(X_test)
    prediction_time = time.time() - start_pred

    mae = mean_absolute_error(y_test, predictions)
    mse = mean_squared_error(y_test, predictions)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, predictions)

    results.append({
        "Model": name,
        "MAE": mae,
        "MSE": mse,
        "RMSE": rmse,
        "R2": r2,
        "Training_Time_Seconds": training_time,
        "Prediction_Time_Seconds": prediction_time,
    })

    training_rows.append({
        "Model": name,
        "Training_Time_Seconds": training_time,
        "Prediction_Time_Seconds": prediction_time,
    })

    model_file = os.path.join(MODELS_DIR, f"{name.replace(' ', '_').lower()}.pkl")
    joblib.dump(model, model_file)

    print(f"MAE  : {mae:.4f}")
    print(f"MSE  : {mse:.4f}")
    print(f"RMSE : {rmse:.4f}")
    print(f"R2   : {r2:.4f}")
    print(f"Train: {training_time:.2f}s | Predict: {prediction_time:.2f}s")

    if r2 > best_r2:
        best_r2 = r2
        best_model_name = name
        best_model = model
        best_predictions = predictions

# ============================================================
# RESULTS TABLE
# ============================================================

results_df = pd.DataFrame(results).sort_values(by="R2", ascending=False).reset_index(drop=True)
training_df = pd.DataFrame(training_rows).sort_values(by="Training_Time_Seconds").reset_index(drop=True)

results_df.to_csv(MODEL_COMPARISON_PATH, index=False)
training_df.to_csv(TRAINING_TIMES_PATH, index=False)

print("\n" + "=" * 80)
print("MODEL COMPARISON")
print("=" * 80)
print(results_df.round(4).to_string(index=False))

print("\n" + "=" * 80)
print("TRAINING TIMES")
print("=" * 80)
print(training_df.round(4).to_string(index=False))

print("\n" + "=" * 80)
print("BEST MODEL")
print("=" * 80)
print(f"Best Model: {best_model_name}")
print(f"Best R2   : {best_r2:.4f}")

joblib.dump(best_model, BEST_MODEL_PATH)

# ============================================================
# SAVE PREDICTIONS
# ============================================================

predictions_df = pd.DataFrame({
    "Actual": y_test,
    "Predicted": best_predictions,
    "Residual": y_test - best_predictions
})
predictions_df.to_csv(BEST_PREDICTIONS_PATH, index=False)

# ============================================================
# PLOTS: ACTUAL VS PREDICTED
# ============================================================

plt.figure(figsize=(8, 8))
plt.scatter(y_test, best_predictions, alpha=0.5)
min_val = min(y_test.min(), best_predictions.min())
max_val = max(y_test.max(), best_predictions.max())
plt.plot([min_val, max_val], [min_val, max_val], linestyle="--")
plt.xlabel("Actual")
plt.ylabel("Predicted")
plt.title(f"Actual vs Predicted - {best_model_name}")
plt.tight_layout()
plt.savefig(ACTUAL_PRED_PLOT_PATH, dpi=300)
plt.close()

# ============================================================
# PLOTS: RESIDUALS
# ============================================================

residuals = y_test - best_predictions

plt.figure(figsize=(8, 6))
plt.scatter(best_predictions, residuals, alpha=0.5)
plt.axhline(0, linestyle="--")
plt.xlabel("Predicted")
plt.ylabel("Residual")
plt.title(f"Residual Plot - {best_model_name}")
plt.tight_layout()
plt.savefig(RESIDUAL_PLOT_PATH, dpi=300)
plt.close()

# ============================================================
# FEATURE IMPORTANCE
# ============================================================

feature_importance_df = None

if hasattr(best_model, "feature_importances_"):
    feature_importance_df = pd.DataFrame({
        "Feature": feature_names,
        "Importance": best_model.feature_importances_
    }).sort_values(by="Importance", ascending=False)

elif hasattr(best_model, "coef_"):
    coef = best_model.coef_
    if coef.ndim > 1:
        coef = coef.ravel()
    feature_importance_df = pd.DataFrame({
        "Feature": feature_names,
        "Importance": np.abs(coef)
    }).sort_values(by="Importance", ascending=False)

else:
    perm = permutation_importance(
        best_model,
        X_test,
        y_test,
        n_repeats=10,
        random_state=42,
        scoring="r2",
        n_jobs=-1
    )
    feature_importance_df = pd.DataFrame({
        "Feature": feature_names,
        "Importance": perm.importances_mean
    }).sort_values(by="Importance", ascending=False)

feature_importance_df.to_csv(FEATURE_IMPORTANCE_PATH, index=False)

plt.figure(figsize=(10, 8))
top_features = feature_importance_df.head(15)
plt.barh(top_features["Feature"][::-1], top_features["Importance"][::-1])
plt.xlabel("Importance")
plt.title(f"Top Feature Importance - {best_model_name}")
plt.tight_layout()
plt.savefig(FEATURE_IMPORTANCE_PLOT_PATH, dpi=300)
plt.close()

# ============================================================
# SUMMARY FILE
# ============================================================

with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
    f.write("=" * 80 + "\n")
    f.write("MINDBALANCE MODEL BENCHMARK SUMMARY\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Best Model: {best_model_name}\n")
    f.write(f"Best R2   : {best_r2:.4f}\n\n")
    f.write("Top 10 Models by R2:\n")
    f.write(results_df.head(10).to_string(index=False))
    f.write("\n\nTop Features:\n")
    f.write(feature_importance_df.head(15).to_string(index=False))

# ============================================================
# FINAL OUTPUT
# ============================================================

print("\n" + "=" * 80)
print("SAVED FILES")
print("=" * 80)
print(f"✓ {MODEL_COMPARISON_PATH}")
print(f"✓ {TRAINING_TIMES_PATH}")
print(f"✓ {BEST_MODEL_PATH}")
print(f"✓ {BEST_PREDICTIONS_PATH}")
print(f"✓ {FEATURE_IMPORTANCE_PATH}")
print(f"✓ {ACTUAL_PRED_PLOT_PATH}")
print(f"✓ {RESIDUAL_PLOT_PATH}")
print(f"✓ {FEATURE_IMPORTANCE_PLOT_PATH}")
print(f"✓ {SUMMARY_PATH}")