"""
STEP 2 — SMOTE + XGBoost + Grid Search CV
==========================================
Urutan yang benar:
  Data masuk → SMOTE (dalam fold CV) → XGBoost

  Mengapa SMOTE di DALAM pipeline CV (bukan di luar)?
  - Jika SMOTE dijalankan di luar CV (sekali sebelum fit), sampel sintetis
    dari data validasi bisa "bocor" ke data train setiap fold → metrik CV
    terlalu optimis, tidak merepresentasikan performa pada data baru.
  - Dengan SMOTE di dalam pipeline, tiap fold:
      1. Data train fold di-resample dengan SMOTE
      2. Data validasi fold TIDAK disentuh SMOTE
    → evaluasi CV lebih jujur dan reliable.

  Chi-Square sudah selesai di step1 (fit pada distribusi asli),
  jadi di sini kita TIDAK perlu SelectKBest lagi.

Input  : output dari step1_feature_selection.py
Output : best_model_step2.pkl, grid_search_results.csv
"""

import joblib
import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

# ── Path konfigurasi ───────────────────────────────────────────────────────────
SCRIPT_DIR   = Path("robust_data")
SEL_DIR      = SCRIPT_DIR/ "selected"
MODEL_DIR    = SCRIPT_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

PATHS = {
    "X_train": SEL_DIR / "X_train_selected.pkl",
    "y_train": SEL_DIR / "y_train.pkl",
    "X_test":  SEL_DIR / "X_test_selected.pkl",
    "y_test":  SEL_DIR / "y_test.pkl",
    "le":      SEL_DIR / "label_encoder.pkl",
}

# ── Muat data hasil step1 ──────────────────────────────────────────────────────
print("=" * 55)
print("STEP 2 — SMOTE + XGBOOST + GRID SEARCH CV")
print("=" * 55)

data = {}
for name, path in PATHS.items():
    if not path.exists():
        print(f"❌ File tidak ditemukan: {path}")
        print("   Pastikan step1_feature_selection.py sudah dijalankan.")
        sys.exit(1)
    data[name] = joblib.load(path)
    print(f"✅ Loaded: {path.name}")

X_train = data["X_train"]
y_train = data["y_train"]
X_test  = data["X_test"]
y_test  = data["y_test"]
le      = data["le"]

print(f"\nDimensi X_train (post chi2): {X_train.shape}")
print(f"Dimensi X_test  (post chi2): {X_test.shape}")

# ── Proporsi kelas ─────────────────────────────────────────────────────────────
def print_proportion(y, title, le):
    unique, counts = np.unique(y, return_counts=True)
    print(f"\n[{title}]")
    for u, c in zip(unique, counts):
        label = str(le.inverse_transform([u])[0]) # Pastikan label dicetak sebagai string
        print(f"  {label:10}: {c:6,} sampel ({c/len(y)*100:.2f}%)")

print_proportion(y_train, "PROPORSI TRAIN (sebelum SMOTE)", le)

# ── Pipeline: SMOTE → XGBoost ──────────────────────────────────────────────────
pipeline = ImbPipeline([
    ("smote", SMOTE(random_state=42)),
    ("clf", XGBClassifier(
        objective="multi:softprob",
        num_class=len(np.unique(y_train)),
        random_state=42,
        eval_metric="mlogloss",
        use_label_encoder=False,
        tree_method="hist",     # lebih cepat untuk data besar
        device="cpu",
    )),
])

param_grid = {
    "clf__learning_rate"   : [0.01, 0.1, 0.2],
    "clf__max_depth"       : [3, 5, 7],
    "clf__n_estimators"    : [100, 200],
    "clf__subsample"       : [0.8, 1.0],
    "clf__colsample_bytree": [0.8, 1.0],
}

total_combinations = 1
for v in param_grid.values():
    total_combinations *= len(v)
print(f"\nTotal kombinasi parameter : {total_combinations}")
print(f"CV folds                  : 5")
print(f"Total fit                 : {total_combinations * 5}")

# ── StratifiedKFold — jaga proporsi kelas di setiap fold ──────────────────────
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

grid_search = GridSearchCV(
    estimator=pipeline,
    param_grid=param_grid,
    cv=cv,
    scoring="f1_macro",     # metrik utama untuk data imbalanced multi-kelas
    n_jobs=-1,
    verbose=2,
    refit=True,             # otomatis latih ulang dengan param terbaik
    return_train_score=True,
)

# ── Training ───────────────────────────────────────────────────────────────────
print(f"\n🔥 MULAI GRID SEARCH... (dimensi input: {X_train.shape})")
start_time = time.time()

grid_search.fit(X_train, y_train)

duration = time.time() - start_time
print(f"\n✅ SELESAI! Waktu: {duration/60:.2f} menit")

# ── Hasil parameter terbaik ────────────────────────────────────────────────────
print("\n" + "=" * 55)
print("PARAMETER TERBAIK")
print("=" * 55)
for k, v in grid_search.best_params_.items():
    print(f"  {k:35}: {v}")
print(f"\n  F1-macro CV (terbaik) : {grid_search.best_score_:.4f}")

# ── Simpan semua hasil CV ke CSV ───────────────────────────────────────────────
cv_results_df = pd.DataFrame(grid_search.cv_results_)
cv_results_df = cv_results_df.sort_values("rank_test_score")
cv_path = MODEL_DIR / "grid_search_results.csv"
cv_results_df.to_csv(cv_path, index=False)
print(f"\n📊 Hasil semua kombinasi CV disimpan: {cv_path}")

# ── Evaluasi pada data test ────────────────────────────────────────────────────
print("\n" + "=" * 55)
print("EVALUASI PADA DATA TEST")
print("=" * 55)

best_model = grid_search.best_estimator_
y_pred = best_model.predict(X_test)

# Mencegah error TypeError '<' saat membandingkan string dan float/NaN
# dengan mengubah seluruh array menjadi tipe data string
y_test_label = le.inverse_transform(y_test).astype(str)
y_pred_label = le.inverse_transform(y_pred).astype(str)
str_classes = le.classes_.astype(str)

print("\nClassification Report:")
print(classification_report(y_test_label, y_pred_label, labels=str_classes))

print("Confusion Matrix:")
cm = confusion_matrix(y_test_label, y_pred_label, labels=str_classes)
cm_df = pd.DataFrame(cm,
                     index=[f"Aktual: {c}"   for c in str_classes],
                     columns=[f"Pred: {c}"   for c in str_classes])
print(cm_df.to_string())

# ── Simpan model ───────────────────────────────────────────────────────────────
model_path = MODEL_DIR / "xgboost_scenario3.pkl"
joblib.dump(best_model, model_path)
print(f"\n💾 Model disimpan: {model_path}")
print("\n✅ STEP 2 SELESAI — Lanjut ke step3_evaluation.py untuk analisis lengkap")