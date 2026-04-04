import joblib
import os
import sys
import pandas as pd
import time
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from pathlib import Path
# ==========================================
# KONFIGURASI PATH
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]

DATA_DIR = PROJECT_ROOT / "data"

PATHS = {
    # Ambil file TF-IDF murni (yang fiturnya masih ribuan)
    "X_train": PROJECT_ROOT / "X_train_tfidf.pkl", 
    "y_train": PROJECT_ROOT / "y_train.pkl", 
    
    # Ambil file Test TF-IDF murni
    "X_test": PROJECT_ROOT / "X_test_tfidf.pkl",
    "y_test": PROJECT_ROOT / "y_test.pkl",
    
    "le": PROJECT_ROOT / "label_encoder.pkl",
}

print("--- MENYIAPKAN TRAINING SCENARIO 3 (OPTIMIZED) ---")

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

print(f"\nDimensi Training: {X_train.shape}")
print(f"Dimensi Testing:  {X_test.shape}")

# ==========================================
# SETTING GRID SEARCH
# ==========================================
# Parameter yang akan dicoba. 
# Jika laptop Anda spek biasa, kurangi jumlah isinya agar tidak terlalu lama.
param_grid = {
    'learning_rate': [0.01, 0.1, 0.2],
    'max_depth': [3, 5, 7],
    'n_estimators': [100, 200],
    'subsample': [0.8, 1.0],
    'colsample_bytree': [0.8, 1.0]
}

# Inisialisasi Model XGBoost
xgb = XGBClassifier(
    objective='multi:softprob', 
    num_class=3, 
    random_state=42, 
    eval_metric='mlogloss',
    use_label_encoder=False
)

# Inisialisasi Grid Search
# cv=3 artinya Cross Validation 3-fold (data dilipat 3x untuk validasi internal)
grid_search = GridSearchCV(
    estimator=xgb,
    param_grid=param_grid,
    cv=3, 
    scoring='f1_macro', # Fokus ke F1 Score karena kita ingin adil ke semua kelas
    n_jobs=-1,          # Gunakan semua core CPU
    verbose=2           # Tampilkan log proses
)

# ==========================================
# EKSEKUSI
# ==========================================
print("\n🔥 MULAI TRAINING & GRID SEARCH...")
print("Harap bersabar, kipas laptop mungkin akan berputar kencang...")
start_time = time.time()

# Proses Training Utama
grid_search.fit(X_train, y_train)

end_time = time.time()
duration = end_time - start_time
print(f"\n✅ SELESAI! Waktu proses: {duration/60:.2f} menit")

# ==========================================
# HASIL & EVALUASI
# ==========================================
best_model = grid_search.best_estimator_

print("\n" + "="*40)
print("HASIL TERBAIK (BEST PARAMETERS)")
print("="*40)
print(grid_search.best_params_)

print("\n" + "="*40)
print("EVALUASI PADA DATA TEST (UNSEEN DATA)")
print("="*40)

# Prediksi ke Data Test (Data Murni)
y_pred = best_model.predict(X_test)

# Kembalikan ke label asli (0->negatif, dst)
y_test_label = le.inverse_transform(y_test)
y_pred_label = le.inverse_transform(y_pred)

# Tampilkan Laporan
print("\nClassification Report:")
print(classification_report(y_test_label, y_pred_label))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test_label, y_pred_label))

# Simpan Model Terbaik
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)

model_path = MODEL_DIR / "new_xgboost_scenario3.pkl"
joblib.dump(best_model, model_path)

print(f"\n💾 Model terbaik disimpan ke: {model_path}")
