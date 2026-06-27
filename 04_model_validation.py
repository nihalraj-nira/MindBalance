import os
import warnings
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.base import clone
from sklearn.model_selection import (
    train_test_split,
    KFold,
    cross_val_score,
    learning_curve,
)
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")

# ============================================================
# PATHS
# ============================================================

BASE_PATH = "."
RAW_DATA_PATH = os.path.join(BASE_PATH, "feature_engineered_dataset.csv")
BEST_MODEL_PATH = os.path.join(BASE_PATH, "models", "best_model.pkl")

RESULTS_DIR = os.path.join(BASE_PATH, "results")
FIGURES_DIR = os.path.join(BASE_PATH, "figures")

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

REPORT_PATH = os.path.join(RESULTS_DIR, "validation_report.txt")
CV_SCORES_PATH = os.path.join(RESULTS_DIR, "cross_validation_scores.csv")
ABLATION_PATH = os.path.join(RESULTS_DIR, "ablation_study.csv")

LEARNING_CURVE_PATH = os.path.join(FIGURES_DIR, "learning_curve.png")
RESIDUAL_HIST_PATH = os.path.join(FIGURES_DIR, "residual_histogram.png")
RESIDUAL_SCATTER_PATH = os.path.join(FIGURES_DIR, "residual_scatter.png")
CV_SCORES_PLOT_PATH = os.path.join(FIGURES_DIR, "cross_validation_scores.png")

# ============================================================
# HELPERS
# ============================================================

def choose_from_options(prompt_text, options):
    print("\n" + prompt_text)
    for idx, opt in enumerate(options):
        print(f"{idx}: {opt}")
    while True:
        try:
            choice = int(input("Enter choice number: ").strip())
            if 0 <= choice < len(options):
                return options[choice]
            print("Invalid choice. Try again.")
        except ValueError:
            print("Please enter a number.")

def recreate_estimator(template_model):
    """
    Recreate a fresh unfitted estimator of the same class.
    Works for sklearn models and usually for CatBoost/XGBoost/LightGBM too.
    """
    cls = template_model.__class__
    params = template_model.get_params()
    return cls(**params)

def make_preprocessed_data(df):
    """
    Reproduce the exact preprocessing used in 02_preprocessing.py so the
    saved best_model.pkl can be validated correctly.

    Note: this intentionally scales all numeric columns, including one-hot
    encoded columns, to match the current trained model pipeline.
    """
    df = df.copy()

    # Drop useless column if present
    if "Country" in df.columns:
        df = df.drop(columns=["Country"])

    # Feature engineering
    df["Sleep_Deficit"] = np.maximum(0, 8 - df["Sleep_Hours_Per_Night"])
    df["Usage_Age_Ratio"] = df["Avg_Daily_Usage_Hours"] / df["Age"]
    df["Recovery_Capacity"] = df["Sleep_Hours_Per_Night"] * df["Mental_Health_Score"]
    df["Psychosocial_Load"] = df["Avg_Daily_Usage_Hours"] * df["Conflicts_Over_Social_Media"]
    df["Lifestyle_Balance"] = df["Sleep_Hours_Per_Night"] / (df["Avg_Daily_Usage_Hours"] + 1)
    df["Wellness_Ratio"] = (
        (df["Mental_Health_Score"] * df["Sleep_Hours_Per_Night"]) /
        (df["Avg_Daily_Usage_Hours"] + 1)
    )
    df["Stress_Density"] = df["Conflicts_Over_Social_Media"] / (df["Mental_Health_Score"] + 1)

    # Binary encoding
    df["Gender"] = df["Gender"].map({"Male": 0, "Female": 1})
    df["Affects_Academic_Performance"] = df["Affects_Academic_Performance"].map({"No": 0, "Yes": 1})

    # Ordinal encoding
    academic_map = {
        "High School": 0,
        "Undergraduate": 1,
        "Graduate": 2
    }
    df["Academic_Level"] = df["Academic_Level"].map(academic_map)

    # Split X and y
    X = df.drop(columns=["Addicted_Score"])
    y = df["Addicted_Score"].copy()

    # Train/test split exactly like preprocessing
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42
    )

    # One-hot encoding on train only
    categorical_columns = [
        "Governorate",
        "Most_Used_Platform",
        "Relationship_Status"
    ]

    encoder = OneHotEncoder(
        drop="first",
        sparse_output=False,
        handle_unknown="ignore"
    )

    X_train_encoded = encoder.fit_transform(X_train[categorical_columns])
    X_test_encoded = encoder.transform(X_test[categorical_columns])

    encoded_feature_names = encoder.get_feature_names_out(categorical_columns)

    X_train_encoded = pd.DataFrame(
        X_train_encoded,
        columns=encoded_feature_names,
        index=X_train.index
    )
    X_test_encoded = pd.DataFrame(
        X_test_encoded,
        columns=encoded_feature_names,
        index=X_test.index
    )

    X_train = X_train.drop(columns=categorical_columns)
    X_test = X_test.drop(columns=categorical_columns)

    X_train = pd.concat([X_train, X_train_encoded], axis=1)
    X_test = pd.concat([X_test, X_test_encoded], axis=1)

    # Scale all numeric columns exactly like the current preprocessing script
    numeric_columns = X_train.select_dtypes(include="number").columns.tolist()

    scaler = StandardScaler()
    X_train[numeric_columns] = scaler.fit_transform(X_train[numeric_columns])
    X_test[numeric_columns] = scaler.transform(X_test[numeric_columns])

    return X_train, X_test, y_train, y_test, encoder, scaler

def risk_label(score):
    if score < 4.5:
        return "LOW"
    if score < 6.5:
        return "MODERATE"
    return "HIGH"

def ask_float(prompt_text, min_val=None, max_val=None):
    while True:
        try:
            val = float(input(prompt_text).strip())
            if min_val is not None and val < min_val:
                print(f"Value must be >= {min_val}")
                continue
            if max_val is not None and val > max_val:
                print(f"Value must be <= {max_val}")
                continue
            return val
        except ValueError:
            print("Please enter a valid number.")

def ask_int(prompt_text, min_val=None, max_val=None):
    while True:
        try:
            val = int(input(prompt_text).strip())
            if min_val is not None and val < min_val:
                print(f"Value must be >= {min_val}")
                continue
            if max_val is not None and val > max_val:
                print(f"Value must be <= {max_val}")
                continue
            return val
        except ValueError:
            print("Please enter a valid integer.")

def build_user_row():
    """
    Collect raw inputs, engineer features, then return a one-row dataframe
    that can be transformed using the same training preprocessor.
    """
    governorates = [
        "Assiut", "Aswan", "Beheira", "Cairo", "Dakahlia", "Fayoum",
        "Gharbia", "Giza", "Ismailia", "Luxor", "Minya", "Monufia",
        "Port Said", "Qalyubia", "Qena", "Red Sea", "Sharqia", "Sohag", "Suez"
    ]

    platforms = [
        "Facebook", "Instagram", "KakaoTalk", "LINE", "LinkedIn",
        "Snapchat", "TikTok", "Twitter", "VKontakte", "WeChat", "WhatsApp", "YouTube"
    ]

    relationship_statuses = [
        "Single", "In Relationship", "Complicated"
    ]

    academic_levels = [
        "High School", "Undergraduate", "Graduate"
    ]

    genders = ["Male", "Female"]
    yes_no = ["No", "Yes"]

    print("\n" + "=" * 70)
    print("USER PREDICTION INPUT")
    print("=" * 70)

    age = ask_float("Age: ", 10, 60)
    gender = choose_from_options("Gender:", genders)
    academic_level = choose_from_options("Academic Level:", academic_levels)
    governorate = choose_from_options("Governorate:", governorates)
    usage = ask_float("Avg Daily Usage Hours: ", 0, 24)
    platform = choose_from_options("Most Used Platform:", platforms)
    affects_academic = choose_from_options("Affects Academic Performance:", yes_no)
    sleep = ask_float("Sleep Hours Per Night: ", 0, 16)
    mental = ask_float("Mental Health Score (1-10): ", 1, 10)
    relationship = choose_from_options("Relationship Status:", relationship_statuses)
    conflicts = ask_float("Conflicts Over Social Media: ", 0, 50)

    sleep_deficit = max(0, 8 - sleep)
    usage_age_ratio = usage / age
    recovery_capacity = sleep * mental
    psychosocial_load = usage * conflicts
    lifestyle_balance = sleep / (usage + 1)
    wellness_ratio = (mental * sleep) / (usage + 1)
    stress_density = conflicts / (mental + 1)

    row = {
        "Age": age,
        "Gender": gender,
        "Academic_Level": academic_level,
        "Governorate": governorate,
        "Avg_Daily_Usage_Hours": usage,
        "Most_Used_Platform": platform,
        "Affects_Academic_Performance": affects_academic,
        "Sleep_Hours_Per_Night": sleep,
        "Mental_Health_Score": mental,
        "Relationship_Status": relationship,
        "Conflicts_Over_Social_Media": conflicts,
        "Sleep_Deficit": sleep_deficit,
        "Usage_Age_Ratio": usage_age_ratio,
        "Recovery_Capacity": recovery_capacity,
        "Psychosocial_Load": psychosocial_load,
        "Lifestyle_Balance": lifestyle_balance,
        "Wellness_Ratio": wellness_ratio,
        "Stress_Density": stress_density,
    }

    return pd.DataFrame([row])

def preprocess_single_row(user_df, encoder, scaler, train_columns):
    """
    Apply the same transformations used during training so the row matches
    the feature space of X_train / the saved best model.
    """
    user_df = user_df.copy()

    # Binary + ordinal mappings
    user_df["Gender"] = user_df["Gender"].map({"Male": 0, "Female": 1})
    user_df["Affects_Academic_Performance"] = user_df["Affects_Academic_Performance"].map({"No": 0, "Yes": 1})
    user_df["Academic_Level"] = user_df["Academic_Level"].map({
        "High School": 0,
        "Undergraduate": 1,
        "Graduate": 2
    })

    categorical_columns = [
        "Governorate",
        "Most_Used_Platform",
        "Relationship_Status"
    ]

    encoded = encoder.transform(user_df[categorical_columns])
    encoded_names = encoder.get_feature_names_out(categorical_columns)

    encoded_df = pd.DataFrame(encoded, columns=encoded_names)

    user_df = user_df.drop(columns=categorical_columns).reset_index(drop=True)
    user_df = pd.concat([user_df, encoded_df], axis=1)

    # Align columns with training columns
    for col in train_columns:
        if col not in user_df.columns:
            user_df[col] = 0

    user_df = user_df[train_columns]

    numeric_columns = user_df.select_dtypes(include="number").columns.tolist()
    user_df[numeric_columns] = scaler.transform(user_df[numeric_columns])

    return user_df

# ============================================================
# LOAD DATA + RECREATE PREPROCESSING
# ============================================================

raw_df = pd.read_csv(RAW_DATA_PATH)
X_train, X_test, y_train, y_test, encoder, scaler = make_preprocessed_data(raw_df)

print("=" * 70)
print("PREPROCESSED DATA RECREATED")
print("=" * 70)
print(f"X_train: {X_train.shape}")
print(f"X_test : {X_test.shape}")

# ============================================================
# LOAD BEST MODEL
# ============================================================

best_model_template = joblib.load(BEST_MODEL_PATH)
best_model_name = best_model_template.__class__.__name__
best_model = best_model_template

print("\n" + "=" * 70)
print("BEST MODEL LOADED")
print("=" * 70)
print(f"Best model class: {best_model_name}")

# ============================================================
# TRAIN / TEST EVALUATION
# ============================================================

train_pred = best_model.predict(X_train)
test_pred = best_model.predict(X_test)

train_mae = mean_absolute_error(y_train, train_pred)
train_mse = mean_squared_error(y_train, train_pred)
train_rmse = np.sqrt(train_mse)
train_r2 = r2_score(y_train, train_pred)

test_mae = mean_absolute_error(y_test, test_pred)
test_mse = mean_squared_error(y_test, test_pred)
test_rmse = np.sqrt(test_mse)
test_r2 = r2_score(y_test, test_pred)

generalization_gap = train_r2 - test_r2

# ============================================================
# CROSS VALIDATION
# ============================================================

cv_model = recreate_estimator(best_model_template)
kf = KFold(n_splits=5, shuffle=True, random_state=42)

cv_scores = cross_val_score(
    cv_model,
    X_train,
    y_train,
    cv=kf,
    scoring="r2",
    n_jobs=-1
)

cv_df = pd.DataFrame({
    "Fold": [1, 2, 3, 4, 5],
    "R2": cv_scores
})
cv_df.to_csv(CV_SCORES_PATH, index=False)

cv_mean = cv_scores.mean()
cv_std = cv_scores.std()

# ============================================================
# LEARNING CURVE
# ============================================================

lc_model = recreate_estimator(best_model_template)
train_sizes, train_scores, val_scores = learning_curve(
    lc_model,
    X_train,
    y_train,
    cv=kf,
    scoring="r2",
    train_sizes=np.linspace(0.1, 1.0, 6),
    n_jobs=-1,
    shuffle=True,
    random_state=42
)

train_mean = train_scores.mean(axis=1)
train_std = train_scores.std(axis=1)
val_mean = val_scores.mean(axis=1)
val_std = val_scores.std(axis=1)

plt.figure(figsize=(9, 6))
plt.plot(train_sizes, train_mean, marker="o", label="Training R2")
plt.plot(train_sizes, val_mean, marker="o", label="Validation R2")
plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.2)
plt.fill_between(train_sizes, val_mean - val_std, val_mean + val_std, alpha=0.2)
plt.xlabel("Training Samples")
plt.ylabel("R2 Score")
plt.title(f"Learning Curve - {best_model_name}")
plt.legend()
plt.tight_layout()
plt.savefig(LEARNING_CURVE_PATH, dpi=300)
plt.close()

# ============================================================
# RESIDUAL PLOTS
# ============================================================

test_residuals = y_test - test_pred

plt.figure(figsize=(8, 6))
plt.hist(test_residuals, bins=30, edgecolor="black")
plt.xlabel("Residual")
plt.ylabel("Frequency")
plt.title(f"Residual Histogram - {best_model_name}")
plt.tight_layout()
plt.savefig(RESIDUAL_HIST_PATH, dpi=300)
plt.close()

plt.figure(figsize=(8, 6))
plt.scatter(test_pred, test_residuals, alpha=0.5)
plt.axhline(0, linestyle="--")
plt.xlabel("Predicted")
plt.ylabel("Residual")
plt.title(f"Residual Scatter - {best_model_name}")
plt.tight_layout()
plt.savefig(RESIDUAL_SCATTER_PATH, dpi=300)
plt.close()

# ============================================================
# ABLATION STUDY
# ============================================================

ablated_df = raw_df.copy()
if "Affects_Academic_Performance" in ablated_df.columns:
    ablated_df = ablated_df.drop(columns=["Affects_Academic_Performance"])

# Rebuild the same feature engineering pipeline on the ablated dataframe
if "Country" in ablated_df.columns:
    ablated_df = ablated_df.drop(columns=["Country"])

ablated_df["Sleep_Deficit"] = np.maximum(0, 8 - ablated_df["Sleep_Hours_Per_Night"])
ablated_df["Usage_Age_Ratio"] = ablated_df["Avg_Daily_Usage_Hours"] / ablated_df["Age"]
ablated_df["Recovery_Capacity"] = ablated_df["Sleep_Hours_Per_Night"] * ablated_df["Mental_Health_Score"]
ablated_df["Psychosocial_Load"] = ablated_df["Avg_Daily_Usage_Hours"] * ablated_df["Conflicts_Over_Social_Media"]
ablated_df["Lifestyle_Balance"] = ablated_df["Sleep_Hours_Per_Night"] / (ablated_df["Avg_Daily_Usage_Hours"] + 1)
ablated_df["Wellness_Ratio"] = (
    (ablated_df["Mental_Health_Score"] * ablated_df["Sleep_Hours_Per_Night"]) /
    (ablated_df["Avg_Daily_Usage_Hours"] + 1)
)
ablated_df["Stress_Density"] = ablated_df["Conflicts_Over_Social_Media"] / (ablated_df["Mental_Health_Score"] + 1)

ablated_df["Gender"] = ablated_df["Gender"].map({"Male": 0, "Female": 1})
academic_map = {"High School": 0, "Undergraduate": 1, "Graduate": 2}
ablated_df["Academic_Level"] = ablated_df["Academic_Level"].map(academic_map)

y_ablate = ablated_df["Addicted_Score"].copy()
X_ablate = ablated_df.drop(columns=["Addicted_Score"])

X_ablate_train, X_ablate_test, y_ablate_train, y_ablate_test = train_test_split(
    X_ablate, y_ablate, test_size=0.20, random_state=42
)

ablate_cat_cols = ["Governorate", "Most_Used_Platform", "Relationship_Status"]
ablate_encoder = OneHotEncoder(drop="first", sparse_output=False, handle_unknown="ignore")

X_ablate_train_encoded = ablate_encoder.fit_transform(X_ablate_train[ablate_cat_cols])
X_ablate_test_encoded = ablate_encoder.transform(X_ablate_test[ablate_cat_cols])

ablate_feature_names = ablate_encoder.get_feature_names_out(ablate_cat_cols)

X_ablate_train_encoded = pd.DataFrame(
    X_ablate_train_encoded,
    columns=ablate_feature_names,
    index=X_ablate_train.index
)
X_ablate_test_encoded = pd.DataFrame(
    X_ablate_test_encoded,
    columns=ablate_feature_names,
    index=X_ablate_test.index
)

X_ablate_train = X_ablate_train.drop(columns=ablate_cat_cols)
X_ablate_test = X_ablate_test.drop(columns=ablate_cat_cols)

X_ablate_train = pd.concat([X_ablate_train, X_ablate_train_encoded], axis=1)
X_ablate_test = pd.concat([X_ablate_test, X_ablate_test_encoded], axis=1)

ablate_numeric = X_ablate_train.select_dtypes(include="number").columns.tolist()
ablate_scaler = StandardScaler()
X_ablate_train[ablate_numeric] = ablate_scaler.fit_transform(X_ablate_train[ablate_numeric])
X_ablate_test[ablate_numeric] = ablate_scaler.transform(X_ablate_test[ablate_numeric])

ablation_model = recreate_estimator(best_model_template)
ablation_model.fit(X_ablate_train, y_ablate_train)
ablation_pred = ablation_model.predict(X_ablate_test)

ablation_mae = mean_absolute_error(y_ablate_test, ablation_pred)
ablation_rmse = np.sqrt(mean_squared_error(y_ablate_test, ablation_pred))
ablation_r2 = r2_score(y_ablate_test, ablation_pred)

ablation_df = pd.DataFrame([{
    "Setting": "Without Affects_Academic_Performance",
    "MAE": ablation_mae,
    "RMSE": ablation_rmse,
    "R2": ablation_r2
}])
ablation_df.to_csv(ABLATION_PATH, index=False)

# ============================================================
# USER PREDICTION MODE
# ============================================================

print("\n" + "=" * 70)
print("MANUAL USER PREDICTION")
print("=" * 70)

run_user_test = input("Do you want to test a custom student input now? (y/n): ").strip().lower()

if run_user_test == "y":
    user_raw = build_user_row()
    user_processed = preprocess_single_row(
        user_raw,
        encoder=encoder,
        scaler=scaler,
        train_columns=X_train.columns.tolist()
    )

    user_score = float(best_model.predict(user_processed)[0])
    user_risk = risk_label(user_score)

    print("\n" + "=" * 70)
    print("PREDICTION RESULT")
    print("=" * 70)
    print(f"Predicted Addicted Score: {user_score:.3f}")
    print(f"Risk Level: {user_risk}")

    print("\n" + "=" * 70)
    print("INTERPRETATION")
    print("=" * 70)
    if user_score < 4.5:
        print("Low risk behavior. Habits look relatively balanced.")
    elif user_score < 6.5:
        print("Moderate risk behavior. Some habits may need attention.")
    else:
        print("High risk behavior. Sleep, usage, and stress factors need attention.")

# ============================================================
# SUMMARY REPORT
# ============================================================

report_lines = []
report_lines.append("=" * 70)
report_lines.append("MINDBALANCE MODEL VALIDATION REPORT")
report_lines.append("=" * 70)
report_lines.append("")
report_lines.append(f"Best Model: {best_model_name}")
report_lines.append("")
report_lines.append("TRAIN vs TEST")
report_lines.append(f"Train R2  : {train_r2:.4f}")
report_lines.append(f"Test R2   : {test_r2:.4f}")
report_lines.append(f"Gap       : {generalization_gap:.4f}")
report_lines.append(f"Train MAE : {train_mae:.4f}")
report_lines.append(f"Test MAE  : {test_mae:.4f}")
report_lines.append(f"Train RMSE: {train_rmse:.4f}")
report_lines.append(f"Test RMSE : {test_rmse:.4f}")
report_lines.append("")
report_lines.append("5-FOLD CROSS VALIDATION")
report_lines.append(f"CV Mean R2 : {cv_mean:.4f}")
report_lines.append(f"CV Std R2  : {cv_std:.4f}")
report_lines.append("")
report_lines.append("ABLATION STUDY")
report_lines.append("Without Affects_Academic_Performance")
report_lines.append(f"R2   : {ablation_r2:.4f}")
report_lines.append(f"MAE  : {ablation_mae:.4f}")
report_lines.append(f"RMSE : {ablation_rmse:.4f}")
report_lines.append("")
report_lines.append("INTERPRETATION")
if generalization_gap < 0.03:
    report_lines.append("Generalization looks strong. No obvious severe overfitting.")
elif generalization_gap < 0.08:
    report_lines.append("Generalization is acceptable, but there is some gap to watch.")
else:
    report_lines.append("Possible overfitting risk. The train-test gap is large.")

report_lines.append("")
report_lines.append("SAVED FILES")
report_lines.append(f"✓ {CV_SCORES_PATH}")
report_lines.append(f"✓ {ABLATION_PATH}")
report_lines.append(f"✓ {LEARNING_CURVE_PATH}")
report_lines.append(f"✓ {RESIDUAL_HIST_PATH}")
report_lines.append(f"✓ {RESIDUAL_SCATTER_PATH}")
report_lines.append(f"✓ {CV_SCORES_PLOT_PATH}")

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))

# ============================================================
# CV PLOT
# ============================================================

plt.figure(figsize=(8, 5))
plt.bar(["Fold 1", "Fold 2", "Fold 3", "Fold 4", "Fold 5"], cv_scores)
plt.axhline(cv_mean, linestyle="--")
plt.ylabel("R2 Score")
plt.title(f"5-Fold Cross Validation - {best_model_name}")
plt.tight_layout()
plt.savefig(CV_SCORES_PLOT_PATH, dpi=300)
plt.close()

# ============================================================
# FINAL PRINT
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION RESULTS")
print("=" * 70)
print(f"Train R2 : {train_r2:.4f}")
print(f"Test R2  : {test_r2:.4f}")
print(f"Gap      : {generalization_gap:.4f}")
print(f"CV Mean  : {cv_mean:.4f} ± {cv_std:.4f}")
print(f"Ablation R2 (without academic feature): {ablation_r2:.4f}")
print(f"Manual report saved to: {REPORT_PATH}")

print("\n" + "=" * 70)
print("SAVED FILES")
print("=" * 70)
print(f"✓ {REPORT_PATH}")
print(f"✓ {CV_SCORES_PATH}")
print(f"✓ {ABLATION_PATH}")
print(f"✓ {LEARNING_CURVE_PATH}")
print(f"✓ {RESIDUAL_HIST_PATH}")
print(f"✓ {RESIDUAL_SCATTER_PATH}")
print(f"✓ {CV_SCORES_PLOT_PATH}")
