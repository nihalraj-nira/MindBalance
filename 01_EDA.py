import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================
# PATHS
# ============================================================

DATA_PATH = "C:/Users/Khush/Desktop/HACKATHON/dataset.csv"
OUTPUT_DIR = "C:/Users/Khush/Desktop/HACKATHON"
FEATURE_ENGINEERED_PATH = os.path.join(OUTPUT_DIR, "feature_engineered_dataset.csv")
CORRELATION_TABLE_PATH = os.path.join(OUTPUT_DIR, "feature_correlations.csv")
HIGH_CORR_PATH = os.path.join(OUTPUT_DIR, "highly_correlated_features.csv")
SUMMARY_STATS_PATH = os.path.join(OUTPUT_DIR, "summary_statistics.csv")
CORR_HEATMAP_PATH = os.path.join(OUTPUT_DIR, "correlation_heatmap.png")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(DATA_PATH)

# ============================================================
# REMOVE USELESS FEATURES
# ============================================================

# Country contains only "Egypt"
if "Country" in df.columns:
    if df["Country"].nunique(dropna=False) == 1:
        df.drop(columns=["Country"], inplace=True)

# ============================================================
# FEATURE ENGINEERING
# ============================================================

# ---------- Sleep ----------
df["Sleep_Deficit"] = np.maximum(
    0,
    8 - df["Sleep_Hours_Per_Night"]
)

# ---------- Usage ----------
df["Usage_Age_Ratio"] = (
    df["Avg_Daily_Usage_Hours"] /
    df["Age"]
)

# ---------- Interaction Features ----------
df["Recovery_Capacity"] = (
    df["Sleep_Hours_Per_Night"] *
    df["Mental_Health_Score"]
)

df["Psychosocial_Load"] = (
    df["Avg_Daily_Usage_Hours"] *
    df["Conflicts_Over_Social_Media"]
)

# ---------- Behaviour Features ----------
df["Lifestyle_Balance"] = (
    df["Sleep_Hours_Per_Night"] /
    (df["Avg_Daily_Usage_Hours"] + 1)
)

df["Wellness_Ratio"] = (
    (
        df["Mental_Health_Score"] *
        df["Sleep_Hours_Per_Night"]
    ) /
    (df["Avg_Daily_Usage_Hours"] + 1)
)

df["Stress_Density"] = (
    df["Conflicts_Over_Social_Media"] /
    (df["Mental_Health_Score"] + 1)
)

# ============================================================
# NUMERICAL CORRELATION
# ============================================================

print("=" * 70)
print("CORRELATION WITH ADDICTED SCORE")
print("=" * 70)

corr = df.select_dtypes(include=np.number).corr()

target_corr = corr["Addicted_Score"].sort_values(ascending=False)
print(target_corr)

# Save correlation ranking
target_corr.to_csv(CORRELATION_TABLE_PATH, header=["Correlation"])

# ============================================================
# HIGHLY CORRELATED FEATURES
# ============================================================

print("\n")
print("=" * 70)
print("FEATURES HAVING |CORRELATION| > 0.90")
print("=" * 70)

high_corr = []
columns = corr.columns

for i in range(len(columns)):
    for j in range(i + 1, len(columns)):
        value = corr.iloc[i, j]
        if abs(value) > 0.90: # type: ignore
            high_corr.append(
                (
                    columns[i],
                    columns[j],
                    round(float(value), 3)
                )
            )

for item in high_corr:
    print(item)

high_corr_df = pd.DataFrame(
    high_corr,
    columns=["Feature 1", "Feature 2", "Correlation"]
)
high_corr_df.to_csv(HIGH_CORR_PATH, index=False)

# ============================================================
# CORRELATION HEATMAP
# ============================================================

plt.figure(figsize=(16, 12))
sns.heatmap(
    corr,
    cmap="coolwarm",
    center=0,
    square=False,
    linewidths=0.2
)
plt.title("Correlation Matrix")
plt.tight_layout()
plt.savefig(CORR_HEATMAP_PATH, dpi=300)
plt.close()

# ============================================================
# TARGET DISTRIBUTION
# ============================================================

print("\n")
print("=" * 70)
print("TARGET STATISTICS")
print("=" * 70)

print(df["Addicted_Score"].describe())

print("\n")

print(df["Addicted_Score"].value_counts().sort_index())

# ============================================================
# CATEGORICAL FEATURES
# ============================================================

print("\n")
print("=" * 70)
print("CATEGORICAL FEATURES")
print("=" * 70)

categorical_columns = [
    "Gender",
    "Academic_Level",
    "Governorate",
    "Most_Used_Platform",
    "Relationship_Status",
    "Affects_Academic_Performance"
]

for col in categorical_columns:
    print(f"\n----- {col} -----")
    print(df[col].value_counts())

# ============================================================
# DATASET INFO
# ============================================================

print("\n")
print("=" * 70)
print("DATASET INFORMATION")
print("=" * 70)

print("\nShape :", df.shape)

print("\nColumns :")
for c in df.columns:
    print(c)

print("\nMissing Values")
print(df.isnull().sum())

print("\nData Types")
print(df.dtypes)

print("\nFirst Five Rows")
print(df.head())

# Save summary statistics
df.describe(include="all").to_csv(SUMMARY_STATS_PATH)

# ============================================================
# OPTIONAL OUTLIER CHECK
# ============================================================

print("\n")
print("=" * 70)
print("OUTLIER CHECK (IQR METHOD)")
print("=" * 70)

numerical_cols = df.select_dtypes(include=np.number).columns

for col in numerical_cols:
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outliers = df[(df[col] < lower) | (df[col] > upper)]
    print(f"{col}: {len(outliers)} outliers")

# ============================================================
# SAVE FEATURE ENGINEERED DATASET
# ============================================================

df.to_csv(FEATURE_ENGINEERED_PATH, index=False)

print("\n")
print("=" * 70)
print("FEATURE ENGINEERED DATASET SAVED SUCCESSFULLY")
print(FEATURE_ENGINEERED_PATH)
print("=" * 70)