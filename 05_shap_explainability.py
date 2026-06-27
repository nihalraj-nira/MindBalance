import os
import warnings
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import shap

warnings.filterwarnings("ignore")

# ============================================================
# PATHS
# ============================================================

BASE_PATH = "C:/Users/Khush/Desktop/HACKATHON"

X_TRAIN_PATH = os.path.join(BASE_PATH, "X_train.csv")
X_TEST_PATH = os.path.join(BASE_PATH, "X_test.csv")
Y_TRAIN_PATH = os.path.join(BASE_PATH, "y_train.csv")
Y_TEST_PATH = os.path.join(BASE_PATH, "y_test.csv")

BEST_MODEL_PATH = os.path.join(BASE_PATH, "models", "best_model.pkl")

FIGURES_DIR = os.path.join(BASE_PATH, "figures")
RESULTS_DIR = os.path.join(BASE_PATH, "results")

os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

SHAP_SUMMARY_BAR_PATH = os.path.join(FIGURES_DIR, "shap_summary_bar.png")
SHAP_SUMMARY_BEESWARM_PATH = os.path.join(FIGURES_DIR, "shap_summary_beeswarm.png")
SHAP_DEPENDENCE_DIR = os.path.join(FIGURES_DIR, "shap_dependence")
SHAP_TOP5_PATH = os.path.join(RESULTS_DIR, "shap_top5_per_student.csv")
SHAP_GLOBAL_PATH = os.path.join(RESULTS_DIR, "shap_global_importance.csv")

os.makedirs(SHAP_DEPENDENCE_DIR, exist_ok=True)

# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("LOADING DATA AND MODEL")
print("=" * 70)

X_train = pd.read_csv(X_TRAIN_PATH)
X_test = pd.read_csv(X_TEST_PATH)

y_train = pd.read_csv(Y_TRAIN_PATH).iloc[:, 0].to_numpy().ravel()
y_test = pd.read_csv(Y_TEST_PATH).iloc[:, 0].to_numpy().ravel()

print(f"X_train: {X_train.shape}")
print(f"X_test : {X_test.shape}")

feature_names = X_train.columns.tolist()

# ============================================================
# LOAD BEST MODEL
# ============================================================

model = joblib.load(BEST_MODEL_PATH)
model_name = model.__class__.__name__

print(f"Best Model: {model_name}")
print()

# ============================================================
# CREATE SHAP EXPLAINER
# ============================================================

print("=" * 70)
print("COMPUTING SHAP VALUES")
print("=" * 70)

# Use TreeExplainer for tree-based models (faster)
# Fall back to generic Explainer for others
tree_models = (
    "RandomForestRegressor", "ExtraTreesRegressor",
    "GradientBoostingRegressor", "HistGradientBoostingRegressor",
    "XGBRegressor", "LGBMRegressor", "CatBoostRegressor",
    "DecisionTreeRegressor", "AdaBoostRegressor",
)

if model_name in tree_models:
    print(f"Using TreeExplainer (optimised for {model_name})")
    explainer = shap.TreeExplainer(model)
else:
    print(f"Using generic Explainer for {model_name}")
    explainer = shap.Explainer(model, X_train)

# Compute SHAP values on test set
shap_values = explainer(X_test)

print(f"SHAP values shape: {shap_values.values.shape}")
print("SHAP computation complete!")
print()

# ============================================================
# PLOT 1: GLOBAL FEATURE IMPORTANCE (BAR)
# ============================================================

print("=" * 70)
print("GENERATING SHAP PLOTS")
print("=" * 70)

plt.figure(figsize=(12, 8))
shap.summary_plot(
    shap_values,
    X_test,
    plot_type="bar",
    max_display=15,
    show=False
)
plt.title(f"SHAP Global Feature Importance - {model_name}", fontsize=14)
plt.tight_layout()
plt.savefig(SHAP_SUMMARY_BAR_PATH, dpi=300, bbox_inches="tight")
plt.close()
print(f"Saved: {SHAP_SUMMARY_BAR_PATH}")

# ============================================================
# PLOT 2: BEESWARM PLOT (DETAILED IMPACT)
# ============================================================

plt.figure(figsize=(12, 8))
shap.summary_plot(
    shap_values,
    X_test,
    max_display=15,
    show=False
)
plt.title(f"SHAP Beeswarm Plot - {model_name}", fontsize=14)
plt.tight_layout()
plt.savefig(SHAP_SUMMARY_BEESWARM_PATH, dpi=300, bbox_inches="tight")
plt.close()
print(f"Saved: {SHAP_SUMMARY_BEESWARM_PATH}")

# ============================================================
# PLOT 3: DEPENDENCE PLOTS (TOP 5 FEATURES)
# ============================================================

mean_abs_shap = np.abs(shap_values.values).mean(axis=0)
top_indices = np.argsort(-mean_abs_shap)[:5]
top_feature_names = [feature_names[i] for i in top_indices]

print(f"\nTop 5 Features by SHAP: {top_feature_names}")

for feat in top_feature_names:
    plt.figure(figsize=(8, 5))
    shap.dependence_plot(
        feat,
        shap_values.values,
        X_test,
        feature_names=feature_names,
        show=False
    )
    plt.title(f"SHAP Dependence: {feat}", fontsize=12)
    plt.tight_layout()
    safe_name = feat.replace(" ", "_").replace("/", "_")
    save_path = os.path.join(SHAP_DEPENDENCE_DIR, f"dependence_{safe_name}.png")
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {save_path}")

# ============================================================
# GLOBAL IMPORTANCE TABLE (CSV)
# ============================================================

global_importance = pd.DataFrame({
    "Feature": feature_names,
    "Mean_Abs_SHAP": mean_abs_shap
}).sort_values(by="Mean_Abs_SHAP", ascending=False)

global_importance.to_csv(SHAP_GLOBAL_PATH, index=False)
print(f"\nSaved: {SHAP_GLOBAL_PATH}")

# ============================================================
# PER-STUDENT TOP-5 EXPLANATIONS (CSV)
# ============================================================

print("\n" + "=" * 70)
print("GENERATING PER-STUDENT EXPLANATIONS")
print("=" * 70)

k = 5
top_features_per_row = np.argsort(-np.abs(shap_values.values), axis=1)[:, :k]

rows = []
for i, idxs in enumerate(top_features_per_row):
    row = {"Student_ID": i}
    for rank, col_idx in enumerate(idxs, start=1):
        col_name = feature_names[col_idx]
        shap_val = shap_values.values[i, col_idx]
        row[f"Feature_{rank}"] = col_name
        row[f"SHAP_{rank}"] = round(float(shap_val), 4)
        row[f"Direction_{rank}"] = "Increases Risk" if shap_val > 0 else "Decreases Risk"
    rows.append(row)

shap_table = pd.DataFrame(rows)
shap_table.to_csv(SHAP_TOP5_PATH, index=False)
print(f"Saved: {SHAP_TOP5_PATH}")

# ============================================================
# SANITY CHECK
# ============================================================

print("\n" + "=" * 70)
print("SANITY CHECK")
print("=" * 70)

predictions = model.predict(X_test)
shap_sums = shap_values.values.sum(axis=1)
corr = np.corrcoef(predictions, shap_sums)[0, 1]
print(f"Correlation (model predictions vs summed SHAP): {corr:.4f}")

if corr > 0.9:
    print("Excellent - SHAP decomposition is highly consistent with model.")
elif corr > 0.7:
    print("Good - SHAP decomposition is reasonably consistent with model.")
else:
    print("Warning - SHAP decomposition may not fully capture model behaviour.")

# ============================================================
# PRINT SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("SHAP EXPLAINABILITY SUMMARY")
print("=" * 70)

print(f"\nModel: {model_name}")
print(f"\nTop 10 Most Important Features (by mean |SHAP|):")
print(global_importance.head(10).to_string(index=False))

print("\n\nKey Insights:")
for i, row in global_importance.head(5).iterrows():
    feat = row["Feature"]
    imp = row["Mean_Abs_SHAP"]
    print(f"  - {feat}: mean |SHAP| = {imp:.4f}")

# ============================================================
# SAVED FILES
# ============================================================

print("\n" + "=" * 70)
print("SAVED FILES")
print("=" * 70)
print(f"  {SHAP_SUMMARY_BAR_PATH}")
print(f"  {SHAP_SUMMARY_BEESWARM_PATH}")
print(f"  {SHAP_DEPENDENCE_DIR}/  (5 dependence plots)")
print(f"  {SHAP_GLOBAL_PATH}")
print(f"  {SHAP_TOP5_PATH}")
print("=" * 70)
