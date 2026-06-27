import pandas as pd
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# ============================================================
# LOAD FEATURE ENGINEERED DATASET
# ============================================================

DATA_PATH = "feature_engineered_dataset.csv"

df = pd.read_csv(DATA_PATH)

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
    df["Academic_Level"].map(academic_map)
)

# ============================================================
# SPLIT FEATURES AND TARGET
# ============================================================

X = df.drop(columns=["Addicted_Score"])
y = df["Addicted_Score"]

# ============================================================
# TRAIN TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)

# ============================================================
# ONE HOT ENCODING
# ============================================================

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

# Learn categories from training data
X_train_encoded = encoder.fit_transform(
    X_train[categorical_columns]
)

# Apply same categories to test data
X_test_encoded = encoder.transform(
    X_test[categorical_columns]
)

# Convert to DataFrames
encoded_feature_names = encoder.get_feature_names_out(
    categorical_columns
)

X_train_encoded = pd.DataFrame(
    X_train_encoded,
    columns=encoded_feature_names,
    index=X_train.index
)

X_test_encoded = pd.DataFrame(
    X_test_encoded, # type: ignore
    columns=encoded_feature_names,
    index=X_test.index
) # type: ignore

# Remove original categorical columns
X_train = X_train.drop(columns=categorical_columns)
X_test = X_test.drop(columns=categorical_columns)

# Merge encoded columns
X_train = pd.concat(
    [X_train, X_train_encoded],
    axis=1
)

X_test = pd.concat(
    [X_test, X_test_encoded],
    axis=1
)

# ============================================================
# FEATURE SCALING
# ============================================================

numeric_columns = X_train.select_dtypes(include="number").columns

scaler = StandardScaler()

X_train[numeric_columns] = scaler.fit_transform(
    X_train[numeric_columns]
)

X_test[numeric_columns] = scaler.transform(
    X_test[numeric_columns]
)

# ============================================================
# SAVE PREPROCESSED DATA
# ============================================================

OUTPUT_DIR = ""

X_train.to_csv(
    OUTPUT_DIR + "X_train.csv",
    index=False
)

X_test.to_csv(
    OUTPUT_DIR + "X_test.csv",
    index=False
)

y_train.to_csv(
    OUTPUT_DIR + "y_train.csv",
    index=False
)

y_test.to_csv(
    OUTPUT_DIR + "y_test.csv",
    index=False
)


os.makedirs(
    "models",
    exist_ok=True
)

joblib.dump(
    encoder,"models/encoder.pkl" # type: ignore
)

joblib.dump(
    scaler, # type: ignore
    "models/scaler.pkl"
)


print("=" * 70)
print("PREPROCESSING COMPLETED")
print("=" * 70)

print(f"Training Shape : {X_train.shape}")
print(f"Testing Shape  : {X_test.shape}")

print("\nFiles Saved:")
print("✓ X_train.csv")
print("✓ X_test.csv")
print("✓ y_train.csv")
print("✓ y_test.csv")
print("✓ encoder.pkl")
print("✓ scaler.pkl")
