import joblib
import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.metrics import classification_report, confusion_matrix
from imblearn.pipeline import Pipeline as ImbPipeline 
from imblearn.over_sampling import SMOTE

# ==========================================
# KONFIGURASI PATH
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
DATA_DIR = PROJECT_ROOT / "data"

# PATHS = {
#     "X_train": DATA_DIR / "tokenize" / "train" / "X_train_tfidf.pkl",
#     "y_train": DATA_DIR / "tokenize" / "train" / "y_train.pkl",
#     "X_test":  DATA_DIR / "tokenize" / "test" / "X_test_tfidf.pkl",
#     "y_test":  DATA_DIR / "tokenize" / "test" / "y_test.pkl",
#     "le":      DATA_DIR / "tokenize" / "label_encoder.pkl",
# }

PATHS = {
    "X_train": PROJECT_ROOT / "X_train_tfidf.pkl",
    "y_train": PROJECT_ROOT / "y_train.pkl",
    "X_test":  PROJECT_ROOT / "X_test_tfidf.pkl",
    "y_test":  PROJECT_ROOT / "y_test.pkl",
    "le":      PROJECT_ROOT / "label_encoder.pkl",
}

print("--- MENYIAPKAN TRAINING SCENARIO 3 (PIPELINE: SMOTE + CHI2 + XGBOOST) ---")

# Load Data
data = {}
for name, path in PATHS.items():
    if not path.exists():
        print(f"❌ ERROR: File tidak ditemukan → {path}")
        sys.exit(1)
    data[name] = joblib.load(path)
    print(f"✅ Loaded: {path}")

X_train, y_train = data["X_train"], data["y_train"]
X_test, y_test = data["X_test"], data["y_test"]
le = data["le"]

# ==========================================
# REPORT PROPORSI DATA (SEBELUM & SESUDAH SMOTE)
# ==========================================
print("\n" + "="*40)
print("REPORT PROPORSI DATA")
print("="*40)

def print_proportion(y, title):
    unique, counts = np.unique(y, return_counts=True)
    print(f"\n[{title}]")
    for u, c in zip(unique, counts):
        label = le.inverse_transform([u])[0]
        print(f"  - {label:8}: {c} sampel ({c/len(y)*100:.2f}%)")

print_proportion(y_train, "PROPORSI DATA AWAL (TRAIN)")

# Simulasi SMOTE untuk melihat hasil akhir yang akan diproses Pipeline
sm_sim = SMOTE(random_state=42)
_, y_resampled_sim = sm_sim.fit_resample(X_train, y_train)
print_proportion(y_resampled_sim, "ESTIMASI PROPORSI SETELAH SMOTE (DALAM PIPELINE)")

print("\n" + "="*40)

# ==========================================
# DEFINISI PIPELINE
# ==========================================
pipeline = ImbPipeline([
    ('smote', SMOTE(random_state=42)), 
    ('selector', SelectKBest(score_func=chi2, k=2000)), 
    ('clf', XGBClassifier(
        objective='multi:softprob',
        num_class=3,
        random_state=42,
        eval_metric='mlogloss',
        use_label_encoder=False
    ))
])

# ==========================================
# SETTING GRID SEARCH
# ==========================================
param_grid = {
    'clf__learning_rate': [0.1, 0.2],
    'clf__max_depth': [5, 7],
    'clf__n_estimators': [100, 200],
    'clf__subsample': [0.8, 1.0],
}

grid_search = GridSearchCV(
    estimator=pipeline,
    param_grid=param_grid,
    cv=3,
    scoring='f1_macro',
    n_jobs=-1,
    verbose=2
)

# ==========================================
# EKSEKUSI TRAINING
# ==========================================
print(f"\n🔥 MULAI TRAINING... (Dimensi Awal: {X_train.shape})")
start_time = time.time()

grid_search.fit(X_train, y_train)

duration = time.time() - start_time
print(f"\n✅ SELESAI! Waktu proses: {duration/60:.2f} menit")

# ==========================================
# EVALUASI
# ==========================================
best_model = grid_search.best_estimator_

print("\n" + "="*40)
print("HASIL PARAMETER TERBAIK")
print("="*40)
print(grid_search.best_params_)

y_pred = best_model.predict(X_test)

# Inverse Transform Label
y_test_label = le.inverse_transform(y_test)
y_pred_label = le.inverse_transform(y_pred)

print("\nClassification Report:")
print(classification_report(y_test_label, y_pred_label))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test_label, y_pred_label))

# ==========================================
# SIMPAN MODEL
# ==========================================
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)
model_path = MODEL_DIR / "final_pipeline_scenario3.pkl"
joblib.dump(best_model, model_path)

print(f"\n💾 Model disimpan ke: {model_path}")